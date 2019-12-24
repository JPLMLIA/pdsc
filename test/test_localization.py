"""
Unit tests for Localization code
"""
import pytest
import numpy as np
from pdsc.metadata import PdsMetadata
from numpy.testing import assert_allclose
from pdsc.localization import (
    MapLocalizer, HiRiseRdrLocalizer, HiRiseRdrBrowseLocalizer, Localizer,
    xyz2latlon, get_localizer, GeodesicLocalizer, MARS_RADIUS_M
)

from .cosmic_test_tools import unit

# tolerance value defined in pixel.
TOLERANCE_PIXEL = 5.0

# tolerance value defined in degree
TOLERANCE_DEG = 5e-4

# tolerance value for size in meters
TOLERANCE_M = 1e-3

# Test case 1:
# Test pixel to lat/lon conversion for equirectangular projection.
# 
# Image id: ESP_050016_1870
# 
# Run ISIS mappt to convert points to latitude and longitude:
# 1. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=1 SAMPLE=1
# 2. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=1 SAMPLE=22023
# 3. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=23798 SAMPLE=22023
# 4. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=23798 SAMPLE=1
# 5. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=11899 SAMPLE=11012
# 
# Results:
# 1. line=1, sample=1         ==> lat=6.9937526632708, lon=69.985892127602
# 2. line=1, sample=22023     ==> lat=6.9937526632708, lon=70.079132239075
# 3. line=23798, sampe=22023  ==> lat=6.8933806899744, lon=70.079132239075
# 4. line=23798, sample=1     ==> lat=6.8933806899744, lon=69.985892127602
# 5. line=11899, sample=11012 ==> lat=6.9435687855433, lon=70.032512183339

HIRISE_ESP_050016_1870_META = PdsMetadata(
    'hirise_rdr', map_projection_type='EQUIRECTANGULAR',
    projection_center_latitude=5.0,
    projection_center_longitude=180.0,
    map_scale=0.25, line_projection_offset=1658135.5,
    sample_projection_offset=25983782.0,
    lines=23798, samples=22023,
    corner1_latitude=6.9035, corner1_longitude=70.0791,
    corner2_latitude=6.8934, corner2_longitude=69.9971,
    corner3_latitude=6.9837, corner3_longitude=69.9859,
    corner4_latitude=6.9937, corner4_longitude=70.068,
)
HIRISE_ESP_050016_1870_TEST_CASE = [
    ((6.9937526632708, 69.985892127602), (1, 1)),
    ((6.9937526632708, 70.079132239075), (1, 22023)),
    ((6.8933806899744, 70.079132239075), (23798, 22023)),
    ((6.8933806899744, 69.985892127602), (23798, 1)),
    ((6.9435687855433, 70.032512183339), (11899, 11012)),
]

# Test case 2:
# Test lat/lon to pixel conversion for equirectangular projection.
# 
# Image id: ESP_050062_1345
# 
# Run ISIS mapt to convert 5 points to line and sample:
# 1. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-44.949798974587
#          LONGITUDE=260.83910415798
# 2. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-44.949798974587
#          LONGITUDE=260.95959132319
# 3. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-45.042204321234
#          LONGITUDE=260.95959132319
# 4. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-45.042204321234
#          LONGITUDE=260.83910415798
# 5. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-44.99600164791050
#          LONGITUDE=260.899347740585
# 
# Results:
# 1. lat=-44.949798974587, lon=260.83910415798     ==> line=1.9730653911829,
#                                                      samp=2.033464346081
# 2. lat=-44.949798974587, lon=260.95959132319     ==> line=1.9730653911829,
#                                                      samp=21832.404278895
# 3. lat=-45.042204321234, lon=260.95959132319     ==> line=21857.609632041,
#                                                      samp=21832.404278895
# 4. lat=-45.042204321234, lon=260.83910415798     ==> line=21857.609632041,
#                                                      samp=2.033464346081
# 5. lat=-44.996001647910504, lon=260.899347740585 ==> line=10929.791348718,
#                                                      samp=10917.21887161
HIRISE_ESP_050062_1345_META = PdsMetadata(
    'hirise_rdr', map_projection_type='EQUIRECTANGULAR',
    projection_center_latitude=-40.0,
    projection_center_longitude=180.0,
    map_scale=0.25, line_projection_offset=-10631488.0,
    sample_projection_offset=-14646768.0,
    samples=21831, lines=21856,
)
HIRISE_ESP_050062_1345_TEST_CASE = [
    ((-44.949798974587,    260.83910415798 ), (1.9730653911829, 2.033464346081)),
    ((-44.949798974587,    260.95959132319 ), (1.9730653911829, 21832.40427889)),
    ((-45.042204321234,    260.95959132319 ), (21857.609632041, 21832.40427889)),
    ((-45.042204321234,    260.83910415798 ), (21857.609632041, 2.033464346081)),
    ((-44.996001647910504, 260.899347740585), (10929.791348718, 10917.21887161)),
]

