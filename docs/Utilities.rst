Command Line Utilities
======================

PDSC provides some command line utilties to provide useful functionality.
Currently, two utilities are implemented to fix HiRISE EDR abd RDR cumulative
index files prior to ingesting them.

Fixing HiRISE EDR Indices
-------------------------

There is a bug in the HiRISE EDR cumulative index files; some values for the
``SCAN_EXPOSURE_DURATION`` column exceed the 9 bytes allocated for that column.
The offending values should be modified to bring the data into accordance with
the schema before attempting to ingest the index. This can be accomplished using
the following command::

    $ pdsc_util fix_hirise_index EDRCUMINDEX.TAB

By default, the index file will be overwritten with a corrected version. A
separate output file can also be specified (use the ``-h`` flag for a full set
of options).

Fixing HiRISE RDR Indices
-------------------------

There are some inconsistencies between the HiRISE RDR cumulative index file
(.TAB) and its metadata file (.LBL). The number of lines in the cumulative
index file doesn't match the entries of ``FILE_RECORDS`` and ``ROWS`` in the
metadata file. The values of ``FILE_RECORDS`` and ```ROWS` should be modified
with respect to the actual number of lines in the cumulative index file. This
can be accomplished using the following command::

    $ pdsc_util fix_hirise_idxlbl RDRCUMINDEX.TAB

By default, the index file will be overwritten with a corrected version. A
separate output file can also be specified using the ``-o`` flag provided.
Please use ``-h`` flag for a full set of options.