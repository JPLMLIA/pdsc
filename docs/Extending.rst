Extending PDSC
==============

This section describes how to extend PDSC to support other instruments and data
products. The basic steps are listed and described in more detail below:

  1. Write a determiner function that recognizes the instrument from the PDS
     cumulative index LBL file
  2. Sub-class the :py:class:`~pdsc.table.PdsTableColumn` and
     :py:class:`~pdsc.table.PdsTable` classes, and register the table class
     with the instrument
  3. Implement and register a localizer that converts pixel coordinates to
     real-world latitude and longitude coordinates
  4. Write a configuration file that describes how to store PDS cumulative index
     metadata

Preliminary Concepts
--------------------

There are a few general concepts that are useful for understanding how to extend
PDSC. First is the concept of an "instrument," which is central to organizing
information within PDSC. In PDSC, an "instrument" corresponds to a single data
product as indexed in the PDS rather than to a piece of hardware. Occasionally,
these concepts do not align. For example, HiRISE EDR and HiRISE RDR are
considered two different "instruments" whereas MOC NA and MOC WA are considered
a single "instrument" because they are indexed together.

Instrument names are used to generate index and database file names, so they
should not contain any characters that will confuse the filesystem. By
convention, all instrument names in PDSC follow `snake_case
<https://en.wikipedia.org/wiki/Snake_case>`_.

The next useful concept is that of "registration." PDSC defines decorators that
can be used to "register" functions or classes to an instrument perform various
parts of the PDSC pipeline. During a stage of the processing pipeline, PDSC
looks for a function or class that has been registered to the relevant
instrument to perform that pipeline step.

Instrument Determination
------------------------

The first step in parsing a PDS cumulative index file is determining the
instrument to which the index corresponds. The PDSC library does this using
"determiner" functions. A determiner function for an instrument takes a PDS
cumulative index label file and uses the file to determine whether the file
is for the given instrument.

An example determiner with registration decorator is shown below::

    @register_determiner('hirise_edr')
    def hirise_edr_determiner(label_contents):
          return ('HiRISE' in label_contents and 'EDR_INDEX_TABLE' in label_contents)

The determiner simply checks whether the words ``HiRISE`` and
``EDR_INDEX_TABLE`` appear in the label file. There is also a
:py:meth:`~pdsc.table.generic_determiner` method that uses the
``INSTRUMENT_NAME`` header in the label file to determine if the files is for
the given instrument. For example::

    @register_determiner('ctx')
    def ctx_determiner(label_contents):
        return generic_determiner(label_contents, 'CONTEXT CAMERA')

To perform instrument determination, PDSC goes through every determiner that
has been registered in alphabetical order by instrument name and returns the
first instrument name for which the determiner returns ``True``.

Metadata Parsing
----------------

After determining the instrument associated with a PDS label file, PDSC looks to
find a subclass of :py:class:`~pdsc.table.PdsTable` that has been registered to
the instrument. This class is used to parse the observation metadata located in
the PDS label and table file pair.

The :py:class:`~pdsc.table.PdsTable` class has several attributes that a
subclass can override to control parsing behavior. See the documentation of that
class for details. One attribute of note is
:py:attr:`~pdsc.table.PdsTable.COLUMN_CLASS`. This attribute should specify a
subclass of :py:class:`~pdsc.table.PdsTableColumn` that is used to parse
individual columns from a PDS table.

The :py:class:`~pdsc.table.PdsTableColumn` also has several attributes that can
be overridden to control parsing behavior. A key attribute of this class is
:py:attr:`~pdsc.table.PdsTableColumn.SPECIAL_TYPES`, which controls how data
from a column is converted to a Python type.

After defining a :py:class:`~pdsc.table.PdsTable` subclass for an instrument and
setting :py:attr:`~pdsc.table.PdsTable.COLUMN_CLASS` appropriately, the
:py:meth:`~pdsc.table.register_table` decorator can be used to register the
table class to an instrument.

Localization
------------

Extensions to PDSC must provide the capability to perform localization, the
mapping of pixels in an observation to real-world latitude and longitude
coordinates. A localizer must follow the interface defined by the
:py:class:`~pdsc.localization.Localizer` class. Extensions should register a
subclass of :py:class:`~pdsc.localization.Localizer` or a function that returns
an instance of this type using the
:py:meth:`~pdsc.localization.register_localizer` decorator.

Subclasses of :py:class:`~pdsc.localization.Localizer` need only implement
:py:meth:`~pdsc.localization.Localizer.pixel_to_latlon`; the reverse mapping
:py:meth:`~pdsc.localization.Localizer.latlon_to_pixel` is already implemented
by inverting the forward mapping. However, subclasses are free to implement both
methods if a more efficient implementation is possible.

There are several generic localizers already available that cover different
approaches to localization given the metadata available in the cumulative index
file. They are as follows (see class documentation for details):

  - :py:class:`~pdsc.localization.GeodesicLocalizer`
  - :py:class:`~pdsc.localization.FourCornerLocalizer`
  - :py:class:`~pdsc.localization.MapLocalizer`

Configuration
-------------

In addition to the snippets of Python code needed to extend PDSC, a
configuration file is required to ingest PDS cumulative index files. The
configuration file should be in YAML format containing the key-value mappings
required by a couple of methods in :py:mod:`pdsc.ingest`:

  - :py:meth:`~pdsc.ingest.store_metadata`
  - :py:meth:`~pdsc.ingest.store_segments`

The documentation of these methods describes the configuration values they
expect, and there are examples under ``config`` in the :py:mod:`pdsc` package
directory.

Ingesting with Extensions
-------------------------

To ingest a PDS cumulative index for an instrument supported by an extension,
the ``pdsc_ingest`` command-line tool should be invoked with two additional
arguments::

    $ pdsc_ingest cumulative_index.lbl /path/to/generated/index/dir/
                  -c configfile.yaml -e extension_script.py

The ``-c`` option should supply the path to the configuration file, and the
``-e`` option should supply the path to one or more Python scripts in which the
extensions have been defined. The ``pdsc_ingest`` script will invoke the
extension scripts, which should register the appropriate pieces of code with
PDSC, prior to the ingestion process.
