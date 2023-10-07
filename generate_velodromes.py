import logging
import pandas as pd
import numpy as np
import trackpy as track

# Configure the logging level and format
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

velodrome_inputs = [
    {
        "name": "Eddy Merckx Wielercentrum",
        "center_utm": (548540.34, 5655259.58),
        "rotation": -17,
        "elevation": 7,
    },
    {
        "name": "Sport Vlaanderen Heusden-Zolder Velodroom Limburg",
        "center_utm": (658970, 5651499),
        "rotation": 19,
        "elevation": 44,
    },
]


def generate_velodromes(velodrome_inputs):
    for inputs in velodrome_inputs:
        name = inputs["name"]

        logging.info(f"Constructing {name}")
        velodrome = track.velodrome.Velodrome(
            inputs["name"],
            center_utm=inputs["center_utm"],
            rotation=inputs["rotation"],
            elevation=inputs["elevation"],
            length=250,
            precision=0.1,
            start_finish=np.round(np.pi * 27.7 + 2 * 38, decimals=1),
        )
        logging.info(f"Succesfully constructed {name}")

        logging.info(f"Saving {name} to a csv file.")
        velodrome.save()
        logging.info(f"Succesfully saved {name} to a csv file.")


generate_velodromes(velodrome_inputs)
