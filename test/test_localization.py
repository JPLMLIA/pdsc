"""
Unit tests for Localization code
"""
import pytest
import numpy as np
from pdsc.metadata import PdsMetadata
from cosmic_test_tools import unit
from numpy.testing import assert_allclose
from pdsc.localization import (
    MapLocalizer, HiRiseRdrLocalizer, HiRiseRdrBrowseLocalizer, Localizer
)

# tolerance value defined in pixel.
TOLERANCE_PIXEL = 5.0

# tolerance value defined in degree
TOLERANCE_DEG = 5 * 1e-4

# tolerance value for size in meters
TOLERANCE_M = 1e-3

@unit
def test_hiriserdrbrowselocalizer_equirectangular_pixel_to_latlon():
    '''
    Test case 1:
    Test pixel to lat/lon conversion for equirectangular projection.

    Image id: ESP_050016_1870

    Run ISIS mappt to convert points to latitude and longitude:
    1. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=1 SAMPLE=1
    2. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=1 SAMPLE=22023
    3. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=23798 SAMPLE=22023
    4. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=23798 SAMPLE=1
    5. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=11899 SAMPLE=11012

    Results:
    1. line=1, sample=1         ==> lat=6.9937526632708, lon=69.985892127602
    2. line=1, sample=22023     ==> lat=6.9937526632708, lon=70.079132239075
    3. line=23798, sampe=22023  ==> lat=6.8933806899744, lon=70.079132239075
    4. line=23798, sample=1     ==> lat=6.8933806899744, lon=69.985892127602
    5. line=11899, sample=11012 ==> lat=6.9435687855433, lon=70.032512183339
    '''

    # full size HiRISE image size
    full_size = (23798.0, 22023.0)
    map_scale = 0.25

    # ratio between full size and browse image
    ratio = full_size[1] / 2048.0

    # points to test
    # the following points are line/samp values defined in browse image
    ul_pixel = [1.0 / ratio, 1.0 / ratio]
    ur_pixel = [1.0 / ratio, full_size[1] / ratio]
    br_pixel = [full_size[0] / ratio, full_size[1] / ratio]
    bl_pixel = [full_size[0] / ratio, 1.0 / ratio]
    center_pixel = [full_size[0] / ratio / 2.0, full_size[1] / ratio / 2.0]

    # expected lat/lon values
    ul_latlon_expected = [6.9937526632708, 69.985892127602]
    ur_latlon_expected = [6.9937526632708, 70.079132239075]
    br_latlon_expected = [6.8933806899744, 70.079132239075]
    bl_latlon_expected = [6.8933806899744, 69.985892127602]
    center_latlon_expected = [6.9435687855433, 70.032512183339]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='EQUIRECTANGULAR',
                           projection_center_latitude=5.0,
                           projection_center_longitude=180.0,
                           map_scale=map_scale, line_projection_offset=1658135.5,
                           sample_projection_offset=25983782.0,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrBrowseLocalizer(metadata, 2048)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert pixel to lat/lon
    ul_latlon = localizer.pixel_to_latlon(ul_pixel[0], ul_pixel[1])
    ur_latlon = localizer.pixel_to_latlon(ur_pixel[0], ur_pixel[1])
    br_latlon = localizer.pixel_to_latlon(br_pixel[0], br_pixel[1])
    bl_latlon = localizer.pixel_to_latlon(bl_pixel[0], bl_pixel[1])
    center_latlon = localizer.pixel_to_latlon(center_pixel[0], center_pixel[1])

    # convert to positive east 360 longitude
    ul_latlon = list(ul_latlon)
    ur_latlon = list(ur_latlon)
    br_latlon = list(br_latlon)
    bl_latlon = list(bl_latlon)
    center_latlon = list(center_latlon)
    ul_latlon[1] = ul_latlon[1] % 360
    ur_latlon[1] = ur_latlon[1] % 360
    br_latlon[1] = br_latlon[1] % 360
    bl_latlon[1] = bl_latlon[1] % 360
    center_latlon[1] = center_latlon[1] % 360

    # test upper left corner
    assert_allclose(ul_latlon, ul_latlon_expected, atol=TOLERANCE_DEG)

    # test upper right corner
    assert_allclose(ur_latlon, ur_latlon_expected, atol=TOLERANCE_DEG)

    # test bottom right corner
    assert_allclose(br_latlon, br_latlon_expected, atol=TOLERANCE_DEG)

    # test bottom left corner
    assert_allclose(bl_latlon, bl_latlon_expected, atol=TOLERANCE_DEG)

    # test center
    assert_allclose(center_latlon, center_latlon_expected, atol=TOLERANCE_DEG)

