PDSC: Planetary Data System Coincidences
========================================

The purpose of this package is to allow quick querying via Python of remote
sensing observations made of a particular location on the surface of a
planetary body, or overlapping with another observation from any supported
instrument.  Incidentally, `pdsc` also allows querying based on metadata and
transforming between pixel and world coordinate systems. Currently, only
several instruments from Mars orbiters are supported, but the system is
designed to be extensible to other instruments and bodies.

Please refer to the [documentation](https://jplmlia.github.io/pdsc/) for
instructions on installation, setup, and usage.

---

Copyright 2019, by the California Institute of Technology. ALL RIGHTS RESERVED.
United States Government Sponsorship acknowledged. Any commercial use must be
negotiated with the Office of Technology Transfer at the California Institute
of Technology.


----
# Usage

First, create and activate a bare-bones env using python 3.7:

```bash
conda env create -f env/bare_env.yml
conda activate p37
```
Then, do a pip install:

```bash
pip install .
```

Note: I created full and mini examples (a subset of rows) for the cases. If you take a subset of the rows, you must also update the label file with the reduced number of rows. The full examples are available on the JPL MLIA machines only, but I have included the mini examples in this repository.

## PyTests

To run the pytests, you'll need to install pytest and mock. You can do this with "pip install pytest" and "pip install mock".

Then, run from the upper directory:

```bash
pytest
```

You should get pytests passed.

## HiRISE Example

# Download HiRISE Label and Table files:

```bash
wget -O RDRCUMINDEX.LBL https://hirise-pds.lpl.arizona.edu/PDS/INDEX/RDRCUMINDEX.LBL
wget -O RDRCUMINDEX.TAB https://hirise-pds.lpl.arizona.edu/PDS/INDEX/RDRCUMINDEX.TAB
```

Example call to ingest indices:

```bash
pdsc_ingest -c pdsc/config/hirise_rdr_metadata.yaml /PATH/TO/LBL/FOLDER /PATH/TO/OUT/FOLDER
```

Or, a mini example (I took a 9 row subset of the full table file and updated the index accordingly, and have added it to this repo):
Note: the LBL folder must be a full path, so replace /home/edunkel/PDS/lroc_proj to where you are storing your repository.

```
pdsc_ingest -c pdsc/config/hirise_rdr_metadata.yaml /home/edunkel/PDS/lroc_proj/pdsc/inputs_mini/hirise/RDRCUMINDEX.LBL /PATH/TO/OUT/FOLDER
```

# CTX example:

Example call if you have access to analysis machines:

```
pdsc_ingest /pds/pdsfs2/pdsdata/mro/ctx/mrox_4098/index/cumindex.tab /PATH/TO/OUT/FOLDER
```

Or, a mini example (I took a subset of rows from the table file and updated the index accordingly):

```
pdsc_ingest /home/edunkel/PDS/lroc_proj/pdsc/inputs_mini/ctx/cumindex.tab /PATH/TO/OUT/FOLDER
```


# LROC

LROC database:

Example call if you have access to analysis machines:

```
pdsc_ingest -c pdsc/config/lroc_cdr_metadata.yaml /home/edunkel/PDS/lroc_proj/pdsc/from_pdsfs2/CUMINDEX.LBL /PATH/TO/OUT/FOLDER
```

Here is a mini example for lroc:

```
pdsc_ingest -c pdsc/config/lroc_cdr_metadata.yaml /home/edunkel/PDS/lroc_proj/pdsc/inputs_mini/lroc/CUMINDEX.LBL /PATH/TO/OUT/FOLDER
```


# Basic Usage

Follow the docs for basic usage, but make sure you're in the python prompt:

```
# set the directory where the database is stored:
export PDSC_DATABASE_DIR=/home/edunkel/PDS/lroc_proj/pdsc/outputs/lroc/
python
>>> import pdsc
>>> pds_client = pdsc.PdsClient()
>>> metadata = pds_client.query_by_observation_id('lroc_cdr', ' M101014437RC')
>>> mydata = metadata[0]
>>> localizer = pdsc.get_localizer(mydata, browse=True)
>>> lat, lon = localizer.pixel_to_latlon(10, 10)
```

# Scripts

To get lroc distributed samples around the lunar globe, you can call get_distritubed_samples.py. Either pass in parameters from the command line, or update the defaults in the script. Here is a calling example:

```
conda activate p37
# point to database
export PDSC_DATABASE_DIR=/home/edunkel/PDS/lroc_proj/pdsc/outputs/lroc/ # example on analysis machines
python scripts/get_distributed_samples.py -o OUTPUT/FILE -n NUM_SAMPLES
```

This will print a list of examples with their sun angle (which helps with labeling, since craters look different depending on where the sun is).

I have a script to assemble the data from this list in the deep learning repository here: https://github.jpl.nasa.gov/PDSIMG/deep-learning/blob/master/src/lroc/salience/scripts/assemble_data.py
