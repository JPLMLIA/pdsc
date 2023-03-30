# !/usr/bin/env python
# This script provides examples for pixel to lat/lon coordinates conversion for
# LROC NAC CDR images (the conversion routine is exactly the same as the
# FourCornerLocalizer from PDSC)
#
# Steven Lu
# Feb. 24, 2023

import numpy as np


def latlon2unit(latlon):
    llrad = np.deg2rad(latlon)
    sinll = np.sin(llrad)
    cosll = np.cos(llrad)

    return np.array([
        cosll[0] * cosll[1],
        cosll[0] * sinll[1],
        sinll[0]
    ])


def xyz2latlon(xyz):
    norm = np.linalg.norm(xyz)
    if norm == 0:
        raise ValueError('Point must be nonzero')
    x, y, z = (xyz / norm)

    return np.rad2deg([
        np.arcsin(z),
        np.arctan2(y, x)
    ])


def main():
    # Test case 1 for LROC NAC CDR image M118769870LE
    #
    # According to the metadata at the URL (https://wms.lroc.asu.edu/lroc/view_lroc/LRO-L-LROC-3-CDR-V1.0/M118769870LC):
    # (Note that following metadata are also available in the LROC cumulative index file)
    # center lat/lon = (-21.58, 165.21)
    # top left corner lat/lon = (-21.94, 165.17)
    # bottom left corner lat/lon = (-21.21, 165.16)
    # bottom right corner lat/lon = (-21.21, 165.25)
    # top right corner lat/lon = (-21.94, 165.26)
    # total rows = 38912
    # total cols = 5064
    corners = np.array([
        [-21.94, 165.17],  # top left
        [-21.21, 165.16],  # bottom left
        [-21.21, 165.25],  # bottom right
        [-21.94, 165.26]   # top right
    ])
    n_rows = 38912
    n_cols = 5064

    C = np.array([
        [latlon2unit(corners[0]), latlon2unit(corners[3])],
        [latlon2unit(corners[1]), latlon2unit(corners[2])]
    ])

    center_row = n_rows // 2
    center_col = n_cols // 2
    dx = np.array([n_cols - center_col, center_col])
    dy = np.array([n_rows - center_row, center_row])

    # bi-linear interpolation
    interpolated = np.array([
        np.dot(dx, np.dot(C[..., dim], dy.T))
        for dim in range(3)
    ]) / float(n_rows * n_cols)

    center_lat, center_lon = xyz2latlon(interpolated)
    center_lat = float('{:.2f}'.format(center_lat))
    center_lon = float('{:.2f}'.format(center_lon))
    print(f'center lat/lon = ({center_lat}, {center_lon})')

    # Compare to the center lat/lon from the metadata
    assert center_lat == -21.58
    assert center_lon == 165.21


if __name__ == '__main__':
    main()
