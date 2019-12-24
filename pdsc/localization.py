"""
Contains code that performs "localization," or the mapping between observation
pixel coordinates and real-world latitude/longitude coordinates.

PDSC uses the convention that pixel space coordinates have their origin at the
top left of the image, with the positive :math:`x`-direction corresponding to
increasing columns and the positive :math:`y`-direction corresponding to
increasing rows. Row and column indices start at 0. The mapping from line/sample
to row/column is instrument-specific, but typically lines are rows and samples
are columns.

.. Warning::
    The localization provided by PDSC is not intended to be the most accurate
    localization possible, but rather the most accurate localization achievable
    *using only information available within PDS cumulative index files*.
    Therefore, PDSC localization often relies on assumptions that introduce
    errors whose magnitudes vary across instruments.
"""
from __future__ import division
from future.utils import with_metaclass
import abc
import numpy as np
from scipy.ndimage import zoom
from scipy.optimize import fmin
from sklearn.neighbors import DistanceMetric
# Requires geographiclib-1.49
from geographiclib.geodesic import Geodesic

from .util import registerer, standard_progress_bar

# https://tharsis.gsfc.nasa.gov/geodesy.html
MARS_RADIUS_M = 3396200.
MARS_FLATTENING = 1.0 / 169.8

LOCALIZERS = {}

register_localizer = registerer(LOCALIZERS)
"""
A decorator that can be used to register a class or function that constructs a
localizer to a particular instrument.

:param instrument: PDSC instrument name
:return: decorator that registers target to given instrument

See :ref:`Extending PDSC` for more details.
"""

def geodesic_distance(latlon1, latlon2, radius=MARS_RADIUS_M):
    """
    Computes the geodesic distance on a spherical body between two points

    :param latlon1: a pair containing the latitude and east longitude (in
        radians) of the first point
    :param latlon2: a pair containing the latitude and east longitude (in
        radians) of the second point
    :param radius: the radius (in meters) of the spherical body for which
        distance is computed (defaults to `mean Mars equatorial radius
        <https://tharsis.gsfc.nasa.gov/geodesy.html>`_)

    :return: geodesic distance (in meters) between the two given points

    >>> import numpy as np
    >>> geodesic_distance((0, 0), (0, np.pi))
    10669476.970121656
    """
    haversine = DistanceMetric.get_metric('haversine')
    return float(radius*haversine.pairwise([latlon1], [latlon2]))

def latlon2unit(latlon):
    """
    Converts a latitude, longitude pair into a vector representing that point on
    a unit circle

    :param latlon: a pair containing the latitude and east longitude (in
        degrees) of a point on a unit sphere

    :return: the Cartesian coordinates of the point on a unit sphere
    """
    llrad = np.deg2rad(latlon)
    sinll = np.sin(llrad)
    cosll = np.cos(llrad)
    return np.array([
        cosll[0]*cosll[1],
        cosll[0]*sinll[1],
        sinll[0]
    ])

def xyz2latlon(xyz):
    """
    Converts a point in Cartesian coordinates to the latitude and longitude of
    that point projected onto a unit sphere

    :param xyz: Cartesian coordinates of a nonzero point

    :return: latitude and east longitude (in degrees) of the point projected
        onto a unit sphere

    >>> xyz2latlon((0, 0, 1))
    array([90.,  0.])
    >>> xyz2latlon((1, 0, 0))
    array([0., 0.])
    >>> xyz2latlon((0, 0, 0))
    Traceback (most recent call last):
     ...
    ValueError: Point must be nonzero
    """
    norm = np.linalg.norm(xyz)
    if norm == 0:
        raise ValueError('Point must be nonzero')
    x, y, z = (xyz / norm)
    return np.rad2deg([
        np.arcsin(z),
        np.arctan2(y, x)
    ])