@unit
def test_hiriserdrbrowselocalizer_equirectangular_latlon_to_pixel():
    '''
    Test case 2:
    Test lat/lon to pixel conversion for equirectangular projection.

    Image id: ESP_050062_1345

    Run ISIS mapt to convert 5 points to line and sample:
    1. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-44.949798974587
             LONGITUDE=260.83910415798
    2. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-44.949798974587
             LONGITUDE=260.95959132319
    3. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-45.042204321234
             LONGITUDE=260.95959132319
    4. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-45.042204321234
             LONGITUDE=260.83910415798
    5. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-44.99600164791050
             LONGITUDE=260.899347740585

    Results:
    1. lat=-44.949798974587, lon=260.83910415798     ==> line=1.9730653911829,
                                                         samp=2.033464346081
    2. lat=-44.949798974587, lon=260.95959132319     ==> line=1.9730653911829,
                                                         samp=21832.404278895
    3. lat=-45.042204321234, lon=260.95959132319     ==> line=21857.609632041,
                                                         samp=21832.404278895
    4. lat=-45.042204321234, lon=260.83910415798     ==> line=21857.609632041,
                                                         samp=2.033464346081
    5. lat=-44.996001647910504, lon=260.899347740585 ==> line=10929.791348718,
                                                         samp=10917.21887161
    '''

    # full size HiRISE image size
    full_size = (21856.0, 21831.0)
    map_scale = 0.25

    # ratio between full size and browse image
    ratio = full_size[1] / 2048.0

    # points to test
    # the following points are lat/lon values
    ul_latlon = [-44.949798974587, 260.83910415798]
    ur_latlon = [-44.949798974587, 260.95959132319]
    br_latlon = [-45.042204321234, 260.95959132319]
    bl_latlon = [-45.042204321234, 260.83910415798]
    center_latlon = [-44.996001647910504, 260.899347740585]

    # expected line/samp values
    ul_pixel_expected = [1.9730653911829 / ratio, 2.033464346081 / ratio]
    ur_pixel_expected = [1.9730653911829 / ratio, 21832.404278895 / ratio]
    br_pixel_expected = [21857.609632041 / ratio, 21832.404278895 / ratio]
    bl_pixel_expected = [21857.609632041 / ratio, 2.033464346081 / ratio]
    center_pixel_expected = [10929.791348718 / ratio, 10917.21887161 / ratio]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='EQUIRECTANGULAR',
                           projection_center_latitude=-40.0,
                           projection_center_longitude=180.0,
                           map_scale=map_scale, line_projection_offset=-10631488.0,
                           sample_projection_offset=-14646768.0,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrBrowseLocalizer(metadata, 2048)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert lat/lon to pixel
    ul_pixel = localizer.latlon_to_pixel(ul_latlon[0], ul_latlon[1])
    ur_pixel = localizer.latlon_to_pixel(ur_latlon[0], ur_latlon[1])
    br_pixel = localizer.latlon_to_pixel(br_latlon[0], br_latlon[1])
    bl_pixel = localizer.latlon_to_pixel(bl_latlon[0], bl_latlon[1])
    center_pixel = localizer.latlon_to_pixel(center_latlon[0],
                                             center_latlon[1])

    # test upper left corner
    assert_allclose(ul_pixel, ul_pixel_expected, atol=TOLERANCE_PIXEL)

    # test upper right corner
    assert_allclose(ur_pixel, ur_pixel_expected, atol=TOLERANCE_PIXEL)

    # test bottom right corner
    assert_allclose(br_pixel, br_pixel_expected, atol=TOLERANCE_PIXEL)

    # test bottom left corner
    assert_allclose(bl_pixel, bl_pixel_expected, atol=TOLERANCE_PIXEL)

    # test center
    assert_allclose(center_pixel, center_pixel_expected,
                    atol=TOLERANCE_PIXEL)

@unit
def test_hiriserdrbrowselocalizer_polarstereographic_pixel_to_latlon_northpole():
    '''
    Test case 3:
    Test pixel to lat/lon conversion for polarstereographic projection using
    image near north pole.

    Image id: ESP_045245_2675

    Run ISIS mappt to convert points to latitude and longitude:
    1. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=375 SAMPLE=1
    2. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=2 SAMPLE=10244
    3. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=31696 SAMPLE=11385
    4. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=32073 SAMPLE=1142
    5. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=16037 SAMPLE=5693

    Results:
    1. line=375, sample=1       ==> lat=87.266078122413, lon=296.01543481484
    2. line=2, sample=10244     ==> lat=87.305746158879, lon=296.39047246968
    3. line=31696, sample=11385 ==> lat=87.247615701464, lon=298.94304912096
    4. line=32073, sample=1142  ==> lat=87.208765944927, lon=298.54015964047
    5. line=16037, sample=5693  ==> lat=87.25773880432, lon=297.48428883797
    '''

    # full size HiRISE image size
    full_size = (32073.0, 11385.0)
    map_scale = 0.25

    # ratio between full size and browse image
    ratio = full_size[1] / 2048.0

    # points to test
    # the following points are line/samp values defined in browse image
    p1_pixel = [375.0 / ratio, 1.0 / ratio]
    p2_pixel = [2.0 / ratio, 10244.0 / ratio]
    p3_pixel = [31696.0 / ratio, 11385.0 /ratio]
    p4_pixel = [32073.0 / ratio, 1142.0 / ratio]
    p5_pixel = [full_size[0] / ratio / 2.0, full_size[1] / ratio / 2.0]

    # expected lat/lon values
    p1_latlon_expected = [87.266078122413, 296.01543481484]
    p2_latlon_expected = [87.305746158879, 296.39047246968]
    p3_latlon_expected = [87.247615701464, 298.94304912096]
    p4_latlon_expected = [87.208765944927, 298.54015964047]
    p5_latlon_expected = [87.25773880432, 297.48428883797]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
                           projection_center_latitude=90.0,
                           projection_center_longitude=0.0,
                           map_scale=map_scale, line_projection_offset=-282320.0,
                           sample_projection_offset=579212.0,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrBrowseLocalizer(metadata, 2048)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert pixel to lat/lon
    p1_latlon = localizer.pixel_to_latlon(p1_pixel[0], p1_pixel[1])
    p2_latlon = localizer.pixel_to_latlon(p2_pixel[0], p2_pixel[1])
    p3_latlon = localizer.pixel_to_latlon(p3_pixel[0], p3_pixel[1])
    p4_latlon = localizer.pixel_to_latlon(p4_pixel[0], p4_pixel[1])
    p5_latlon = localizer.pixel_to_latlon(p5_pixel[0], p5_pixel[1])

    # convert positive east 180 longitude to positive 360 longitude
    p1_latlon = list(p1_latlon)
    p2_latlon = list(p2_latlon)
    p3_latlon = list(p3_latlon)
    p4_latlon = list(p4_latlon)
    p5_latlon = list(p5_latlon)
    p1_latlon[1] = p1_latlon[1] % 360
    p2_latlon[1] = p2_latlon[1] % 360
    p3_latlon[1] = p3_latlon[1] % 360
    p4_latlon[1] = p4_latlon[1] % 360
    p5_latlon[1] = p5_latlon[1] % 360

    # test 5 points
    assert_allclose(p1_latlon, p1_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p2_latlon, p2_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p3_latlon, p3_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p4_latlon, p4_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p5_latlon, p5_latlon_expected, atol=TOLERANCE_DEG)

