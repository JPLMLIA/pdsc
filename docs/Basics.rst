Basic Usage
===========

There are several main classes used in PDSC: clients, metadata, and localizers.
To begin, construct a client:

.. doctest::

    >>> import pdsc
    >>> client = pdsc.PdsClient()

After constructing a :py:class:`~pdsc.client.PdsClient`, call one of its methods
to query observations:

.. doctest::

    >>> metadata = client.query_by_observation_id(
    ...     'hirise_rdr', 'PSP_005423_1780'
    ... )
    >>> red_metadata = [m for m in metadata if 'RED' in m.product_id]
    >>> len(red_metadata)
    1
    >>> red_metadata[0]
    PdsMetadata(instrument='hirise_rdr', ...)

To map between pixel and latitude/longitude coordinates, construct a localizer
using the :py:meth:`~pdsc.localization.get_localizer` method:

.. doctest::

    >>> rdr_localizer = pdsc.get_localizer(red_metadata[0])
    >>> rdr_localizer.pixel_to_latlon(100, 200)
    (-1.9184998785575753, 354.44753717949027)

You can also query for observations from another instrument overlapping a given
observation:

.. doctest::

    >>> client.find_overlapping_observations(
    ...     'hirise_rdr', 'PSP_005423_1780', 'ctx'
    ... )
    [u'B02_010341_1778_XI_02S005W', ..., u'T01_000873_1780_XI_02S005W']

Or, you can query for observations of a given location:

.. doctest::

    >>> client.find_observations_of_latlon('hirise_rdr', -4.5, 137.4)
    [u'ESP_018854_1755', u'ESP_018920_1755', ..., u'PSP_010639_1755']

Finally, you can form more complex queries using conditions on metadata fields:

.. doctest::

    >>> client.query('hirise_rdr', [
    ...     ('corner1_latitude', '>', -0.5),
    ...     ('corner1_latitude', '<',  0.5)
    ... ])
    [PdsMetadata(...), ..., PdsMetadata(...)]
