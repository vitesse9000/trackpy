import pandas as pd


def read_transponder(filename=None, length=250, sessions=None):
    """
    Read and preprocess a csv file from https://results.sporthive.com containing transponder data.

    This function reads a csv file, performs various data transformations,
    and returns a DataFrame with the processed data. The DataFrame will
    contain columns for timestamp, session, lap, lap time, average speed,
    and distance.

    Parameters
    ----------
    filename : str, optional
        The path to the csv file to read.
    length : int, optional
        The length of the track in meters. The default is 250.
    sessions : list of int, optional
        A list of session IDs to filter the data by. If None, no filtering is applied.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the processed data with the following columns:
        - 'Timestamp': Timestamp of the lap
        - 'Session': Session ID
        - 'Lap': Lap number
        - 'Laptime (s)': Time taken to complete the lap in seconds
        - 'Average speed (m/s)': Average speed during the lap in meters per second
        - 'Distance (m)': Cumulative distance covered in meters

    Examples
    --------
    >>> read_transponder('data.csv')
    Returns a DataFrame with processed data from 'data.csv'.

    >>> read_transponder('data.csv', sessions=[1, 2])
    Returns a DataFrame with processed data from 'data.csv', filtered for sessions 1 and 2.

    Notes
    -----
    The input CSV file should be encoded in 'utf-16-le' and should contain the following columns:
    - 'Date': The date of the lap
    - 'Start time': The start time of the lap
    - 'Total time': The total time taken for the lap
    - 'Laptime': The time taken for the lap
    - 'Speed': The average speed during the lap in km/h
    - 'Lap': The lap number
    - 'Diff': The time difference from the previous lap
    - 'Transponder': The transponder ID

    """
    df = pd.read_csv(filename, encoding="utf-16-le").dropna(how="all")

    # add time and date
    df["Timestamp"] = pd.to_datetime(
        df[["Date", "Start time"]].agg(" ".join, axis=1), format="%d-%m-%Y %H:%M:%S"
    )

    # convert objects to floats (decimal seconds)
    for column in ["Total time", "Laptime"]:
        df[column] = pd.to_timedelta(df[column]).dt.total_seconds()

    # convert lap to int
    df["Lap"] = df["Lap"].astype(int)

    # add sessions
    df["Session"] = (df["Lap"] != df["Lap"].shift(1) + 1).cumsum()

    # filter on desired sessions
    if sessions:
        df = df.query("Session in @sessions").copy()

    # convert speed string to float
    df["Speed"] = df["Speed"].str.replace(" km/h", "").astype(float) / 3.6

    # remove unnecessary or processed columns
    df = df.drop(columns=["Date", "Start time", "Diff", "Transponder"])

    # reorder columns
    df = df[
       [
           "Timestamp",
           "Session",
           "Lap",
           "Laptime",
           "Speed",
       ]
    ]

    # rename columns
    df = df.rename(
        columns={
            "Speed": "Average speed (m/s)",
            "Laptime": "Laptime (s)",
        }
    )

    df["Distance (m)"] = (
        (df["Laptime (s)"] * df["Average speed (m/s)"]).cumsum().round()
    )

    return df