# Test case 3:
# Test pixel to lat/lon conversion for polarstereographic projection using
# image near north pole.
# 
# Image id: ESP_045245_2675
# 
# Run ISIS mappt to convert points to latitude and longitude:
# 1. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=375 SAMPLE=1
# 2. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=2 SAMPLE=10244
# 3. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=31696 SAMPLE=11385
# 4. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=32073 SAMPLE=1142
# 5. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=16037 SAMPLE=5693
# 
# Results:
# 1. line=375, sample=1       ==> lat=87.266078122413, lon=296.01543481484
# 2. line=2, sample=10244     ==> lat=87.305746158879, lon=296.39047246968
# 3. line=31696, sample=11385 ==> lat=87.247615701464, lon=298.94304912096
# 4. line=32073, sample=1142  ==> lat=87.208765944927, lon=298.54015964047
# 5. line=16037, sample=5693  ==> lat=87.25773880432, lon=297.48428883797

HIRISE_ESP_045245_2675_META = PdsMetadata(
    'hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
    projection_center_latitude=90.0,
    projection_center_longitude=0.0,
    map_scale=0.25, line_projection_offset=-282320.0,
    sample_projection_offset=579212.0,
    samples=11385, lines=32073,
)
HIRISE_ESP_045245_2675_TEST_CASE = [
    ((87.266078122413, 296.01543481484), (375, 1)),
    ((87.305746158879, 296.39047246968), (2, 10244)),
    ((87.247615701464, 298.94304912096), (31696, 11385)),
    ((87.208765944927, 298.54015964047), (32073, 1142)),
    ((87.25773880432,  297.48428883797), (16037, 5693)),
]

# Test case 4:
# Test lat/lon to pixel conversion for polarstereographic projection using
# image near north pole.
# 
# Image id: ESP_050054_2565
# 
# Run ISIS mappt to convert 5 points to line and sample:
# 1. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.0918
#          LONGITUDE=95.545
# 2. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.0818
#          LONGITUDE=95.3689
# 3. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.291
#          LONGITUDE=95.1579
# 4. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.3011
#          LONGITUDE=95.3366
# 5. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.19145
#          LONGITUDE=95.3515
# 
# Results:
# 1. lat=76.0918, lon=95.545   ==> line=3.3481906144007,
#                                  sample=24353.96564842
# 2. lat=76.0818, lon=95.3689  ==> line=4931.2083980744,
#                                  sample=26026.240391183
# 3. lat=76.291, lon=95.1579   ==> line=13225.079025231,
#                                  sample=1667.938772222
# 4. lat=76.3011, lon=95.3366  ==> line=8295.4296541251,
#                                  sample=2.6312731597573
# 5. lat=76.19145, lon=95.3515 ==> line=6652.6553750653,
#                                  sample=13016.659884301
HIRISE_ESP_050054_2565_META = PdsMetadata(
    'hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
    projection_center_latitude=90.0,
    projection_center_longitude=0.0,
    map_scale=0.5, line_projection_offset=159167.5,
    sample_projection_offset=-1615142.5,
    samples=26027, lines=13224,
)
HIRISE_ESP_050054_2565_TEST_CASE = [
    ((76.0918 , 95.545 ), (3.3481906144007, 24353.96564842 )),
    ((76.0818 , 95.3689), (4931.2083980744, 26026.240391183)),
    ((76.291  , 95.1579), (13225.079025231, 1667.938772222 )),
    ((76.3011 , 95.3366), (8295.4296541251, 2.6312731597573)),
    ((76.19145, 95.3515), (6652.6553750653, 13016.659884301)),
]

