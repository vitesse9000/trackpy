from xml.etree import ElementTree

import gpxpy
import gpxpy.gpx
import pandas as pd
import sweat


def read_fit(
    file, tz="Europe/Brussels", hr=True, cadence=True, calories=True, lap=True
):
    """
    Read and process a .fit file, converting time zone and filtering columns.

    Parameters
    ----------
    file : str
        Path to the .fit file to read.
    tz : str, optional
        Time zone to convert the timestamps to. Default is "Europe/Brussels".
    hr : bool, optional
        Whether to include the 'heartrate' column. Default is True.
    cadence : bool, optional
        Whether to include the 'cadence' column. Default is True.
    calories : bool, optional
        Whether to include the 'calories' column. Default is True.
    lap : bool, optional
        Whether to include the 'lap' column. Default is True.

    Returns
    -------
    pd.DataFrame
        DataFrame containing selected columns with timestamps converted to the specified time zone.

    """

    fit = sweat.read_fit(file).reset_index()
    fit["datetime"] = fit["datetime"].dt.tz_convert(tz=tz)

    columns = ["datetime"]

    if hr:
        columns += ["heartrate"]
    if cadence:
        columns += ["cadence"]
    if calories:
        columns += ["calories"]
    if lap:
        columns += ["lap"]

    return fit[columns]


def construct_gpx(latitudes, longitudes, times, elevations, heartrates, cadences):
    """
    Construct a GPX (GPS Exchange Format) object from provided data.

    Parameters
    ----------
    latitudes : list of float
        List of latitudes for each track point.
    longitudes : list of float
        List of longitudes for each track point.
    times : list of datetime
        List of datetime objects representing the time for each track point.
    elevations : list of float
        List of elevations for each track point.
    heartrates : list of int
        List of heart rates for each track point.
    cadences : list of int
        List of cadences for each track point.

    Returns
    -------
    gpxpy.gpx.GPX
        A GPX object containing the track points with the provided latitudes, longitudes, times, elevations, heart rates, and cadences.
    """
    
    gpx = gpxpy.gpx.GPX()

    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    # Create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for lat, long, time, elevation, heartrate, cadence in zip(
        latitudes, longitudes, times, elevations, heartrates, cadences
    ):
        gpx_point = gpxpy.gpx.GPXTrackPoint(
            latitude=lat, longitude=long, time=time, elevation=elevation
        )

        if heartrate:
            # create extension element
            namespace = "{gpxpy}"
            nsmap = {
                namespace[
                    1:-1
                ]: "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
            }
            gpx.nsmap = nsmap

            track_point_extensions = ElementTree.Element(
                f"{namespace}TrackPointExtension"
            )
            hr = ElementTree.SubElement(
                track_point_extensions,
                f"{namespace}hr",
            )
            hr.text = str(heartrate)

            gpx_point.extensions.append(track_point_extensions)

        gpx_segment.points.append(gpx_point)
        
    return gpx


def write_gpx(filename, interpolation, fit=None, velodrome=None):
    """
    Write GPX (GPS Exchange Format) data to a file based on provided interpolation and optional fit data.

    Parameters
    ----------
    filename : str
        Name of the file to write the GPX data to.
    interpolation : pd.DataFrame
        DataFrame containing interpolated data with columns 'Latitude (WGS84)', 'Longitude (WGS84)', and 'Interpolated time (s)'.
    fit : pd.DataFrame, optional
        DataFrame containing optional fit data with columns 'datetime', 'heartrate', 'cadence', and 'lap'. Default is None.
    velodrome : Velodrome, optional
        A Velodrome object containing the velodrome's geometry and elevation. Default is None.

    Returns
    -------
    None
        Writes the GPX data to the specified file.

    Notes
    -----
    The function merges the `interpolation` DataFrame with the `fit` DataFrame if provided, and uses elevation from the `velodrome` object if provided.
    """

    if fit is not None:
        interpolation = interpolation.merge(
            fit, left_on="Interpolated time (s)", right_on="datetime", how="left"
        )
        heartrates = interpolation["heartrate"]
        cadences = interpolation["cadence"]
        laps = interpolation["lap"]
    else:
        heartrates = [None] * interpolation.shape[0]
        cadences = [None] * interpolation.shape[0]

    if velodrome:
        elevations = [velodrome.elevation] * interpolation.shape[0]
    else:
        elevations = [0] * interpolation.shape[0]

    latitudes = interpolation["Latitude (WGS84)"]
    longitudes = interpolation["Longitude (WGS84)"]
    times = interpolation["Interpolated time (s)"]

    gpx = construct_gpx(latitudes, longitudes, times, elevations, heartrates, cadences)
    
    with open(filename, "w") as f:
        f.write(gpx.to_xml())