def _add_missing_observations(lap_distances):
    """
    Add missing observations to account for auto-pauses in the lap data.

    This function takes a DataFrame containing lap data and adds extra rows
    to account for periods where the rider is stationary (auto-pauses).
    This ensures that such periods are correctly identified in platforms like Strava.

    Parameters
    ----------
    lap_distances : pd.DataFrame
        A DataFrame containing lap data with the following columns:
        - 'Timestamp': Timestamp of the lap
        - 'Session': Session ID
        - 'Lap': Lap number
        - 'Laptime (s)': Time taken to complete the lap in seconds
        - 'Average speed (m/s)': Average speed during the lap in meters per second

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the original data along with additional rows
        for auto-pauses. The DataFrame will have the same columns as the input.

    Notes
    -----
    The function calculates the pause length between sessions and adds extra
    observations where the rider is stationary. These extra observations have
    'Laptime (s)' and 'Average speed (m/s)' set to 0.

    """
    gby = (
        lap_distances.assign(
            Timestamp_after_last_round=lap_distances["Timestamp"]
            + pd.to_timedelta(lap_distances["Laptime (s)"], unit="seconds")
        )
        .reset_index()
        .groupby("Session")
        .agg(
            first_time=pd.NamedAgg("Timestamp", "min"),
            last_time=pd.NamedAgg("Timestamp_after_last_round", "max"),
        )
    )

    pause_length = (
        (gby["first_time"].shift(-1) - gby["last_time"]).dt.total_seconds().dropna()
    )
    for session, seconds in zip(pause_length.index, pause_length.values):
        seconds = int(seconds)
        last_observation = lap_distances.query("Session == @session").tail(1).copy()
        last_observation.loc[
            last_observation.index, ["Laptime (s)", "Average speed (m/s)"]
        ] = 0

        extra_observations = pd.concat([last_observation] * seconds)

        lap_distances = pd.concat([lap_distances, extra_observations]).fillna(0)

    return lap_distances


def interpolate(lap_distances, length=250, tz="Europe/Brussels"):
     """
    Interpolate lap data to generate more granular observations.

    This function takes a DataFrame containing lap data and performs interpolation
    to generate observations with a frequency of 1 second. It also adjusts for 
    time zones and adds additional columns for interpolated distance and time.

    Parameters
    ----------
    lap_distances : pd.DataFrame
        A DataFrame containing lap data with the following columns:
        - 'Timestamp': Timestamp of the lap
        - 'Session': Session ID
        - 'Lap': Lap number
        - 'Laptime (s)': Time taken to complete the lap in seconds
        - 'Average speed (m/s)': Average speed during the lap in meters per second
    length : int, optional
        The length of the track in meters. The default is 250.
    tz : str, optional
        The time zone to localize the timestamps to. The default is "Europe/Brussels".

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the original data along with additional interpolated
        rows and columns for distance and time. The DataFrame will have the following columns:
        - 'Interpolated distance (m)': Cumulative distance covered in meters
        - 'Distance covered': Distance covered on the velodrome in meters
        - 'Interpolated time (s)': Interpolated timestamps localized to the given time zone

    Notes
    -----
    The function performs several steps to interpolate the data:
    1. Rounds lap times to the nearest second.
    2. Adds counters to keep track of interpolated values.
    3. Adds observations for paused seconds using `_add_missing_observations`.
    4. Sorts the DataFrame and calculates intermediate distances and times.
    5. Localizes the timestamps to the given time zone.

    """

    # trick to copy each row t amount of times where t is the number of seconds needed to complete the quarter
    lap_distances["Laptime rounded (s)"] = (
        lap_distances["Laptime (s)"].round(0).astype(int)
    )

    # add counter to keep track of all interpolated values
    lap_distances["Distance counter"] = lap_distances["Laptime rounded (s)"].apply(
        lambda x: list(range(0, x))
    )
    lap_distances["Laptime rounded (s)"] = lap_distances["Laptime rounded (s)"].apply(
        lambda x: [x] * x
    )
    lap_distances = lap_distances.explode(["Laptime rounded (s)", "Distance counter"])

    # add observations for every paused second
    lap_distances = _add_missing_observations(lap_distances)
    lap_distances = lap_distances.sort_values(by=["Session", "Lap", "Timestamp"])

    # add time counter used to determine intermediate distance and total elapsed time
    lap_distances["Time counter"] = list(range(0, lap_distances.shape[0]))

    # calculate intermediate distance
    lap_distances["Interpolated distance (m)"] = (
        lap_distances["Time counter"].diff().fillna(0)
        * lap_distances["Average speed (m/s)"]
    ).cumsum()

    # calculate distance covered on the velodrome
    _, distance_covered = lap_distances["Interpolated distance (m)"].divmod(length)
    lap_distances["Distance covered"] = distance_covered.round(decimals=1)

    # highest sampling rate in gpx file is dictated by the timeformat ISO 8601
    # which is 1 second, as such, the counter is actually the number of seconds
    # since the start of the activity
    lap_distances["Total elapsed interpolated time (s)"] = pd.to_timedelta(
        lap_distances["Time counter"].apply(lambda x: str(x) + "s")
    )

    # add intermediate time to starttime of quarter
    lap_distances["Interpolated time (s)"] = (
        lap_distances["Timestamp"].iloc[0]
        + lap_distances["Total elapsed interpolated time (s)"]
    )

    # convert to correct timezone
    lap_distances["Interpolated time (s)"] = lap_distances[
        "Interpolated time (s)"
    ].dt.tz_localize(tz=tz)

    # remove intermediate columns needed for calculations
    lap_distances = lap_distances.drop(
       columns=[
           "Laptime (s)",
           "Distance (m)",
           "Laptime rounded (s)",
           "Total elapsed interpolated time (s)",
           "Distance counter",
           "Time counter",
       ]
    )

    # between two sessions, the riders leaves the track
    # thus distance covered is 250 divmod 250 or 0
    condition = lap_distances["Average speed (m/s)"] == 0
    lap_distances.loc[condition, "Distance covered"] = 0

    # after the last lap, the rider leaves the track
    # hence distance covered should also be 0 for these last few observations
    # due to numerical precision
    # there can be a few observations that start a new lap, which isn't there in reality
    # set distance covered 0 for these observations
    last_element_above_230 = lap_distances[::-1]["Distance covered"].gt(230).idxmax()
    lap_distances.loc[last_element_above_230 + 1 :, "Distance covered"] = 0

    return lap_distances