@unit
def test_hiriserdrbrowselocalizer_polarstereographic_latlon_to_pixel_northpole():
    '''
    Test case 4:
    Test lat/lon to pixel conversion for polarstereographic projection using
    image near north pole.

    Image id: ESP_050054_2565

    Run ISIS mappt to convert 5 points to line and sample:
    1. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.0918
             LONGITUDE=95.545
    2. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.0818
             LONGITUDE=95.3689
    3. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.291
             LONGITUDE=95.1579
    4. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.3011
             LONGITUDE=95.3366
    5. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.19145
             LONGITUDE=95.3515

    Results:
    1. lat=76.0918, lon=95.545   ==> line=3.3481906144007,
                                     sample=24353.96564842
    2. lat=76.0818, lon=95.3689  ==> line=4931.2083980744,
                                     sample=26026.240391183
    3. lat=76.291, lon=95.1579   ==> line=13225.079025231,
                                     sample=1667.938772222
    4. lat=76.3011, lon=95.3366  ==> line=8295.4296541251,
                                     sample=2.6312731597573
    5. lat=76.19145, lon=95.3515 ==> line=6652.6553750653,
                                     sample=13016.659884301
    '''

    # full size HiRISE image size
    full_size = (13224.0, 26027.0)
    map_scale = 0.5

    # ratio between full size and browse image
    ratio = full_size[1] / 2048.0

    # points to test
    # the following points are lat/lon values
    p1_latlon = [76.0918, 95.545]
    p2_latlon = [76.0818, 95.3689]
    p3_latlon = [76.291, 95.1579]
    p4_latlon = [76.3011, 95.3366]
    p5_latlon = [76.19145, 95.3515]

    # expected line/sample values
    p1_pixel_expected = [3.3481906144007 /ratio, 24353.96564842 / ratio]
    p2_pixel_expected = [4931.2083980744 / ratio, 26026.240391183 / ratio]
    p3_pixel_expected = [13225.079025231 / ratio, 1667.938772222 / ratio]
    p4_pixel_expected = [8295.4296541251 / ratio, 2.6312731597573 /ratio]
    p5_pixel_expected = [6652.6553750653 / ratio, 13016.659884301 /ratio]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
                           projection_center_latitude=90.0,
                           projection_center_longitude=0.0,
                           map_scale=map_scale, line_projection_offset=159167.5,
                           sample_projection_offset=-1615142.5,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrBrowseLocalizer(metadata, 2048)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert lat/lon to pixel
    p1_pixel = localizer.latlon_to_pixel(p1_latlon[0], p1_latlon[1])
    p2_pixel = localizer.latlon_to_pixel(p2_latlon[0], p2_latlon[1])
    p3_pixel = localizer.latlon_to_pixel(p3_latlon[0], p3_latlon[1])
    p4_pixel = localizer.latlon_to_pixel(p4_latlon[0], p4_latlon[1])
    p5_pixel = localizer.latlon_to_pixel(p5_latlon[0], p5_latlon[1])

    # test 5 points
    assert_allclose(p1_pixel, p1_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p2_pixel, p2_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p3_pixel, p3_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p4_pixel, p4_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p5_pixel, p5_pixel_expected, atol=TOLERANCE_PIXEL)