# Test case 5:
# Test pixel to lat/lon conversion for polarstereographic projection using
# image near south pole.
# 
# Image id: ESP_049989_0930
# 
# Run ISIS mappt to convert points to latitude and longitude:
# 1. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=7940 SAMPLE=2
# 2. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=1 SAMPLE=665
# 3. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=2429 SAMPLE=30226
# 4. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=10375 SAMPLE=29560
# 5. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=5187.5 SAMPLE=15113
# 
# Results:
# 1. line=7940, sample=2       ==> lat=-86.959605211451, lon=158.25660498659
# 2. line=1, sample=665        ==> lat=-86.989790088818, lon=157.96944372902
# 3. line=2429, sample=30226   ==> lat=-86.931180262264, lon=155.87103130598
# 4. line=10375, sample=29560  ==> lat=-86.901547240436, lon=156.1734811286
# 5. line=5187.5, sample=15113 ==> lat=-86.946044198298, lon=157.05843125555
HIRISE_ESP_049989_0930_META = PdsMetadata(
    'hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
    projection_center_latitude=-90.0,
    projection_center_longitude=0.0,
    map_scale=0.25, line_projection_offset=-657861.5,
    sample_projection_offset=-265537.5,
    samples=30226, lines=10375,
)
HIRISE_ESP_049989_0930_TEST_CASE = [
    ((-86.959605211451, 158.25660498659), (7940, 2)),
    ((-86.989790088818, 157.96944372902), (1, 665)),
    ((-86.931180262264, 155.87103130598), (2429, 30226)),
    ((-86.901547240436, 156.1734811286 ), (10375, 29560)),
    ((-86.946044198298, 157.05843125555), (5187.5, 15113)),
]

# Test case 6:
# Test lat/lon to pixel conversion for polarstereographic projection using image
# near south pole.
# 
# Image id: ESP_050042_1000
# 
# Run ISIS mappt to convert 5 points to line and sample:
# 1. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.7669
#          LONGITUDE=101.843
# 2. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.7874
#          LONGITUDE=101.43
# 3. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.625
#          LONGITUDE=101.179
# 4. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.6047
#          LONGITUDE=101.587
# 5. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.69605
#          LONGITUDE=101.511
# 
# Results:
# 1. lat=-79.7669, lon=101.843  ==> line=10463.328397211,
#                                   sample=628.5909773563
# 2. lat=-79.7874, lon=101.43   ==> line=1443.6864533564,
#                                   sample=-0.33655633684248
# 3. lat=-79.625, lon=101.179   ==> line=0.37412327560014,
#                                   sample=19964.313501756
# 4. lat=-79.6047, lon=101.587  ==> line=9043.8461438996,
#                                   sample=20604.159140396
# 5. lat=-79.69605, lon=101.511 ==> line=5281.32804386,
#                                   sample=10294.632151381
HIRISE_ESP_050042_1000_META = PdsMetadata(
    'hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
    projection_center_latitude=-90.0,
    projection_center_longitude=0.0,
    map_scale=0.5, line_projection_offset=-237703.5,
    sample_projection_offset=-1182837.5,
    samples=20597, lines=10462,
)
HIRISE_ESP_050042_1000_TEST_CASE = [
    ((-79.7669 , 101.843), (10463.328397211 , 628.5909773563)),
    ((-79.7874 , 101.43 ), (1443.6864533564 , -0.33655633684248)),
    ((-79.625  , 101.179), (0.37412327560014, 19964.313501756)),
    ((-79.6047 , 101.587), (9043.8461438996 , 20604.159140396)),
    ((-79.69605, 101.511), (5281.32804386   , 10294.632151381)),
]

# The MOC test cases are regression tests; these are know to deviate from
# localization estimates provided by JMARS, etc. since they're presumably based
# on pre-computed versus reconstructed trajectories. However, JMARS was used to
# verify the correct orientation of the observation footprints relative to the
# observation center, given the orientation of the MOC browse images.
#
# During the verification process, it was observed that the localization does
# not seem to depend on whether the observation is "flipped" as indicated in the
# usage_note field. This might be cause the flipping is corrected when the
# browse image is generated. In that case, the localization applies to the
# "unflipped" version of the observation.
MOC_S2200304_META = PdsMetadata(
    'moc', usage_note='F', north_azimuth=94.13,
    lines=480, samples=480,
    center_latitude=-40.09, center_longitude=-265.03,
    image_height=118500.0, image_width=119820.0,
)
MOC_S2200304_TEST_CASE = [
    ((-39.15751239435537, 93.57704018765617), (480, 480)),
    ((-39.014031900835406, 96.17481633368809), (480, 0)),
    ((-41.005342590109564, 96.40129571345858), (0, 0)),
]

