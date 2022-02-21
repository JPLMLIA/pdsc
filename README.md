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

First, create and activate a barebones env using python 3.7:

```bash
conda env create -f env/bare_env.yml
conda activate p37
```

I have also tried with python2, but when doing pip install, I got an error with incompatible numpy versions, but python 3 works, so recommend to use that.

Note: I created full and mini examples (a subset of rows) for the cases. If you take a subset of the rows, you must also update the label file with the reduced number of rows.

## HiRISE Example

# Download HiRISE Label and Table files:

```bash
wget -O RDRCUMINDEX.LBL https://hirise-pds.lpl.arizona.edu/PDS/INDEX/RDRCUMINDEX.LBL
wget -O RDRCUMINDEX.TAB https://hirise-pds.lpl.arizona.edu/PDS/INDEX/RDRCUMINDEX.TAB
```

To ingest indices:

```bash
pdsc_ingest -c pdsc/config/hirise_rdr_metadata.yaml /home/edunkel/PDS/lroc_proj/pdsc/inputs/hirise/RDRCUMINDEX.LBL /home/edunkel/PDS/lroc_proj/pdsc/outputshirise/
```

# CTX example:

```
pdsc_ingest /pds/pdsfs2/pdsdata/mro/ctx/mrox_4098/index/cumindex.tab /home/edunkel/PDS/lroc_proj/pdsc/outputsctx/ 
```

Or, a mini example (I took a subset of rows from the table file and updated the index accordingly):

```
pdsc_ingest /home/edunkel/PDS/lroc_proj/pdsc/inputs_mini/ctx/cumindex.tab /home/edunkel/PDS/lroc_proj/pdsc/outputsctxmini/
```
