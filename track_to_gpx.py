import numpy as np
import pandas as pd
import pathlib
import logging
import trackpy as track
import argparse

parser = argparse.ArgumentParser(description='Convert track CSV into GPX file')
parser.add_argument('--input', '-i', help='CSV file to read')
parser.add_argument('--output', '-o', help='GPX file to write')

args = parser.parse_args()

csvfile = args.input
gpxfile = args.output

# Configure the logging level and format
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

wielercentrum = track.velodrome.Velodrome(
    "Eddy Mercx Wielercentrum",
    center_utm=(548540.34, 5655259.58),
    rotation=-18,
    elevation=7,
    length=250,
    precision=0.1,
    start_finish=np.round(np.pi * 27.7 + 2 * 38, decimals=1),
)

filename = pathlib.Path(csvfile)
logging.info(f"Parsing {filename}")
transponder = track.parse_transponder(filename)

logging.info(f"Mapping {filename} to the Eddy Merck wielercentrum")
interpolation = track.map_interpolation_to_velodrome(transponder, wielercentrum)

logging.info(f"Writing to {gpxfile}")
track.write_gpx(gpxfile, interpolation, velodrome=wielercentrum)