@unit
def test_hiriserdrbrowselocalizer_polarstereographic_pixel_to_latlon_southpole():
    '''
    Test case 5:
    Test pixel to lat/lon conversion for polarstereographic projection using
    image near south pole.

    Image id: ESP_049989_0930

    Run ISIS mappt to convert points to latitude and longitude:
    1. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=7940 SAMPLE=2
    2. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=1 SAMPLE=665
    3. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=2429 SAMPLE=30226
    4. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=10375 SAMPLE=29560
    5. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=5187.5 SAMPLE=15113

    Results:
    1. line=7940, sample=2       ==> lat=-86.959605211451, lon=158.25660498659
    2. line=1, sample=665        ==> lat=-86.989790088818, lon=157.96944372902
    3. line=2429, sample=30226   ==> lat=-86.931180262264, lon=155.87103130598
    4. line=10375, sample=29560  ==> lat=-86.901547240436, lon=156.1734811286
    5. line=5187.5, sample=15113 ==> lat=-86.946044198298, lon=157.05843125555
    '''

    # full size HiRISE image size
    full_size = (10375.0, 30226.0)
    map_scale = 0.25

    # ratio between full size and browse image
    ratio = full_size[1] / 2048.0

    # points to test
    # the following points are line/samp values defined in browse image
    p1_pixel = [7940.0 / ratio, 2.0 / ratio]
    p2_pixel = [1.0 / ratio, 665.0 / ratio]
    p3_pixel = [2429.0 / ratio, 30226.0 /ratio]
    p4_pixel = [10375.0 / ratio, 29560.0 / ratio]
    p5_pixel = [full_size[0] / ratio / 2.0, full_size[1] / ratio / 2.0]

    # expected lat/lon values
    p1_latlon_expected = [-86.959605211451, 158.25660498659]
    p2_latlon_expected = [-86.989790088818, 157.96944372902]
    p3_latlon_expected = [-86.931180262264, 155.87103130598]
    p4_latlon_expected = [-86.901547240436, 156.1734811286]
    p5_latlon_expected = [-86.946044198298, 157.05843125555]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
                           projection_center_latitude=-90.0,
                           projection_center_longitude=0.0,
                           map_scale=map_scale, line_projection_offset=-657861.5,
                           sample_projection_offset=-265537.5,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrBrowseLocalizer(metadata, 2048)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert pixel to lat/lon
    p1_latlon = localizer.pixel_to_latlon(p1_pixel[0], p1_pixel[1])
    p2_latlon = localizer.pixel_to_latlon(p2_pixel[0], p2_pixel[1])
    p3_latlon = localizer.pixel_to_latlon(p3_pixel[0], p3_pixel[1])
    p4_latlon = localizer.pixel_to_latlon(p4_pixel[0], p4_pixel[1])
    p5_latlon = localizer.pixel_to_latlon(p5_pixel[0], p5_pixel[1])

    # convert positive east 180 longitude to positive 360 longitude
    p1_latlon = list(p1_latlon)
    p2_latlon = list(p2_latlon)
    p3_latlon = list(p3_latlon)
    p4_latlon = list(p4_latlon)
    p5_latlon = list(p5_latlon)
    p1_latlon[1] = p1_latlon[1] % 360
    p2_latlon[1] = p2_latlon[1] % 360
    p3_latlon[1] = p3_latlon[1] % 360
    p4_latlon[1] = p4_latlon[1] % 360
    p5_latlon[1] = p5_latlon[1] % 360

    # test 5 points
    assert_allclose(p1_latlon, p1_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p2_latlon, p2_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p3_latlon, p3_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p4_latlon, p4_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p5_latlon, p5_latlon_expected, atol=TOLERANCE_DEG)

@unit
def test_hiriserdrbrowselocalizer_polarstereographic_latlon_to_pixel_southpole():
    '''
    Test case 6:
    Test lat/lon to pixel conversion for polarstereographic projection using image
    near south pole.

    Image id: ESP_050042_1000

    Run ISIS mappt to convert 5 points to line and sample:
    1. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.7669
             LONGITUDE=101.843
    2. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.7874
             LONGITUDE=101.43
    3. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.625
             LONGITUDE=101.179
    4. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.6047
             LONGITUDE=101.587
    5. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.69605
             LONGITUDE=101.511

    Results:
    1. lat=-79.7669, lon=101.843  ==> line=10463.328397211,
                                      sample=628.5909773563
    2. lat=-79.7874, lon=101.43   ==> line=1443.6864533564,
                                      sample=-0.33655633684248
    3. lat=-79.625, lon=101.179   ==> line=0.37412327560014,
                                      sample=19964.313501756
    4. lat=-79.6047, lon=101.587  ==> line=9043.8461438996,
                                      sample=20604.159140396
    5. lat=-79.69605, lon=101.511 ==> line=5281.32804386,
                                      sample=10294.632151381
    '''

    # full size HiRISE image size
    full_size = (10462.0, 20597.0)
    map_scale = 0.5

    # ratio between full size and browse image
    ratio = full_size[1] / 2048.0

    # points to test
    # the following points are lat/lon values
    p1_latlon = [-79.7669, 101.843]
    p2_latlon = [-79.7874, 101.43]
    p3_latlon = [-79.625, 101.179]
    p4_latlon = [-79.6047, 101.587]
    p5_latlon = [-79.69605, 101.511]

    # expected line/sample values
    p1_pixel_expected = [10463.328397211 /ratio, 628.5909773563 / ratio]
    p2_pixel_expected = [1443.6864533564 / ratio, -0.33655633684248 / ratio]
    p3_pixel_expected = [0.37412327560014 / ratio, 19964.313501756 / ratio]
    p4_pixel_expected = [9043.8461438996 / ratio, 20604.159140396 /ratio]
    p5_pixel_expected = [5281.32804386 / ratio, 10294.632151381 /ratio]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
                           projection_center_latitude=-90.0,
                           projection_center_longitude=0.0,
                           map_scale=map_scale, line_projection_offset=-237703.5,
                           sample_projection_offset=-1182837.5,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrBrowseLocalizer(metadata, 2048)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert lat/lon to pixel
    p1_pixel = localizer.latlon_to_pixel(p1_latlon[0], p1_latlon[1])
    p2_pixel = localizer.latlon_to_pixel(p2_latlon[0], p2_latlon[1])
    p3_pixel = localizer.latlon_to_pixel(p3_latlon[0], p3_latlon[1])
    p4_pixel = localizer.latlon_to_pixel(p4_latlon[0], p4_latlon[1])
    p5_pixel = localizer.latlon_to_pixel(p5_latlon[0], p5_latlon[1])

    # test 5 points
    assert_allclose(p1_pixel, p1_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p2_pixel, p2_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p3_pixel, p3_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p4_pixel, p4_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p5_pixel, p5_pixel_expected, atol=TOLERANCE_PIXEL)