class Localizer(with_metaclass(abc.ABCMeta, object)):
    """
    Base class for all localizers

    Subclasses need only implement
    :py:meth:`~pdsc.localization.Localizer.pixel_to_latlon` and the reverse
    translation :py:meth:`~pdsc.localization.Localizer.latlon_to_pixel` is
    derived from it.
    """

    BODY_RADIUS = MARS_RADIUS_M
    """
    Radius of the observed body (defaults to `mean Mars equatorial radius
    <https://tharsis.gsfc.nasa.gov/geodesy.html>`_)
    """

    DEFAULT_RESOLUTION_M = 0.1
    """
    Default resolution (in meters) when optimizing the reverse mapping from
    latitude and longitude back to pixel coordinates via
    :py:meth:`~pdsc.localization.Localizer.latlon_to_pixel`
    """

    NORMALIZED_PIXEL_SPACE = False
    """
    If ``True``, pixel coordinates are defined such that (0, 0) is the top left
    corner of the image and (1, 1) is the bottom right. Otherwise, (0, 0) is the
    top left and (rows, cols) is the bottom right
    """

    @abc.abstractproperty
    def observation_width_m(self):
        """
        Total observation width (cross-track) in meters
        """
        pass # pragma: no cover

    @abc.abstractproperty
    def observation_length_m(self):
        """
        Total observation length (along-track) in meters
        """
        pass # pragma: no cover

    @abc.abstractmethod
    def pixel_to_latlon(self, row, col):
        """
        Converts pixel coordinates to latitude and longitude coordinates within
        an observation

        :param row: image row, starting at 0 at the top of the image
        :param col: image column, starting at 0 at the left of the image

        .. Note::
            If :py:attr:`~Localizer.NORMALIZED_PIXEL_SPACE` for this localizer
            is ``False``, then the pixel coordinates range from zero to one less
            than the number of total rows/columns in the image. Otherwise, the
            pixel coordinates range from zero to one along each dimension.
        """
        pass # pragma: no cover

    def latlon_to_pixel(self, lat, lon, resolution_m=None, resolution_pix=0.1):
        """
        Converts a latitude and longitude location to pixel coordinates within
        an observation

        :param lat:
            latitude (in degrees)
        :param lon:
            east longitude (in degrees)
        :param resolution_m:
            the resolution (in meters) when optimizing the mapping from latitude
            and longitude to pixel coordinates; if ``None``, the value defaults
            to :py:attr:`~Localizer.DEFAULT_RESOLUTION_M`
        :param resolution_pix:
            the resolution (in pixels) when optimizing the mapping from latitude
            and longitude to pixel coordinates

        :return: the tuple containing the row and column of the specified
            location to within the stricter of the two resolution requirements
        """
        if resolution_m is None: resolution_m = self.DEFAULT_RESOLUTION_M

        loc = np.deg2rad([lat, lon])

        def f(u):
            loc_u = np.deg2rad(self.pixel_to_latlon(*u))
            return geodesic_distance(loc, loc_u, self.BODY_RADIUS)

        u0 = (0, 0)
        ustar = fmin(f, u0, xtol=resolution_pix, ftol=resolution_m, disp=False)
        return tuple(ustar)