MOC_M0000110_META = PdsMetadata(
    'moc', usage_note=u'N', north_azimuth=94.59,
    lines=3968, samples=1024,
    center_latitude=-50.97, center_longitude=-159.81,
    image_height=23470.0, image_width=2850.0,
)
MOC_M0000110_TEST_CASE = [
    ((-50.77456585933269, -159.87294768415293), (3968, 1024)),
    ((-50.770734429860006, -159.797159814558), (3968, 0)),
    ((-51.16540002433904, -159.74652039353282), (0, 0)),
]

THEMIS_IR_I34619017_META = PdsMetadata(
    'themis_ir',
    center_latitude=-54.121, center_longitude=202.748,
    lines=272, samples=320, north_azimuth=100.239,
    pixel_aspect_ratio=0.845, pixel_height=102.0, pixel_width=120.0,
)
THEMIS_IR_I34619017_TEST_CASE = [
    ((-53.94804265851535, -157.86154852611733), (272, 320)),
    ((-53.83349019671131, -156.78373360980942), (272, 0)),
    ((-54.29083103668251, -156.63740954256997), (0, 0)),
]

CTX_P06_003181_0946_XI_85S260W_META = PdsMetadata(
    'ctx', north_azimuth=179.85,
    center_latitude=-85.42, center_longitude=-260.56,
    image_height=86490.0, image_width=31440.0,
    lines=14336, samples=5056, usage_note=u'F',
)
CTX_P06_003181_0946_XI_85S260W_TEST_CASE = [
    ((-85.10207160374867, 90.85528333927553), (14336, 5056)),
    ((-85.0985004494083, 108.00199482283183), (0, 5056)),
    ((-85.62209854254696, 109.05122054313493), (0, 0)),
]

CTX_T01_000849_1676_XI_12S069W_META = PdsMetadata(
    'ctx', north_azimuth=276.93,
    center_latitude=-12.45, center_longitude=-69.29,
    image_height=43530.0, image_width=25970.0,
    lines=7168, samples=5056, usage_note=u'N',
)
CTX_T01_000849_1676_XI_12S069W_TEST_CASE = [
    ((-12.111797753021992, -69.55772674321044), (7168, 0)),
    ((-12.059007889850992, -69.11293214267153), (7168, 5056)),
    ((-12.78793820020455, -69.02157480900689), (0, 5056)),
]

@unit
@pytest.mark.parametrize(
    'metadata, latlons_pixels',
    [
        (HIRISE_ESP_050016_1870_META, HIRISE_ESP_050016_1870_TEST_CASE),
        (HIRISE_ESP_050062_1345_META, HIRISE_ESP_050062_1345_TEST_CASE),
        (HIRISE_ESP_045245_2675_META, HIRISE_ESP_045245_2675_TEST_CASE),
        (HIRISE_ESP_050054_2565_META, HIRISE_ESP_050054_2565_TEST_CASE),
        (HIRISE_ESP_049989_0930_META, HIRISE_ESP_049989_0930_TEST_CASE),
        (HIRISE_ESP_050042_1000_META, HIRISE_ESP_050042_1000_TEST_CASE),
        (MOC_S2200304_META, MOC_S2200304_TEST_CASE),
        (MOC_M0000110_META, MOC_M0000110_TEST_CASE),
        (THEMIS_IR_I34619017_META, THEMIS_IR_I34619017_TEST_CASE),
        (CTX_P06_003181_0946_XI_85S260W_META,
            CTX_P06_003181_0946_XI_85S260W_TEST_CASE),
        (CTX_T01_000849_1676_XI_12S069W_META,
            CTX_T01_000849_1676_XI_12S069W_TEST_CASE),
    ]
)
def test_localizer(metadata, latlons_pixels, browse=False):
    if metadata.instrument == 'hirise_rdr':
        localizer = get_localizer(metadata, browse=browse)
    else:
        localizer = get_localizer(metadata)

    for (lat, lon), (row, col) in latlons_pixels:
        if browse:
            factor = (
                float(HiRiseRdrBrowseLocalizer.HIRISE_BROWSE_WIDTH) /
                metadata.samples
            )
            row *= factor
            col *= factor

        lat_result, lon_result = localizer.pixel_to_latlon(row, col)
        assert_allclose(
            (lat_result, lon_result % 360), (lat, lon % 360),
            atol=TOLERANCE_DEG
        )

        rowcol_result = localizer.latlon_to_pixel(lat, lon)
        assert_allclose(rowcol_result, (row, col), atol=TOLERANCE_PIXEL)

    if metadata.instrument == 'moc':
        assert_allclose(
            localizer.observation_width_m,
            metadata.image_width,
            atol=TOLERANCE_M
        )
        assert_allclose(
            localizer.observation_length_m,
            metadata.image_height,
            atol=TOLERANCE_M
        )

    if metadata.instrument == 'hirise_rdr':
        assert_allclose(
            localizer.observation_width_m,
            metadata.map_scale*metadata.samples,
            atol=TOLERANCE_M
        )
        assert_allclose(
            localizer.observation_length_m,
            metadata.map_scale*metadata.lines,
            atol=TOLERANCE_M
        )

        if not browse:
            # Run the same set of tests for the browse localizer...
            test_localizer(metadata, latlons_pixels, browse=True)