def map_interpolation_to_velodrome(interpolation, velodrome):
    """
    Map interpolated lap data to a velodrome's geometry.

    This function takes a DataFrame containing interpolated lap data and a
    Velodrome object containing the velodrome's geometry. It merges the
    DataFrame with the arc lengths from the Velodrome object based on the
    distance covered on the velodrome mapping the interpolated
    data to the velodrome's geometry.

    Parameters
    ----------
    interpolation : pd.DataFrame
        A DataFrame containing interpolated lap data with the following columns:
        - 'Interpolated distance (m)': Cumulative distance covered in meters
        - 'Distance covered': Distance covered on the velodrome in meters
        - 'Interpolated time (s)': Interpolated timestamps
    velodrome : Velodrome
        A Velodrome object containing the velodrome's geometry. The object
        should have an attribute `arc_length_wgs84` which is a DataFrame with
        the following column:
        - 'Arc length (m)': The arc length at various points on the velodrome in meters

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the original interpolated data along with the
        velodrome's geometry. The DataFrame will have the following columns:
        - 'Interpolated distance (m)'
        - 'Distance covered'
        - 'Interpolated time (s)'
        - 'Arc length (m)'

    Notes
    -----
    The function performs a left join between the `interpolation` DataFrame
    and the `arc_length_wgs84` DataFrame from the `Velodrome` object based
    on the 'Distance covered' and 'Arc length (m)' columns.

    """
    arc_length = velodrome.arc_length_wgs84

    interpolation = interpolation[
        ["Interpolated distance (m)", "Distance covered", "Interpolated time (s)"]
    ]

    result = interpolation.merge(
        arc_length, left_on="Distance covered", right_on="Arc length (m)", how="left"
    )

    return result


def parse_transponder(filename, length=250, tz="Europe/Brussels", sessions=None):
    """
    Parse and interpolate transponder data from a csv file coming from https://results.sporthive.com.

    Parameters
    ----------
    filename : str
        Path to the csb file containing transponder data.
    length : int, optional
        Length of the track in meters. Default is 250.
    tz : str, optional
        Time zone for timestamps. Default is "Europe/Brussels".
    sessions : list of int, optional
        List of session IDs to filter by. Default is None.

    Returns
    -------
    pd.DataFrame
        DataFrame containing interpolated lap data.
    """

    transponder = read_transponder(filename, length=length, sessions=sessions)
    interpolation = interpolate(transponder, length=length, tz=tz)

    return interpolation
