import folium
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyproj


class Velodrome:
    def __init__(
        self,
        name,
        center_utm=None,
        center_wgs84=None,
        rotation=None,
        length=None,
        elevation=None,
        precision=0.1,
        # TO DO
        # calculate this in some easier way for users
        start_finish=None,
    ):
        self.name = name

        if center_utm:
            self.center_utm = center_utm
            self.lat_utm, self.long_utm = self.center_utm

            # determine wgs84 coordinates
            self.center_wgs84 = self.transform_coordinates(
                self.center_utm, from_coor="utm"
            )
            self.lat_wgs84, self.long_wgs84 = self.center_wgs84

        if center_wgs84:
            self.center_wgs84 = center_wgs84
            self.lat_wgs84, self.long_wgs84 = self.center_wgs84

            # determine utm84 coordinates
            self.center_utm = self.transform_coordinates(
                self.center_wgs84, from_coor="wgs84"
            )
            self.lat_utm, self.long_utm = self.center_utm

        self.length = length
        self.rotation = rotation
        # use https://api.open-elevation.com/api/v1/lookup?locations=51.04682000579793,3.69245806519157
        self.elevation = elevation
        self.precision = precision
        self.start_finish = start_finish

        # set corner radius and straight distance and corresponding precision
        self.determine_velodrome_dimensions()

        # build velodrome
        self.coordinates_utm = self.build_velodrome()
        self.coordinates_wgs84 = self.transform_coordinates(
            self.coordinates_utm, from_coor="utm"
        )

        # determine arc length for both coordinate system
        self.arc_length_utm, self.arc_length_wgs84 = self.calculate_arc_length()

    def determine_velodrome_dimensions(self):

        if self.length == 250:
            self.corner_radius = 27.7
            self.straight_length = 38

        else:
            raise NotImplementedError(
                f"Velodromes of length {self.length} meter are not supported."
            )

        # set precision so each point on the velodrome corresponds to 0.1 meter arc length
        self.corner_precision = int(np.pi * self.corner_radius / self.precision)
        self.straight_precision = int(self.straight_length / self.precision)

    def transform_coordinates(
        self, points, from_coor="utm", to_coor="wgs84", utm_zone=31
    ):
        """
        Zone 31 is Belgium.
        """

        if isinstance(points, tuple):
            points = [points]

        # utm are local cartesian coordinates
        utm = pyproj.Proj(proj="utm", ellps="WGS84", zone=utm_zone)

        # wgs84 is the default coordinate system for gps and geodesy
        # models the earth as on oblate spheroid instead of a sphere
        wgs84 = pyproj.Proj("epsg:4326")

        if from_coor == "utm":
            transformer = pyproj.Transformer.from_proj(utm, wgs84)
        elif from_coor == "wgs84":
            transformer = pyproj.Transformer.from_proj(wgs84, utm)

        coordinates = [transformer.transform(x, y) for (x, y) in points]

        if len(coordinates) == 1:
            coordinates = coordinates[0]

        return coordinates

    def build_corner(self, center, direction="left"):

        if direction == "left":
            corner_radius = self.corner_radius

        elif direction == "right":
            corner_radius = -self.corner_radius

        start = np.pi / 2
        end = 3 * np.pi / 2
        step = (end - start) / (self.corner_precision - 1)
        angles = np.arange(start, end + step, step)

        x, y = center
        corner = [
            (
                x + corner_radius * np.cos(angle),
                y + corner_radius * np.sin(angle),
            )
            for angle in angles
        ]

        return corner

    def build_straight(self, start, direction="left"):

        if direction == "left":
            straight_length = -self.straight_length

        elif direction == "right":
            straight_length = self.straight_length

        x, y = start
        straight = [
            (x + straight_length * (i / self.straight_precision), y)
            for i in range(1, self.straight_precision + 1)
        ]

        return straight

    def rotate_points(self, points, center, angle=0):

        # rotation matrix in radians
        angle = np.deg2rad(angle)
        R = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])

        # matrices with center and points to be rotated
        c = np.atleast_2d(center)
        points = np.atleast_2d(points)

        return np.squeeze((R @ (points.T - c.T) + c.T).T)

    def build_velodrome(self):

        # build velodrome start at top right, i.e. end of the right corner
        start_top_straight = (
            self.lat_utm + (self.straight_length / 2),
            self.long_utm + self.corner_radius,
        )
        top_straight = self.build_straight(
            start_top_straight,
            direction="left",
        )

        start_left_corner = (self.lat_utm - (self.straight_length / 2), self.long_utm)
        left_corner = self.build_corner(start_left_corner, direction="left")

        start_bottom_straight = (
            self.lat_utm - (self.straight_length / 2),
            self.long_utm - self.corner_radius,
        )
        bottom_straight = self.build_straight(start_bottom_straight, direction="right")

        start_right_corner = (
            self.lat_utm + (self.straight_length / 2),
            self.long_utm,
        )
        right_corner = self.build_corner(start_right_corner, direction="right")

        velodrome = top_straight + left_corner + bottom_straight + right_corner

        if self.rotation != 0:
            velodrome = self.rotate_points(
                velodrome, self.center_utm, angle=self.rotation
            )

        # set the start of the velodrome at the start/finish line
        start_finish = int(self.start_finish * 10)
        velodrome = np.concatenate([velodrome[start_finish:], velodrome[:start_finish]])

        return velodrome

    def calculate_arc_length(self):

        # the arc length is the same for both coordinates systems
        arc_length = np.arange(0, len(self.coordinates_utm) / 10, self.precision)

        # utm
        lat_utm, long_utm = zip(*self.coordinates_utm)
        arc_length_utm = pd.DataFrame(
            data={
                "Latitude (UTM)": lat_utm,
                "Longitude (UTM)": long_utm,
                "Arc length (m)": arc_length,
            }
        )
        arc_length_utm["Arc length (m)"] = arc_length_utm["Arc length (m)"].round(
            decimals=1
        )

        # wgs84
        lat_wgs84, long_wgs84 = zip(*self.coordinates_wgs84)
        arc_length_wgs84 = pd.DataFrame(
            data={
                "Latitude (WGS84)": lat_wgs84,
                "Longitude (WGS84)": long_wgs84,
                "Arc length (m)": arc_length,
            }
        )
        arc_length_wgs84["Arc length (m)"] = arc_length_wgs84["Arc length (m)"].round(
            decimals=1
        )

        return arc_length_utm, arc_length_wgs84

    def plot_velodrome(self):

        x, y = zip(*self.coordinates_utm)
        fig, ax = plt.subplots()

        # plot velodrome except for start/finish
        ax.scatter(x[1:], y[1:], color="cornflowerblue")

        # hightlight start/finish in red
        ax.scatter(x[0], y[0], color="darkblue")

        return ax

    def osm_velodrome(self):

        # construct openstreetmap plot
        # velodromes are small, so zoom in to max zoom == 18
        osm_map = folium.Map(location=[self.lat_wgs84, self.long_wgs84], zoom_start=18)

        # add velodrome to map
        for (lat, lon) in self.coordinates_wgs84[1:]:
            folium.CircleMarker(
                location=[lat, lon],
                radius=2,
                weight=4,
                color="cornflowerblue",
            ).add_to(osm_map)

        # highlight start/finish in red
        lat_start, lon_start = self.coordinates_wgs84[0]
        folium.CircleMarker(
            location=[lat, lon], radius=2, weight=4, color="darkblue"
        ).add_to(osm_map)

        return osm_map