# Regression tests for all CCDs/channels for HiRISE EDRs
HIRISE_EDR_PSP_001334_2645_TEST_CASES = [
    ( 8250,  256, 1.2696, 'BG12', 0, 4, 84.3370604, -16.0018754, 0, 0),
    ( 8250,  256, 1.2696, 'BG12', 0, 4, 84.3344558, -16.0503966, 0, 256),
    ( 8250,  256, 1.2696, 'BG12', 1, 4, 84.3396948, -15.9526324, 0, 0),
    ( 8250,  256, 1.2696, 'BG12', 1, 4, 84.3370902, -16.0011762, 0, 256),
    ( 8250,  256, 1.2696, 'BG13', 0, 4, 84.3319035, -16.0979204, 0, 0),
    ( 8250,  256, 1.2696, 'BG13', 0, 4, 84.3292989, -16.1463975, 0, 256),
    ( 8250,  256, 1.2696, 'BG13', 1, 4, 84.3345458, -16.0487673, 0, 0),
    ( 8250,  256, 1.2696, 'BG13', 1, 4, 84.3319412, -16.0972670, 0, 256),
    ( 8250,  256, 1.2696, 'IR10', 0, 4, 84.3370604, -16.0018754, 0, 0),
    ( 8250,  256, 1.2696, 'IR10', 0, 4, 84.3344558, -16.0503966, 0, 256),
    ( 8250,  256, 1.2696, 'IR10', 1, 4, 84.3396948, -15.9526324, 0, 0),
    ( 8250,  256, 1.2696, 'IR10', 1, 4, 84.3370902, -16.0011762, 0, 256),
    ( 8250,  256, 1.2696, 'IR11', 0, 4, 84.3319035, -16.0979204, 0, 0),
    ( 8250,  256, 1.2696, 'IR11', 0, 4, 84.3292989, -16.1463975, 0, 256),
    ( 8250,  256, 1.2696, 'IR11', 1, 4, 84.3345458, -16.0487673, 0, 0),
    ( 8250,  256, 1.2696, 'IR11', 1, 4, 84.3319412, -16.0972670, 0, 256),
    (16500,  512, 0.6348, 'RED0', 0, 2, 84.3575326, -15.6159420, 0, 0),
    (16500,  512, 0.6348, 'RED0', 0, 2, 84.3549281, -15.6646393, 0, 512),
    (16500,  512, 0.6348, 'RED0', 1, 2, 84.3601350, -15.5663401, 0, 0),
    (16500,  512, 0.6348, 'RED0', 1, 2, 84.3575305, -15.6150600, 0, 512),
    (16500,  512, 0.6348, 'RED1', 0, 2, 84.3524379, -15.7126882, 0, 0),
    (16500,  512, 0.6348, 'RED1', 0, 2, 84.3498334, -15.7613416, 0, 512),
    (16500,  512, 0.6348, 'RED1', 1, 2, 84.3550484, -15.6631760, 0, 0),
    (16500,  512, 0.6348, 'RED1', 1, 2, 84.3524438, -15.7118519, 0, 512),
    (16500,  512, 0.6348, 'RED2', 0, 2, 84.3473277, -15.8092592, 0, 0),
    (16500,  512, 0.6348, 'RED2', 0, 2, 84.3447231, -15.8578686, 0, 512),
    (16500,  512, 0.6348, 'RED2', 1, 2, 84.3499461, -15.7598367, 0, 0),
    (16500,  512, 0.6348, 'RED2', 1, 2, 84.3473415, -15.8084687, 0, 512),
    (16500,  512, 0.6348, 'RED3', 0, 2, 84.3422018, -15.9056549, 0, 0),
    (16500,  512, 0.6348, 'RED3', 0, 2, 84.3395972, -15.9542203, 0, 512),
    (16500,  512, 0.6348, 'RED3', 1, 2, 84.3448282, -15.8563222, 0, 0),
    (16500,  512, 0.6348, 'RED3', 1, 2, 84.3422236, -15.9049101, 0, 512),
    (33000, 1024, 0.3174, 'RED4', 0, 1, 84.3370604, -16.0018754, 0, 0),
    (33000, 1024, 0.3174, 'RED4', 0, 1, 84.3344558, -16.0503966, 0, 1024),
    (33000, 1024, 0.3174, 'RED4', 1, 1, 84.3396948, -15.9526324, 0, 0),
    (33000, 1024, 0.3174, 'RED4', 1, 1, 84.3370902, -16.0011762, 0, 1024),
    (33000, 1024, 0.3174, 'RED5', 0, 1, 84.3319035, -16.0979204, 0, 0),
    (33000, 1024, 0.3174, 'RED5', 0, 1, 84.3292989, -16.1463975, 0, 1024),
    (33000, 1024, 0.3174, 'RED5', 1, 1, 84.3345458, -16.0487673, 0, 0),
    (33000, 1024, 0.3174, 'RED5', 1, 1, 84.3319412, -16.0972670, 0, 1024),
    (33000, 1024, 0.3174, 'RED6', 0, 1, 84.3267312, -16.1937901, 0, 0),
    (33000, 1024, 0.3174, 'RED6', 0, 1, 84.3241265, -16.2422230, 0, 1024),
    (33000, 1024, 0.3174, 'RED6', 1, 1, 84.3293814, -16.1447268, 0, 0),
    (33000, 1024, 0.3174, 'RED6', 1, 1, 84.3267767, -16.1931823, 0, 1024),
    (16500,  512, 0.6348, 'RED7', 0, 2, 84.3215434, -16.2894843, 0, 0),
    (16500,  512, 0.6348, 'RED7', 0, 2, 84.3189387, -16.3378729, 0, 512),
    (16500,  512, 0.6348, 'RED7', 1, 2, 84.3242015, -16.2405108, 0, 0),
    (16500,  512, 0.6348, 'RED7', 1, 2, 84.3215968, -16.2889221, 0, 512),
    (16500,  512, 0.6348, 'RED8', 0, 2, 84.3163403, -16.3850030, 0, 0),
    (16500,  512, 0.6348, 'RED8', 0, 2, 84.3137356, -16.4333473, 0, 512),
    (16500,  512, 0.6348, 'RED8', 1, 2, 84.3190062, -16.3361194, 0, 0),
    (16500,  512, 0.6348, 'RED8', 1, 2, 84.3164015, -16.3844863, 0, 512),
    (16500,  512, 0.6348, 'RED9', 0, 2, 84.3111219, -16.4803462, 0, 0),
    (16500,  512, 0.6348, 'RED9', 0, 2, 84.3085171, -16.5286461, 0, 512),
    (16500,  512, 0.6348, 'RED9', 1, 2, 84.3137956, -16.4315524, 0, 0),
    (16500,  512, 0.6348, 'RED9', 1, 2, 84.3111908, -16.4798750, 0, 512),
]

