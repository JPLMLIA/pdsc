import os
import numpy as np
import pdsc
import pdb

# Emily Dunkel
# 2022
# Simple script to look at lat lon conversion


def main(img, xval, yval):
    """
    Get the lat/long from the pixel values from the image
    """
    client = pdsc.PdsClient()
    metadata = client.query_by_observation_id('lroc_cdr', ' M101013931LC')
    mydata = metadata[0]
    localizer = pdsc.get_localizer(mydata, browse=True)
    lat, lon = localizer.pixel_to_latlon(10, 10)
    print('lat:', lat)
    print('lon: ', lon)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)

    img = ' M101013931LC'
    x = 10
    y = 10
    parser.add_argument('-i', '--img', default=img, type=str)
    parser.add_argument('-x', '--xval', default=x, type=int)
    parser.add_argument('-y', '--yval', default=y, type=int)
    args = parser.parse_args()
    main(**vars(args))
