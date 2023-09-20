# trackpy
Code to convert sporthive csv files to gpx files.

# Supported velodromes
* Eddy Merckx Wielerpiste (Strandlaan 3, 9000 Gent, Belgium)

## Adding velodromes
You can add your own velodrome with
```
import trackpy as track

velodrome = track.velodrome.Velodrome(
        name,
        center_utm=(x, y),
        rotation=rotation,
        length=250,
        precision=0.1,
        elevation=elevation,
        start_finish=start_finish,
    )
```

You need to specify the geometric center of the velodrome in UTM coordinates. These are local Cartesian coordinates. You can find UTM coordinates with a tool such as [geoplaner](https://www.geoplaner.com). Optionally, you can define the elevation of the velodrome. Elevation can be found with e.g. the [Open Elevation API](https://open-elevation.com). The `start_finish` argument determines where the the start and finish line lies on the velodrome, expressed in arc length. For a velodrome of 250 meters, this must be a value between 0 and 250.

Currently only velodromes with a length of 250 meters are supported. The exact geometry of a velodrome can be quite complicated. We approximate a velodrome as two semicircles connected by two straight lines.

# Installation
1. Clone the repo  
`git clone https://github.com/vitesse9000/trackpy.git`
2. Change to the cloned repo  
`cd trackpy`
3. Install the dependencies with  
`python3 -m pip install -r requirements.txt`

# How to
## Command line interface example
```
python3 track_to_gpx.py --input="example.csv" --output="example.gpx"
```

## Python script example
```
import trackpy as track

# construct velodrome
filename = "eddy_merckx_wielercentrum_wgs84.csv"
arc_length_wgs84 = pd.read_csv(filename)
wielercentrum = track.velodrome.BaseVelodrome(
    "Eddy Merckx Wielercentrum",
    elevation=7,
    start_finish=np.round(np.pi * 27.7 + 2 * 38, decimals=1),
    arc_length_wgs84=arc_length_wgs84,
)

# parse the csv file and convert to gpx
transponder = track.parse_transponder("example.csv")
interpolation = track.map_interpolation_to_velodrome(transponder, wielercentrum)
track.write_gpx("example.gpx", interpolation, velodrome=wielercentrum)
```

## Options
The sporthive csv files can contain multiple sessions if the rider takes a rest. It's possible to only use a subset of the sessions available in the sporthive csv file with the `sessions` keyword argument.

## Command line interface
```
python3 track_to_gpx.py --input="example.csv" --output="example.gpx" --sessions=2,3
```

## Python script interface
```
transponder = track.parse_transponder("example.csv", sessions=[2,3])
```