@unit
@pytest.mark.parametrize(
    'lines,samples,pixel_width,ccd_name,channel_number,binning,lat,lon,row,col',
    HIRISE_EDR_PSP_001334_2645_TEST_CASES
)
def test_hirise_edr_localizer(lines, samples, pixel_width, ccd_name,
        channel_number, binning, lat, lon, row, col):

    # This test is specifically for PSP_001334_2645
    meta = PdsMetadata(
        'hirise_edr', lines=lines, samples=samples,
        pixel_width=pixel_width, ccd_name=ccd_name,
        channel_number=channel_number, binning=binning,
        center_latitude=84.4102, center_longitude=343.495,
        north_azimuth=118.967,
    )
    latlon_rowcol = [((lat, lon), (row, col))]
    test_localizer(meta, latlon_rowcol)

@unit
def test_abstract_methods():
    with pytest.raises(TypeError):
        localizer = Localizer()

@unit
@pytest.mark.parametrize(
    'xyz,expected',
    [
        ((0, 0, 1), (90, 0)),
        ((1, 0, 0), ( 0, 0)),
        ((0, 0, 0), None),
    ]
)
def test_xyz2latlon(xyz, expected):
    if expected is None:
        pytest.raises(ValueError, xyz2latlon, xyz)
    else:
        latlon = xyz2latlon(xyz)
        assert_allclose(latlon, expected)