@unit
def test_hiriserdrlocalizer_equirectangular_pixel_to_latlon():
    '''
    Test case 7:
    Test pixel to lat/lon conversion for equirectangular projection.

    Image id: ESP_050016_1870

    Run ISIS mappt to convert points to latitude and longitude:
    1. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=1 SAMPLE=1
    2. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=1 SAMPLE=22023
    3. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=23798 SAMPLE=22023
    4. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=23798 SAMPLE=1
    5. mappt FROM=ESP_050016_1870_RED.cub TYPE=IMAGE LINE=11899 SAMPLE=11012

    Results:
    1. line=1, sample=1         ==> lat=6.9937526632708, lon=69.985892127602
    2. line=1, sample=22023     ==> lat=6.9937526632708, lon=70.079132239075
    3. line=23798, sampe=22023  ==> lat=6.8933806899744, lon=70.079132239075
    4. line=23798, sample=1     ==> lat=6.8933806899744, lon=69.985892127602
    5. line=11899, sample=11012 ==> lat=6.9435687855433, lon=70.032512183339
    '''

    # full size HiRISE image size
    full_size = (23798.0, 22023.0)
    map_scale = 0.25

    # points to test
    # the following points are line/samp values defined in full size image
    ul_pixel = [1.0, 1.0]
    ur_pixel = [1.0, 22023.0]
    br_pixel = [23798.0, 22023.0]
    bl_pixel = [23798.0, 1.0]
    center_pixel = [11899.0, 11012.0]

    # expected lat/lon values
    ul_latlon_expected = [6.9937526632708, 69.985892127602]
    ur_latlon_expected = [6.9937526632708, 70.079132239075]
    br_latlon_expected = [6.8933806899744, 70.079132239075]
    bl_latlon_expected = [6.8933806899744, 69.985892127602]
    center_latlon_expected = [6.9435687855433, 70.032512183339]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='EQUIRECTANGULAR',
                           projection_center_latitude=5.0,
                           projection_center_longitude=180.0,
                           map_scale=map_scale, line_projection_offset=1658135.5,
                           sample_projection_offset=25983782.0,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrLocalizer(metadata)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert pixel to lat/lon
    ul_latlon = localizer.pixel_to_latlon(ul_pixel[0], ul_pixel[1])
    ur_latlon = localizer.pixel_to_latlon(ur_pixel[0], ur_pixel[1])
    br_latlon = localizer.pixel_to_latlon(br_pixel[0], br_pixel[1])
    bl_latlon = localizer.pixel_to_latlon(bl_pixel[0], bl_pixel[1])
    center_latlon = localizer.pixel_to_latlon(center_pixel[0], center_pixel[1])

    # convert to positive east 360 longitude
    ul_latlon = list(ul_latlon)
    ur_latlon = list(ur_latlon)
    br_latlon = list(br_latlon)
    bl_latlon = list(bl_latlon)
    center_latlon = list(center_latlon)
    ul_latlon[1] = ul_latlon[1] % 360
    ur_latlon[1] = ur_latlon[1] % 360
    br_latlon[1] = br_latlon[1] % 360
    bl_latlon[1] = bl_latlon[1] % 360
    center_latlon[1] = center_latlon[1] % 360

    # test upper left corner
    assert_allclose(ul_latlon, ul_latlon_expected, atol=TOLERANCE_DEG)

    # test upper right corner
    assert_allclose(ur_latlon, ur_latlon_expected, atol=TOLERANCE_DEG)

    # test bottom right corner
    assert_allclose(br_latlon, br_latlon_expected, atol=TOLERANCE_DEG)

    # test bottom left corner
    assert_allclose(bl_latlon, bl_latlon_expected, atol=TOLERANCE_DEG)

    # test center
    assert_allclose(center_latlon, center_latlon_expected, atol=TOLERANCE_DEG)

