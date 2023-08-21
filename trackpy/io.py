from xml.etree import ElementTree

import gpxpy
import gpxpy.gpx
import pandas as pd
import sweat


def read_fit(
    file, tz="Europe/Brussels", hr=True, cadence=True, calories=True, lap=True
):
    """
    Fix the timezone and give the timestamp as a column.
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


def write_gpx(filename, interpolation, fit=None, velodrome=None):

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

    with open(filename, "w") as f:
        f.write(gpx.to_xml())
