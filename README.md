# trackpy
Code to convert sporthive csv files to gpx files.

# Supported velodromes
* Eddy Merck Wielerpiste

# How to
1. Clone the repo
2. Install dependencies with `python3 -m pip install -r requirements.txt`
3. Run the example code with `python3 track_to_gpx.py --input="example.csv" --output="example.gpx"`

# Options
It's possible to only use a subset of the sessions available in the sporthive csv file. This can be done as follows
`python3 track_to_gpx.py --input="example.csv" --output="example.gpx" --sessions=[2,3]`