@unit
def test_hiriserdrlocalizer_equirectangular_latlon_to_pixel():
    '''
    Test case 8:
    Test lat/lon to pixel conversion for equirectangular projection.

    Image id: ESP_050062_1345

    Run ISIS mapt to convert 5 points to line and sample:
    1. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-44.949798974587
             LONGITUDE=260.83910415798
    2. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-44.949798974587
             LONGITUDE=260.95959132319
    3. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-45.042204321234
             LONGITUDE=260.95959132319
    4. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-45.042204321234
             LONGITUDE=260.83910415798
    5. mappt FROM=ESP_050062_1345_RED.cub TYPE=GROUND LATITUDE=-44.996001647910504
             LONGITUDE=260.899347740585

    Results:
    1. lat=-44.949798974587, lon=260.83910415798     ==> line=1.9730653911829,
                                                         samp=2.033464346081
    2. lat=-44.949798974587, lon=260.95959132319     ==> line=1.9730653911829,
                                                         samp=21832.404278895
    3. lat=-45.042204321234, lon=260.95959132319     ==> line=21857.609632041,
                                                         samp=21832.404278895
    4. lat=-45.042204321234, lon=260.83910415798     ==> line=21857.609632041,
                                                         samp=2.033464346081
    5. lat=-44.996001647910504, lon=260.899347740585 ==> line=10929.791348718,
                                                         samp=10917.21887161
    '''

    # full size HiRISE image size
    full_size = (21856.0, 21831.0)
    map_scale = 0.25

    # points to test
    # the following points are lat/lon values
    ul_latlon = [-44.949798974587, 260.83910415798]
    ur_latlon = [-44.949798974587, 260.95959132319]
    br_latlon = [-45.042204321234, 260.95959132319]
    bl_latlon = [-45.042204321234, 260.83910415798]
    center_latlon = [-44.996001647910504, 260.899347740585]

    # expected line/samp values
    ul_pixel_expected = [1.9730653911829, 2.033464346081]
    ur_pixel_expected = [1.9730653911829, 21832.404278895]
    br_pixel_expected = [21857.609632041, 21832.404278895]
    bl_pixel_expected = [21857.609632041, 2.033464346081]
    center_pixel_expected = [10929.791348718, 10917.21887161]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='EQUIRECTANGULAR',
                           projection_center_latitude=-40.0,
                           projection_center_longitude=180.0,
                           map_scale=map_scale, line_projection_offset=-10631488.0,
                           sample_projection_offset=-14646768.0,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrLocalizer(metadata)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert lat/lon to pixel
    ul_pixel = localizer.latlon_to_pixel(ul_latlon[0], ul_latlon[1])
    ur_pixel = localizer.latlon_to_pixel(ur_latlon[0], ur_latlon[1])
    br_pixel = localizer.latlon_to_pixel(br_latlon[0], br_latlon[1])
    bl_pixel = localizer.latlon_to_pixel(bl_latlon[0], bl_latlon[1])
    center_pixel = localizer.latlon_to_pixel(center_latlon[0],
                                             center_latlon[1])

    # test upper left corner
    assert_allclose(ul_pixel, ul_pixel_expected, atol=TOLERANCE_PIXEL)

    # test upper right corner
    assert_allclose(ur_pixel, ur_pixel_expected, atol=TOLERANCE_PIXEL)

    # test bottom right corner
    assert_allclose(br_pixel, br_pixel_expected, atol=TOLERANCE_PIXEL)

    # test bottom left corner
    assert_allclose(bl_pixel, bl_pixel_expected, atol=TOLERANCE_PIXEL)

    # test center
    assert_allclose(center_pixel, center_pixel_expected,
                    TOLERANCE_PIXEL)

@unit
def test_hiriserdrlocalizer_polarstereographic_pixel_to_latlon_northpole():
    '''
    Test case 9:
    Test pixel to lat/lon conversion for polarstereographic projection using
    image near north pole.

    Image id: ESP_045245_2675

    Run ISIS mappt to convert points to latitude and longitude:
    1. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=375 SAMPLE=1
    2. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=2 SAMPLE=10244
    3. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=31696 SAMPLE=11385
    4. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=32073 SAMPLE=1142
    5. mappt FROM=ESP_045245_2675_RED.cub TYPE=IMAGE LINE=16037 SAMPLE=5693

    Results:
    1. line=375, sample=1       ==> lat=87.266078122413, lon=296.01543481484
    2. line=2, sample=10244     ==> lat=87.305746158879, lon=296.39047246968
    3. line=31696, sample=11385 ==> lat=87.247615701464, lon=298.94304912096
    4. line=32073, sample=1142  ==> lat=87.208765944927, lon=298.54015964047
    5. line=16037, sample=5693  ==> lat=87.25773880432, lon=297.48428883797
    '''

    # full size HiRISE image size
    full_size = (32073.0, 11385.0)
    map_scale = 0.25

    # points to test
    # the following points are line/samp values defined in full size image
    p1_pixel = [375.0, 1.0]
    p2_pixel = [2.0, 10244.0]
    p3_pixel = [31696.0, 11385.0]
    p4_pixel = [32073.0, 1142.0]
    p5_pixel = [16037.0, 5693.0]

    # expected lat/lon values
    p1_latlon_expected = [87.266078122413, 296.01543481484]
    p2_latlon_expected = [87.305746158879, 296.39047246968]
    p3_latlon_expected = [87.247615701464, 298.94304912096]
    p4_latlon_expected = [87.208765944927, 298.54015964047]
    p5_latlon_expected = [87.25773880432, 297.48428883797]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
                           projection_center_latitude=90.0,
                           projection_center_longitude=0.0,
                           map_scale=map_scale, line_projection_offset=-282320.0,
                           sample_projection_offset=579212.0,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrLocalizer(metadata)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert pixel to lat/lon
    p1_latlon = localizer.pixel_to_latlon(p1_pixel[0], p1_pixel[1])
    p2_latlon = localizer.pixel_to_latlon(p2_pixel[0], p2_pixel[1])
    p3_latlon = localizer.pixel_to_latlon(p3_pixel[0], p3_pixel[1])
    p4_latlon = localizer.pixel_to_latlon(p4_pixel[0], p4_pixel[1])
    p5_latlon = localizer.pixel_to_latlon(p5_pixel[0], p5_pixel[1])

    # convert positive east 180 longitude to positive 360 longitude
    p1_latlon = list(p1_latlon)
    p2_latlon = list(p2_latlon)
    p3_latlon = list(p3_latlon)
    p4_latlon = list(p4_latlon)
    p5_latlon = list(p5_latlon)
    p1_latlon[1] = p1_latlon[1] % 360
    p2_latlon[1] = p2_latlon[1] % 360
    p3_latlon[1] = p3_latlon[1] % 360
    p4_latlon[1] = p4_latlon[1] % 360
    p5_latlon[1] = p5_latlon[1] % 360

    # test 5 points
    assert_allclose(p1_latlon, p1_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p2_latlon, p2_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p3_latlon, p3_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p4_latlon, p4_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p5_latlon, p5_latlon_expected, atol=TOLERANCE_DEG)

