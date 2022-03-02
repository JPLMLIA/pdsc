import os
import numpy as np
from sklearn.neighbors import DistanceMetric
from progressbar import ProgressBar, Bar, ETA
#from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pdsc
import pdb

# Emily Dunkel
# 2022
# Get maximally distant lroc imagery
# Selects a random image, then the maximally distant image from that, then for each image, get the minimum distance to every already select point, then take the max
# This will give us distributed samples around the globe
# Based on script: https://github-fn.jpl.nasa.gov/COSMIC/COSMIC_CTX_impacts/commit/e4c167a2e4d9e345693cd5e25df0149f5d641653

def get_latlon(row):
    """
    Return center lat/lon of image

    Inputs
    ------
    row: PdsMetadata
        single row in table, information for a single image
    
    Returns
    -------
    latlon: (float, float)
        (latitude in radians, longitude in radians
    """
    # latlon of the center of the image
    latlon = np.deg2rad(float(row.center_latitude)), np.deg2rad(float(row.center_longitude))
    return latlon

def pick_next(selected, latlon):
    """
    Return the index of the next selected point

    Inputs
    ------
    selected: list of integers
        index of previously selected points
    latlon: numpy array of shape (number_of_images, 2)
        latitude and longitude of all images

    Returns
    -------
    returns: integer
        index of image that is farthest away to the selected points
    """
    dist = DistanceMetric.get_metric('haversine')
    S = latlon[np.array(selected)]
    D = dist.pairwise(S, latlon)
    # Distance to closest selected points
    Dmin = np.min(D, axis=0)
    # Index of observation with farthest distance to closest selected point
    return np.argmax(Dmin)

def main(outputfile, number):
    """
    Returns list of images that are spread throughout the globe
   
    Inputs
    ------
    outputfile: str, path to outputfile
        file with list of images
    number: int
        number of images to return
    """
    np.random.seed(0)
    client = pdsc.PdsClient()

    # get the lroc NAC data
    full_data = client.query('lroc_cdr')
    nac_data = [row for row in full_data if ('NAC' in row.file_specification_name and 'MOON' in row.target_name)]

    # get the number of NAC observations
    num_obs = len(nac_data)
    print('Total number of observations = ', num_obs)

    # loop through the nac data and get the lat/lon
    print('Getting every lat/lon')
    latlon = np.array([get_latlon(row) for row in nac_data])
    print('Getting every filename')
    ids = np.array([row.file_specification_name for row in nac_data])
 
    # start with a random observation
    print('Selected 0th observation')
    selected = [np.random.choice(num_obs)]

    # select the maximally distance image 
    for ii in range(1, number):
        print('Getting observation #: ', ii)
        selected.append(pick_next(selected, latlon))

    selected = np.array(selected)
    # filenames of selected cases
    selected_ids = ids[selected]
    with open(outputfile, 'w') as f:
        for i in selected_ids:
            f.write('%s\n' % (i))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)

    outputfile_d = '/home/edunkel/PDS/lroc_proj/pdsc/inputs_mini/lroc/selected.txt'    

    parser.add_argument('-o', '--outputfile', default=outputfile_d, type=str)
    parser.add_argument('-n', '--number', default=10, type=int)
    args = parser.parse_args()
    main(**vars(args))
