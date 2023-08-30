import pandas as pd


def read_transponder(filename=None, length=250):
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

    df = df.set_index(["Session", "Lap"])
    df["Distance (m)"] = (
        (df["Laptime (s)"] * df["Average speed (m/s)"]).cumsum().round()
    )

    return df


def interpolate(lap_distances, length=250, tz="Europe/Brussels"):
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

    # add observations where time continues, but the rider stand still
    # this is such that Strava detects these as auto pauses
    # calculate how many seconds are between each sessions, i.e. how long did the rider pause
    # we need to add the time of the last lap to the timestamp
    # as the timestamps are the start of the round
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
    lap_distances = lap_distances.reset_index()
    last_element_above_230 = lap_distances[::-1]["Distance covered"].gt(230).idxmax()
    lap_distances.loc[last_element_above_230 + 1 :, "Distance covered"] = 0

    return lap_distances


def map_interpolation_to_velodrome(interpolation, velodrome):
    arc_length = velodrome.arc_length_wgs84
    interpolation = interpolation[
        ["Interpolated distance (m)", "Distance covered", "Interpolated time (s)"]
    ]

    result = interpolation.merge(
        arc_length, left_on="Distance covered", right_on="Arc length (m)", how="left"
    )

    # result = result.drop(columns=["Distance covered"])

    return result

def parse_transponder(filename, length=250, tz="Europe/Brussels", sessions=[]):
    transponder = read_transponder(filename, length=length)

    if sessions:
        transponder = transponder.query("session in @sessions")

    interpolation = interpolate(transponder, length=length, tz=tz)

    return interpolation