@unit
def test_hiriserdrlocalizer_polarstereographic_latlon_to_pixel_northpole():
    '''
    Test case 10:
    Test lat/lon to pixel conversion for polarstereographic projection using
    image near north pole.

    Image id: ESP_050054_2565

    Run ISIS mappt to convert 5 points to line and sample:
    1. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.0918
             LONGITUDE=95.545
    2. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.0818
             LONGITUDE=95.3689
    3. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.291
             LONGITUDE=95.1579
    4. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.3011
             LONGITUDE=95.3366
    5. mappt FROM=ESP_050054_2565_RED.cub TYPE=GROUND LATITUDE=76.19145
             LONGITUDE=95.3515

    Results:
    1. lat=76.0918, lon=95.545   ==> line=3.3481906144007,
                                     sample=24353.96564842
    2. lat=76.0818, lon=95.3689  ==> line=4931.2083980744,
                                     sample=26026.240391183
    3. lat=76.291, lon=95.1579   ==> line=13225.079025231,
                                     sample=1667.938772222
    4. lat=76.3011, lon=95.3366  ==> line=8295.4296541251,
                                     sample=2.6312731597573
    5. lat=76.19145, lon=95.3515 ==> line=6652.6553750653,
                                     sample=13016.659884301
    '''

    # full size HiRISE image size
    full_size = (13224.0, 26027.0)
    map_scale = 0.5

    # points to test
    # the following points are lat/lon values
    p1_latlon = [76.0918, 95.545]
    p2_latlon = [76.0818, 95.3689]
    p3_latlon = [76.291, 95.1579]
    p4_latlon = [76.3011, 95.3366]
    p5_latlon = [76.19145, 95.3515]

    # expected line/sample values
    p1_pixel_expected = [3.3481906144007, 24353.96564842]
    p2_pixel_expected = [4931.2083980744, 26026.240391183]
    p3_pixel_expected = [13225.079025231, 1667.938772222]
    p4_pixel_expected = [8295.4296541251, 2.6312731597573]
    p5_pixel_expected = [6652.6553750653, 13016.659884301]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
                           projection_center_latitude=90.0,
                           projection_center_longitude=0.0,
                           map_scale=map_scale, line_projection_offset=159167.5,
                           sample_projection_offset=-1615142.5,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrLocalizer(metadata)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert lat/lon to pixel
    p1_pixel = localizer.latlon_to_pixel(p1_latlon[0], p1_latlon[1])
    p2_pixel = localizer.latlon_to_pixel(p2_latlon[0], p2_latlon[1])
    p3_pixel = localizer.latlon_to_pixel(p3_latlon[0], p3_latlon[1])
    p4_pixel = localizer.latlon_to_pixel(p4_latlon[0], p4_latlon[1])
    p5_pixel = localizer.latlon_to_pixel(p5_latlon[0], p5_latlon[1])

    # test 5 points
    assert_allclose(p1_pixel, p1_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p2_pixel, p2_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p3_pixel, p3_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p4_pixel, p4_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p5_pixel, p5_pixel_expected, atol=TOLERANCE_PIXEL)

@unit
def test_hiriserdrlocalizer_polarstereographic_pixel_to_latlon_southpole():
    '''
    Test case 11:
    Test pixel to lat/lon conversion for polarstereographic projection using
    image near south pole.

    Image id: ESP_049989_0930

    Run ISIS mappt to convert points to latitude and longitude:
    1. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=7940 SAMPLE=2
    2. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=1 SAMPLE=665
    3. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=2429 SAMPLE=30226
    4. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=10375 SAMPLE=29560
    5. mappt FROM=ESP_049989_0930_RED.cub TYPE=IMAGE LINE=5187.5 SAMPLE=15113

    Results:
    1. line=7940, sample=2       ==> lat=-86.959605211451, lon=158.25660498659
    2. line=1, sample=665        ==> lat=-86.989790088818, lon=157.96944372902
    3. line=2429, sample=30226   ==> lat=-86.931180262264, lon=155.87103130598
    4. line=10375, sample=29560  ==> lat=-86.901547240436, lon=156.1734811286
    5. line=5187.5, sample=15113 ==> lat=-86.946044198298, lon=157.05843125555
    '''

    # full size HiRISE image size
    full_size = (10375.0, 30226.0)
    map_scale = 0.25

    # points to test
    # the following points are line/samp values defined in browse image
    p1_pixel = [7940.0, 2.0]
    p2_pixel = [1.0, 665.0]
    p3_pixel = [2429.0, 30226.0]
    p4_pixel = [10375.0, 29560.0]
    p5_pixel = [5187.5, 15113.0]

    # expected lat/lon values
    p1_latlon_expected = [-86.959605211451, 158.25660498659]
    p2_latlon_expected = [-86.989790088818, 157.96944372902]
    p3_latlon_expected = [-86.931180262264, 155.87103130598]
    p4_latlon_expected = [-86.901547240436, 156.1734811286]
    p5_latlon_expected = [-86.946044198298, 157.05843125555]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
                           projection_center_latitude=-90.0,
                           projection_center_longitude=0.0,
                           map_scale=map_scale, line_projection_offset=-657861.5,
                           sample_projection_offset=-265537.5,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrLocalizer(metadata)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert pixel to lat/lon
    p1_latlon = localizer.pixel_to_latlon(p1_pixel[0], p1_pixel[1])
    p2_latlon = localizer.pixel_to_latlon(p2_pixel[0], p2_pixel[1])
    p3_latlon = localizer.pixel_to_latlon(p3_pixel[0], p3_pixel[1])
    p4_latlon = localizer.pixel_to_latlon(p4_pixel[0], p4_pixel[1])
    p5_latlon = localizer.pixel_to_latlon(p5_pixel[0], p5_pixel[1])

    # convert positive east 180 longitude to positive 360 longitude
    p1_latlon = list(p1_latlon)
    p2_latlon = list(p2_latlon)
    p3_latlon = list(p3_latlon)
    p4_latlon = list(p4_latlon)
    p5_latlon = list(p5_latlon)
    p1_latlon[1] = p1_latlon[1] % 360
    p2_latlon[1] = p2_latlon[1] % 360
    p3_latlon[1] = p3_latlon[1] % 360
    p4_latlon[1] = p4_latlon[1] % 360
    p5_latlon[1] = p5_latlon[1] % 360

    # test 5 points
    assert_allclose(p1_latlon, p1_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p2_latlon, p2_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p3_latlon, p3_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p4_latlon, p4_latlon_expected, atol=TOLERANCE_DEG)
    assert_allclose(p5_latlon, p5_latlon_expected, atol=TOLERANCE_DEG)

