import numpy as np
import pandas as pd
import pathlib
import logging
import trackpy as track

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

filename = pathlib.Path("csvs/report.csv")
logging.info(f"Parsing {filename}")
transponder = track.parse_transponder(filename)

logging.info(f"Mapping {filename} to the Eddy Merck wielercentrum")
interpolation = track.map_interpolation_to_velodrome(transponder, wielercentrum)

output = "example.gpx"
logging.info(f"Writing to {output}")
track.write_gpx(output, interpolation, velodrome=wielercentrum)
