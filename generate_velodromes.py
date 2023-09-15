import logging
import pandas as pd
import numpy as np

import trackpy as track

# Configure the logging level and format
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Constructing the Eddy Merckx Wielercentrum")
wielercentrum = track.velodrome.Velodrome(
    "Eddy Merckx Wielercentrum",
    center_utm=(548540.34, 5655259.58),
    rotation=-17,
    elevation=7,
    length=250,
    precision=0.1,
    start_finish=np.round(np.pi * 27.7 + 2 * 38, decimals=1),
)
logging.info("Succesfully constructed the Eddy Merckx Wielercentrum")

logging.info("Saving Eddy Merck Wielercentrum to a csv file.")
wielercentrum.save()
logging.info("Succesfully saved Eddy Merck Wielercentrum to a csv file.")
