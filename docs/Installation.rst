Installation and Setup
======================

In addition to installing the Python package, there are several additional steps
required for ingesting and building indices.

Installation
------------

The recommended installation method is to use ``pip`` as follows from within the
repository root directory after downloading the code or cloning it via ``git
clone``::

    pip install .

Ingesting Cumulative Indices
----------------------------

One of the two command-line tools installed with :py:mod:`pdsc` is
``pdsc_ingest``. This tool is used to ingest cumulative index files for PDS
observations. The ingestion process constructs databases and index data
structures to enable efficient querying of observations by metadata and
geometry.

By default, :py:mod:`pdsc` supports ingesting cumulative index files from the
following data products:

  - CTX
  - HiRISE (EDR) [1]_
  - HiRISE (RDR)
  - MOC
  - THEMIS IR
  - THEMIS VIS

For information on extending PDSC to support other instruments, see
:ref:`Extending PDSC`.

As an example, the most recent cumulative index files for the HiRISE data
products can be found here: https://hirise-pds.lpl.arizona.edu/PDS/INDEX/.

The cumulative index files for these instruments consist of a ``.lbl`` file and
a ``.tab`` file. Both files must be present in the same directory, and either
file can be specified when ingesting the index::

    $ pdsc_ingest cumulative_index.lbl /path/to/generated/index/dir/

It will be necessary to re-ingest new versions of the cumulative index files as
new volumes of data are released.

Environment Variables
---------------------

In order to use the ingested indices, several environment variables can be set
to tell :py:mod:`pdsc` where to look for the files or which server to query (see
:ref:`Running a Server`). The variables are:

+-----------------------+-------------------------------------------------+
| Variable Name         | Description                                     |
+=======================+=================================================+
| ``PDSC_DATABASE_DIR`` | Location of the ingested PDS cumulative indices |
+-----------------------+-------------------------------------------------+
| ``PDSC_SERVER_HOST``  | Hostname or IP address of PDSC server           |
+-----------------------+-------------------------------------------------+
| ``PDSC_SERVER_PORT``  | Port of PDSC server                             |
+-----------------------+-------------------------------------------------+

If these environment variables are not set, they can be specified as arguments
when constructing a client to query metadata.

.. [1] There is a bug in the HiRISE EDR cumulative index files; some values for
       the ``SCAN_EXPOSURE_DURATION`` column exceed the 9 bytes allocated for
       that column. The offending values should be modified to bring the data
       into accordance with the schema before attempting to ingest the index.
       See :ref:`Fixing HiRISE EDR Indices` for instructions.
