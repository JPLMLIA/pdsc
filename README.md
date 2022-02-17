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

## HiRISE Example

# Download HiRISE Label and Tablel files:

```bash
wget -O RDRCUMINDEX.LBL https://hirise-pds.lpl.arizona.edu/PDS/INDEX/RDRCUMINDEX.LBL
wget -O RDRCUMINDEX.TAB https://hirise-pds.lpl.arizona.edu/PDS/INDEX/RDRCUMINDEX.TAB
```

To ingest indices:

```bash
pdsc_ingest -c pdsc/config/hirise_rdr_metadata.yaml /home/edunkel/PDS/lroc_proj/pdsc/inputs/hirise/RDRCUMINDEX.LBL /home/edunkel/PDS/lroc_proj/pdsc/outputshirise/
```