@unit
def test_bad_proj_types():
    loc = MapLocalizer('BAD_TYPE', 0, 0, 1, 0, 0, 1, 1)
    pytest.raises(ValueError, loc.pixel_to_latlon, 0, 0)
    pytest.raises(ValueError, loc.latlon_to_pixel, 0, 0)

@unit
def test_missing_localizer():
    meta = PdsMetadata('bad_instrument')
    pytest.raises(IndexError, get_localizer, meta)

@unit
def test_hirise_localizer_types():
    metadata = HIRISE_ESP_050016_1870_META
    latlon_expected, (row, col) = HIRISE_ESP_050016_1870_TEST_CASE[0]

    loc = get_localizer(metadata, nomap=False, browse=False)
    latlon = loc.pixel_to_latlon(row, col)
    assert_allclose(latlon, latlon_expected, atol=TOLERANCE_DEG)

    factor = (
        float(HiRiseRdrBrowseLocalizer.HIRISE_BROWSE_WIDTH) /
        metadata.samples
    )
    loc = get_localizer(metadata, nomap=False, browse=True)
    latlon = loc.pixel_to_latlon(factor*row, factor*col)
    assert_allclose(latlon, latlon_expected, atol=TOLERANCE_DEG)

    latlon_expected = [6.9035, 70.0791]
    loc = get_localizer(metadata, nomap=True, browse=False)
    latlon = loc.pixel_to_latlon(0, 0)
    assert_allclose(latlon, latlon_expected)

    loc = get_localizer(metadata, nomap=True, browse=True)
    latlon = loc.pixel_to_latlon(0, 0)
    assert_allclose(latlon, latlon_expected)

    row_col = loc.latlon_to_pixel(*latlon_expected)
    assert_allclose(row_col, [0, 0])

    pytest.raises(
        ValueError, get_localizer, metadata,
        nomap=False, browse=True, browse_width=0
    )

@unit
def test_location_mask():
    size = MARS_RADIUS_M / 360.
    loc = GeodesicLocalizer(
        center_row=5.5, center_col=2.5,
        center_lat=0.0, center_lon=0.0,
        n_rows=11, n_cols=5,
        pixel_height_m=size, pixel_width_m=size,
        north_azimuth_deg=90.0)

    mask = loc.location_mask(1, 1, reinterpolate=False)
    assert mask.shape == (11, 5, 2)
    assert_allclose(mask[0, 0, :], loc.pixel_to_latlon(0, 0))
    assert_allclose(mask[10, 4, :], loc.pixel_to_latlon(10, 4))
    center = (mask[5, 2, :] + mask[6, 3]) / 2.0
    assert_allclose(center, (0, 0))

    mask2 = loc.location_mask(2, 2, reinterpolate=False)
    assert mask2.shape == (5, 2, 2)
    assert_allclose(mask[0, 0, :], mask2[0, 0, :])

    mask3 = loc.location_mask(2, 2, reinterpolate=True)
    assert mask.shape == (11, 5, 2)
    assert_allclose(mask[0, 0, :], mask3[0, 0, :])
    center = (mask3[5, 2, :] + mask3[6, 3]) / 2.0
    assert_allclose(center, (0, 0), atol=1e-6)