class GeodesicLocalizer(Localizer):
    """
    The :py:class:`GeodesicLocalizer` is a type of localizer that is used when
    observation locations are described in terms of a center latitude/longitude
    and a line-of-flight direction. This localizer assumes that along-track
    pixels in the center column of the observaton roughly follow a geodesic path
    in the direction of flight and cross-track pixels in each row are
    perpendicular to this path.
    """

    BODY = Geodesic(MARS_RADIUS_M, MARS_FLATTENING)
    """
    A :py:class:`~geographiclib.geodesic.Geodesic` object describing the target
    body
    """

    def __init__(self, center_row, center_col, center_lat, center_lon,
            n_rows, n_cols, pixel_height_m, pixel_width_m,
            north_azimuth_deg, flight_direction=1):
        """
        :param center_row:
            the center row of the observation
        :param center_col:
            the center column of the observation
        :param center_lat:
            the latitude (in degrees) of the pixel at the center of the
            observation
        :param center_lat:
            the longitude (east, in degrees) of the pixel at the center of the
            observation
        :param n_rows:
            the total number of rows in the observation
        :param n_cols:
            the total number of columns in the observation
        :param pixel_height_m:
            the pixel height (in meters)
        :param pixel_width_m:
            the pixel width (in meters)
        :param north_azimuth_deg:
            the clockwise angle (in degrees) from a vector that points 90
            degrees counter-clockwise from the line-of-flight direction to north
        :param flight_direction:
            a multiplicative factor indicating the direction of flight relative
            to the :math:`y`-direction in pixel space; if
            ``flight_direction=1``, then the flight direction is from the the
            top down, whereas ``flight_direction=-1`` indicates a bottom-up
            direction of flight

        .. Note::
            If :py:attr:`~Localizer.NORMALIZED_PIXEL_SPACE` for this localizer
            is ``True``, then the pixel coordinates range from zero to one.
            Consequently, the attributes :py:attr:`~GeodesicLocalizer.n_cols`
            and :py:attr:`~GeodesicLocalizer.n_rows` are both equal to one, and
            the attributes :py:attr:`~GeodesicLocalizer.pixel_width_m` and
            :py:attr:`~GeodesicLocalizer.pixel_height_m` are both the width and
            height of the *entire* observation.
        """

        if n_rows <= 0: raise ValueError('No image rows')
        if n_cols <= 0: raise ValueError('No image columns')
        if pixel_height_m <= 0: raise ValueError('Negative pixel height')
        if pixel_width_m <= 0: raise ValueError('Negative pixel width')

        self.center_row = center_row
        self.center_col = center_col
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.pixel_height_m = pixel_height_m
        self.pixel_width_m = pixel_width_m
        self.north_azimuth_deg = north_azimuth_deg
        self.flight_direction = flight_direction
        self._height = None
        self._width = None

    @property
    def observation_width_m(self):
        if self._width is None:
            self._width = self.pixel_width_m*self.n_cols
        return self._width

    @property
    def observation_length_m(self):
        if self._height is None:
            self._height = self.pixel_height_m*self.n_rows
        return self._height

    def pixel_to_latlon(self, row, col):
        x_m = (col - self.center_col) * self.pixel_width_m
        y_m = (row - self.center_row) * self.pixel_height_m
        y_m *= self.flight_direction

        flight_line_point = self.BODY.Direct(
            self.center_lat, self.center_lon,
            90 - self.north_azimuth_deg,
            y_m
        )

        cross_line_point = self.BODY.Direct(
            flight_line_point['lat2'],
            flight_line_point['lon2'],
            flight_line_point['azi2'] - 90,
            x_m
        )

        return cross_line_point['lat2'], cross_line_point['lon2']

    def location_mask(self, subsample_rows=10, subsample_cols=25,
            reinterpolate=True, verbose=False):
        """
        Compute a latitude and longitude for every pixel in an observation (with
        subsampling/reinterpolation to increase efficiency)

        :param subsample_rows: only compute location once every this many rows
        :param subsample_cols: only compute location once every this many
            columns
        :param reinterpolate: if subsampling is used, reinterpolate values for
            skipped pixels
        :param verbose: if ``True``, display a progress bar

        :return: a :py:class:`numpy.array` containing the latitude and east
            longitude (in degrees) along the last dimension for every pixel in
            the image, modulo subsampling

        .. Warning::
            This function is experimental and the reinterpolation step does not
            correctly handle discontinuities that arise near the "date line" or
            the poles.
        """
        nrows = int(np.ceil(self.n_rows // subsample_rows))
        ncols = int(np.ceil(self.n_cols // subsample_cols))

        progress = standard_progress_bar('Computing Location Mask', verbose)
        L = np.array([
            [self.pixel_to_latlon(r, c)
                for c in np.linspace(0, self.n_cols - 1, ncols)]
            for r in progress(np.linspace(0, self.n_rows - 1, nrows))
        ])
        if reinterpolate:
            zoom_factor = (
                float(self.n_rows) / L.shape[0],
                float(self.n_cols) / L.shape[1]
            )
            L = np.dstack([
                zoom(L[..., 0], zoom_factor, order=1, mode='nearest'),
                zoom(L[..., 1], zoom_factor, order=1, mode='nearest')
            ])
        return L

class FourCornerLocalizer(GeodesicLocalizer):
    """
    The :py:class:`FourCornerLocalizer` is a type of localizer that is used when
    observation locations are described using the latitude and longitude of the
    four corners of the observation.
    """

    def __init__(self, corners, n_rows, n_cols, flight_direction):
        """
        :param corners:
            an ordered collection of the four image corners, each a latitude and
            east longitude pair (in degrees); the order of the corners is:

                - top left
                - bottom left
                - bottom right
                - top right

        :param n_rows: the number of rows in the image
        :param n_cols: the number of columns in the image
        :param flight_direction:
            a multiplicative factor indicating the direction of flight relative
            to the :math:`y`-direction in pixel space; if
            ``flight_direction=1``, then the flight direction is from the the
            top down, whereas ``flight_direction=-1`` indicates a bottom-up
            direction of flight
        """

        if n_rows <= 0: raise ValueError('No image rows')
        if n_cols <= 0: raise ValueError('No image columns')

        self.n_rows = n_rows
        self.n_cols = n_cols
        self.flight_direction = flight_direction

        self.corners = np.asarray(corners)
        self.corner_matrix = np.array([
            [latlon2unit(corners[0]), latlon2unit(corners[3])],
            [latlon2unit(corners[1]), latlon2unit(corners[2])],
        ])

        corners = np.deg2rad(corners)
        self.pixel_height_m = (
            (
                geodesic_distance(corners[0], corners[3]) +
                geodesic_distance(corners[1], corners[2])
            ) / (2*n_rows)
        )
        self.pixel_width_m = (
            (
                geodesic_distance(corners[0], corners[1]) +
                geodesic_distance(corners[2], corners[3])
            ) / (2*n_cols)
        )

        self._height = None
        self._width = None

    def pixel_to_latlon(self, row, col):
        # Use bi-linear interpolation
        C = self.corner_matrix
        dx = np.array([self.n_cols - col, col])
        dy = np.array([self.n_rows - row, row])
        interpolated = np.array([
            np.dot(dx, np.dot(C[..., dim], dy.T))
            for dim in range(3)
        ]) / float(self.n_rows*self.n_cols)
        return tuple(xyz2latlon(interpolated))

class MapLocalizer(Localizer):
    """
    The :py:class:`MapLocalizer` supports map-projected observations.
    Specifically, it supports the EQUIRECTANGULAR and POLAR STEREOGRAPHIC
    projection types used for HiRISE observations.
    """

    MARS_RADIUS_POLAR = 3376200
    """
    The Mars polar radius used for `HiRISE map projections
    <https://hirise-pds.lpl.arizona.edu/PDS/CATALOG/DSMAP.CAT>`_
    """

    MARS_RADIUS_EQUATORIAL = 3396190
    """
    The Mars equatorial radius used for `HiRISE map projections
    <https://hirise-pds.lpl.arizona.edu/PDS/CATALOG/DSMAP.CAT>`_
    """

    def __init__(self, proj_type, proj_latitude, proj_longitude,
                 map_scale, row_offset, col_offset, lines, samples):
        """
        :param proj_type: map projection type
        :param proj_latitude: projection center latitude
        :param proj_longitude: projection center longitude
        :param map_scale: projection map scale (meters)
        :param row_offset: projection row offset
        :param col_offset: projection col offset
        :param lines: total observation lines (rows)
        :param samples: total observation samples (columns)

        See https://hirise-pds.lpl.arizona.edu/PDS/CATALOG/DSMAP.CAT for a
        further description of these parameters.
        """
        self.proj_type = proj_type
        self.proj_latitude = np.deg2rad(proj_latitude)
        self.proj_longitude = np.deg2rad(proj_longitude)
        self.map_scale = map_scale
        self.row_offset = row_offset
        self.col_offset = col_offset
        self.lines = lines
        self.samples = samples
        self._width = None
        self._height = None

        a = self.MARS_RADIUS_POLAR*np.cos(self.proj_latitude)
        b = self.MARS_RADIUS_EQUATORIAL*np.sin(self.proj_latitude)
        self.R = (
            (self.MARS_RADIUS_POLAR*self.MARS_RADIUS_EQUATORIAL) /
            np.sqrt(a**2 + b**2)
        )
        self.cos_proj_lat = np.cos(self.proj_latitude)

    def _equirect_pixel_to_latlon(self, row, col):
        x = (col - self.col_offset)*self.map_scale
        y = -(row - self.row_offset)*self.map_scale
        return (
            np.rad2deg(y / self.R),
            np.rad2deg(
                self.proj_longitude + x / (self.R*self.cos_proj_lat)
            )
        )

    def _equirect_latlon_to_pixel(self, lat, lon):
        lat_rad = np.deg2rad(lat)
        lon_rad = np.deg2rad(lon % 360.)
        x = self.R*(lon_rad - self.proj_longitude)*self.cos_proj_lat
        y = self.R*lat_rad
        row = (-y / self.map_scale) + self.row_offset
        col = (x / self.map_scale) + self.col_offset
        return row, col

    def _polar_pixel_to_latlon(self, row, col):
        x = (col - self.col_offset)*self.map_scale
        y = -(row - self.row_offset)*self.map_scale
        P = np.sqrt(x**2 + y**2)
        C = 2*np.arctan(P / (2*self.MARS_RADIUS_POLAR))
        lon = np.rad2deg(
            self.proj_longitude +
            np.arctan2(x, -np.sign(self.proj_latitude)*y)
        )
        lat = np.rad2deg(np.arcsin(
            np.cos(C)*np.sin(self.proj_latitude) +
            y*np.sin(C)*np.cos(self.proj_latitude)/P
        ))
        return lat, lon

    def _polar_latlon_to_pixel(self, lat, lon):
        lat_rad = np.deg2rad(lat)
        lon_rad = np.deg2rad(lon % 360.)
        T = np.tan((np.pi / 4.0) - np.abs(lat_rad / 2.0))
        A = 2*self.MARS_RADIUS_POLAR*T
        x = A*np.sin(lon_rad - self.proj_longitude)
        y = -A*np.cos(lon_rad - self.proj_longitude)*np.sign(self.proj_latitude)
        row = (-y / self.map_scale) + self.row_offset
        col = (x / self.map_scale) + self.col_offset
        return row, col

    @property
    def observation_width_m(self):
        if self._width is None:
            self._width = self.samples*self.map_scale
        return self._width

    @property
    def observation_length_m(self):
        if self._height is None:
            self._height = self.lines*self.map_scale
        return self._height

    def pixel_to_latlon(self, row, col):
        if self.proj_type == 'EQUIRECTANGULAR':
            return self._equirect_pixel_to_latlon(row, col)
        elif self.proj_type == 'POLAR STEREOGRAPHIC':
            return self._polar_pixel_to_latlon(row, col)
        else:
            raise ValueError('Unknown projection type "%s"' % self.proj_type)

    def latlon_to_pixel(self, lat, lon):
        if self.proj_type == 'EQUIRECTANGULAR':
            return self._equirect_latlon_to_pixel(lat, lon)
        elif self.proj_type == 'POLAR STEREOGRAPHIC':
            return self._polar_latlon_to_pixel(lat, lon)
        else:
            raise ValueError('Unknown projection type "%s"' % self.proj_type)

@register_localizer('ctx')
class CtxLocalizer(GeodesicLocalizer):
    """
    A localizer for the CTX instrument (subclass of
    :py:class:`GeodesicLocalizer`)
    """

    DEFAULT_RESOLUTION_M = 1e-3
    """
    Sets the default resolution for CTX localization
    """

    BODY = Geodesic(MARS_RADIUS_M, 0.0) # Works better assuming sphere
    """
    Uses a Geodesic model for CTX that assumes Mars is spherical, which seems to
    work better in practice.
    """

    def __init__(self, metadata):
        """
        :param metadata:
            "ctx" :py:class:`~pdsc.metadata.PdsMetadata` object
        """
        flipped_na = (180 - metadata.north_azimuth
            if metadata.usage_note == 'F' else metadata.north_azimuth)
        super(CtxLocalizer, self).__init__(
            metadata.lines / 2.0, metadata.samples / 2.0,
            metadata.center_latitude, metadata.center_longitude,
            metadata.lines, metadata.samples,
            metadata.image_height / metadata.lines,
            metadata.image_width / metadata.samples,
            flipped_na, -1
        )

@register_localizer('themis_vis')
@register_localizer('themis_ir')
class ThemisLocalizer(GeodesicLocalizer):
    """
    A localizer for the THEMIS VIS and IR instruments (subclass of
    :py:class:`GeodesicLocalizer`)
    """

    DEFAULT_RESOLUTION_M = 1e-3
    """
    Sets the default resolution for THEMIS localization
    """

    def __init__(self, metadata):
        """
        :param metadata:
            "themis_ir" or "themis_vis" :py:class:`~pdsc.metadata.PdsMetadata`
            object
        """
        super(ThemisLocalizer, self).__init__(
            metadata.lines / 2.0, metadata.samples / 2.0,
            metadata.center_latitude, metadata.center_longitude,
            metadata.lines, metadata.samples,
            metadata.pixel_aspect_ratio*metadata.pixel_width,
            metadata.pixel_width,
            metadata.north_azimuth, 1
        )

@register_localizer('hirise_edr')
class HiRiseLocalizer(GeodesicLocalizer):
    """
    A localizer for the HiRISE EDR observations (subclass of
    :py:class:`GeodesicLocalizer`)
    """

    DEFAULT_RESOLUTION_M = 1e-6
    """
    Sets the default resolution for HiRISE EDR localization
    """

    # Each CCD is 2048 pixels across, but they overlap
    # by 48 pixels.
    CCD_TABLE = {
        'RED0': -9000,
        'RED1': -7000,
        'RED2': -5000,
        'RED3': -3000,
        'RED4': -1000,
        'RED5':  1000,
        'RED6':  3000,
        'RED7':  5000,
        'RED8':  7000,
        'RED9':  9000,
        'IR10': -1000,
        'IR11':  1000,
        'BG12': -1000,
        'BG13':  1000,
    }
    """
    A mapping from HiRISE CCDs to pixel offsets from the center of the
    observation. Each CCD is 2048 pixels across, but they overlap by 48 pixels.

    See Figure 2.1.b in the `HiRISE EDR SIS
    <https://hirise.lpl.arizona.edu/pdf/HiRISE_EDR_SIS.pdf>`_.
    """

    CHANNEL_OFFSET = {
        0:  512,
        1: -512,
    }
    """
    Each HiRISE CCD is split into two channels, each 1024 pixels of the full
    2048-pixel CCD. Within a CCD, this dictionary defines a mapping from channel
    to the offset of the center pixel within that channel.

    See Figure 2.1.b in the `HiRISE EDR SIS
    <https://hirise.lpl.arizona.edu/pdf/HiRISE_EDR_SIS.pdf>`_.
    """

    def __init__(self, metadata):
        """
        :param metadata:
            "hirise_edr" :py:class:`~pdsc.metadata.PdsMetadata` object
        """
        helper_localizer = GeodesicLocalizer(
            metadata.lines / 2.0, metadata.samples / 2.0,
            metadata.center_latitude, metadata.center_longitude,
            metadata.lines, metadata.samples,
            metadata.pixel_width,
            metadata.pixel_width,
            metadata.north_azimuth, 1
        )
        edr_center_col = float(
            self.CCD_TABLE[metadata.ccd_name] +
            self.CHANNEL_OFFSET[metadata.channel_number]
        ) / metadata.binning
        edr_center_lat, edr_center_lon = helper_localizer.pixel_to_latlon(
            metadata.lines / 2.0, edr_center_col)

        super(HiRiseLocalizer, self).__init__(
            metadata.lines / 2.0, metadata.samples / 2.0,
            edr_center_lat, edr_center_lon,
            metadata.lines, metadata.samples,
            metadata.pixel_width,
            metadata.pixel_width,
            metadata.north_azimuth, 1
        )

class HiRiseRdrNoMapLocalizer(FourCornerLocalizer):
    """
    A localizer for the HiRISE RDR NOMAP observations (subclass of
    :py:class:`FourCornerLocalizer`)
    """

    DEFAULT_RESOLUTION_M = 1e-6
    """
    Sets the default resolution for HiRISE NOMAP localization
    """

    NORMALIZED_PIXEL_SPACE = True
    """
    The HiRISE RDR cumulative index metadata does not contain information about
    the size of the NOMAP data product. Therefore, we must use a normalized
    pixel space for these observations.
    """

    def __init__(self, metadata):
        """
        :param metadata:
            "hirise_rdr" :py:class:`~pdsc.metadata.PdsMetadata` object
        """
        corners = np.array([
            [metadata.corner1_latitude, metadata.corner1_longitude],
            [metadata.corner2_latitude, metadata.corner2_longitude],
            [metadata.corner3_latitude, metadata.corner3_longitude],
            [metadata.corner4_latitude, metadata.corner4_longitude],
        ])
        super(HiRiseRdrNoMapLocalizer, self).__init__(
            corners, 1.0, 1.0, 1
        )

class HiRiseRdrLocalizer(MapLocalizer):
    """
    A localizer for the HiRISE RDR (map-projected) observations (subclass of
    :py:class:`MapLocalizer`)
    """

    DEFAULT_RESOLUTION_M = 1e-6
    """
    Sets the default resolution for HiRISE RDR localization, although this
    attribute is not used for the :py:class:`MapLocalizer`
    """

    def __init__(self, metadata):
        """
        :param metadata:
            "hirise_rdr" :py:class:`~pdsc.metadata.PdsMetadata` object
        """
        super(HiRiseRdrLocalizer, self).__init__(
            metadata.map_projection_type,
            metadata.projection_center_latitude,
            metadata.projection_center_longitude,
            metadata.map_scale,
            metadata.line_projection_offset,
            metadata.sample_projection_offset,
            metadata.lines,
            metadata.samples
        )

class HiRiseRdrBrowseLocalizer(HiRiseRdrLocalizer):
    """
    A localizer for the HiRISE RDR (map-projected) "browse" images (subclass of
    :py:class:`HiRiseRdrLocalizer`)

    This classifier is included for convenience; it simply scales the pixel
    coordinates of the browse image to/from those of the full image before/after
    calling the super-class implementation.
    """

    HIRISE_BROWSE_WIDTH = 2048
    """
    The default width of HiRISE browse images
    """

    def __init__(self, metadata, browse_width):
        """
        :param metadata:
            "hirise_rdr" :py:class:`~pdsc.metadata.PdsMetadata` object
        :param browse_width:
            the width of the HiRISE browse image (if it varies from the default
            value)
        """
        super(HiRiseRdrBrowseLocalizer, self).__init__(metadata)
        self.scale_factor = float(browse_width) / metadata.samples
        if self.scale_factor <= 0:
            raise ValueError('Invalid scale factor: %f' % self.scale_factor)

    def pixel_to_latlon(self, row, col):
        return super(HiRiseRdrBrowseLocalizer, self).pixel_to_latlon(
            row / self.scale_factor, col / self.scale_factor
        )

    def latlon_to_pixel(self, lat, lon):
        pix = super(HiRiseRdrBrowseLocalizer, self).latlon_to_pixel(lat, lon)
        return pix[0]*self.scale_factor, pix[1]*self.scale_factor

@register_localizer('hirise_rdr')
def hirise_rdr_localizer(metadata, nomap=False, browse=False,
                         browse_width=HiRiseRdrBrowseLocalizer.HIRISE_BROWSE_WIDTH):
    """
    Constructs the appropriate HiRISE RDR localizer for the desired data
    product type

    :param metadata:
        "hirise_rdr" :py:class:`~pdsc.metadata.PdsMetadata` object
    :param nomap:
        construct localizer for the NOMAP (non-map-projected) data product
    :param browse:
        construct localizer for the BROWSE data product
    :param browse_width:
        if ``browse=True``, use this value as the width of the browse image

    :return: a :py:class:`Localizer` for the appropriate data product
    """
    if nomap:
        return HiRiseRdrNoMapLocalizer(metadata)
    else:
        if browse:
            return HiRiseRdrBrowseLocalizer(metadata, browse_width)
        else:
            return HiRiseRdrLocalizer(metadata)

@register_localizer('moc')
class MocLocalizer(GeodesicLocalizer):
    """
    A localizer for the MOC observations (subclass of
    :py:class:`GeodesicLocalizer`)
    """

    DEFAULT_RESOLUTION_M = 1e-3
    """
    Sets the default resolution for MOC localization
    """

    BODY = Geodesic(MARS_RADIUS_M, 0.0)
    """
    Uses a Geodesic model for MOC that assumes Mars is spherical, which seems to
    work better in practice.
    """

    def __init__(self, metadata):
        """
        :param metadata:
            "moc" :py:class:`~pdsc.metadata.PdsMetadata` object
        """
        super(MocLocalizer, self).__init__(
            metadata.lines / 2.0, metadata.samples / 2.0,
            metadata.center_latitude, metadata.center_longitude,
            metadata.lines, metadata.samples,
            metadata.image_height / metadata.lines,
            metadata.image_width / metadata.samples,
            metadata.north_azimuth, 1
        )

def get_localizer(metadata, *args, **kwargs):
    """
    Get a localizer for an observation corresponding to the provided metadata

    :param metadata:
        a :py:class:`~pdsc.metadata.PdsMetadata` object for an observation
    :param \*args:
        additional args provided to the localizer constructor
    :param \**kwargs:
        additional kwargs provided to the localizer constructor

    :return: a :py:class:`Localizer` for the observation

    .. Note::
        The :py:meth:`get_localizer` method determines the appropriate localizer
        to use for the observation by looking for the class or function that was
        registered to the instrument using the :py:meth:`register_localizer`
        decorator. See :ref:`Extending PDSC` for more details.
    """
    if metadata.instrument not in LOCALIZERS:
        raise IndexError(
            'No localizer implemented for %s' % metadata.instrument)

    return LOCALIZERS[metadata.instrument](metadata, *args, **kwargs)
