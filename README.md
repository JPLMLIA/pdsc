PDSC: PDS Coincidences
======================

This module allows ingesting/indexing and querying PDS data for the following
information:

  - Observation metadata
  - Observations meeting some basic metadata constraints (e.g., within date
    range or latitude range)
  - Localizing pixels within observations
  - Observations of a given latitude/longitude (or within some radius of that
    location)
  - Observations overlaping some other observation

# Injesting Data

In order to ingest new metadata, the following steps are required:

1. Modify `determine_instrument` in `pds_table.py` to recognize the instrument
name from the cumulative index label file

2. Subclass `PdsTableColumn` and `PdsTable` to correctly parse the PDS table
file

3. Add the subclass of `PdsTable` to the `INSTRUMENT_TABLES` dictionary in
`pds_table.py`

4. Add a config file to the `config` directory matching the naming convention
`[instrument name]_metadata.yaml`. This file maps table columns to metadata
field names and also allows unit conversion, indexing of metadata fields, and
specifying segmentation resolution

5. Subclass `Localizer` in `localization.py`. For most cases, it is probably
easiest to subclass the `GeodesicLocalizer`

6. Add the localizer subclass to the `LOCALIZERS` table in `localization.py`

7. Run the following: `python ingest.py [cumulative index file] [output directory]`