@unit
def test_hiriserdrlocalizer_polarstereographic_latlon_to_pixel_southpole():
    '''
    Test case 12:
    Test lat/lon to pixel conversion for polarstereographic projection using image
    near south pole.

    Image id: ESP_050042_1000

    Run ISIS mappt to convert 5 points to line and sample:
    1. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.7669
             LONGITUDE=101.843
    2. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.7874
             LONGITUDE=101.43
    3. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.625
             LONGITUDE=101.179
    4. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.6047
             LONGITUDE=101.587
    5. mappt FROM=ESP_050042_1000_RED.cub TYPE=GROUND LATITUDE=-79.69605
             LONGITUDE=101.511

    Results:
    1. lat=-79.7669, lon=101.843  ==> line=10463.328397211,
                                      sample=628.5909773563
    2. lat=-79.7874, lon=101.43   ==> line=1443.6864533564,
                                      sample=-0.33655633684248
    3. lat=-79.625, lon=101.179   ==> line=0.37412327560014,
                                      sample=19964.313501756
    4. lat=-79.6047, lon=101.587  ==> line=9043.8461438996,
                                      sample=20604.159140396
    5. lat=-79.69605, lon=101.511 ==> line=5281.32804386,
                                      sample=10294.632151381
    '''

    # full size HiRISE image size
    full_size = (10462.0, 20597.0)
    map_scale = 0.5

    # points to test
    # the following points are lat/lon values
    p1_latlon = [-79.7669, 101.843]
    p2_latlon = [-79.7874, 101.43]
    p3_latlon = [-79.625, 101.179]
    p4_latlon = [-79.6047, 101.587]
    p5_latlon = [-79.69605, 101.511]

    # expected line/sample values
    p1_pixel_expected = [10463.328397211, 628.5909773563]
    p2_pixel_expected = [1443.6864533564, -0.33655633684248]
    p3_pixel_expected = [0.37412327560014, 19964.313501756]
    p4_pixel_expected = [9043.8461438996, 20604.159140396]
    p5_pixel_expected = [5281.32804386, 10294.632151381]

    # invoke localizer object
    metadata = PdsMetadata('hirise_rdr', map_projection_type='POLAR STEREOGRAPHIC',
                           projection_center_latitude=-90.0,
                           projection_center_longitude=0.0,
                           map_scale=map_scale, line_projection_offset=-237703.5,
                           sample_projection_offset=-1182837.5,
                           samples=full_size[1], lines=full_size[0])
    localizer = HiRiseRdrLocalizer(metadata)

    assert_allclose(
        localizer.observation_width_m,
        map_scale*full_size[1],
        atol=TOLERANCE_M
    )
    assert_allclose(
        localizer.observation_length_m,
        map_scale*full_size[0],
        atol=TOLERANCE_M
    )

    # convert lat/lon to pixel
    p1_pixel = localizer.latlon_to_pixel(p1_latlon[0], p1_latlon[1])
    p2_pixel = localizer.latlon_to_pixel(p2_latlon[0], p2_latlon[1])
    p3_pixel = localizer.latlon_to_pixel(p3_latlon[0], p3_latlon[1])
    p4_pixel = localizer.latlon_to_pixel(p4_latlon[0], p4_latlon[1])
    p5_pixel = localizer.latlon_to_pixel(p5_latlon[0], p5_latlon[1])

    # test 5 points
    assert_allclose(p1_pixel, p1_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p2_pixel, p2_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p3_pixel, p3_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p4_pixel, p4_pixel_expected, atol=TOLERANCE_PIXEL)
    assert_allclose(p5_pixel, p5_pixel_expected, atol=TOLERANCE_PIXEL)

@unit
def test_unimplemented_methods():
    localizer = Localizer()

    with pytest.raises(NotImplementedError):
        localizer.observation_length_m

    with pytest.raises(NotImplementedError):
        localizer.observation_width_m

    with pytest.raises(NotImplementedError):
        localizer.pixel_to_latlon(0, 0)
