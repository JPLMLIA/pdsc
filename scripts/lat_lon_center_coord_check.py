# Emily Dunkel
# 2023
# Script to look at center lat lon conversion for example LROC NAC imagery

import os
import numpy as np
import pdsc
import pdb

client = pdsc.PdsClient()

def get_pixel_cnt_diff(img):
    """
    Get the pixel difference between the center lat/lon and calculated
    """
    metadata = client.query_by_observation_id('lroc_cdr', img)
    if metadata == []:
        print('Could not get metadata for: ', img)
        row_diff = 'NULL'
        col_diff = 'NULL'
    else:
        mydata = metadata[0]
        nrows = mydata.lines
        ncols = mydata.samples
        localizer = pdsc.get_localizer(mydata, browse=False)
        row_c, col_c = localizer.latlon_to_pixel(mydata.center_latitude, mydata.center_longitude)
        row_diff = abs(nrows/2 - row_c);
        col_diff = abs(ncols/2 - col_c);
        print('row diff:', int(round(row_diff)))
        print('col diff: ', int(round(col_diff)))
        
    return row_diff, col_diff

if __name__ == '__main__':

    img_list = [' M101014437RC', ' M119217559LC', ' M186790112RC', ' M186786083LC', ' M186778737LC',
                ' M121817429LC', ' M186778235RC', ' M186775740LC', ' M186775813RC', ' M186762974RC', 
                ' M117358581LC', ' M186749329RC', ' M186728887RC', ' M157867349LC', ' M160230711LC',
                ' M186627048RC', ' M109978196RC', ' M109987085RC', ' M101013931LC', ' M112699470LC',
                ' M112713912LC', ' M112722915RC', ' M148563970RC', ' M186790281RC', ' M191761375RC']
    res = 0.5 # resolution in meters
    count = 0
    row_l = []
    col_l = []
    for ii in img_list:
        count = count + 1
        print(count)
        row_diff, col_diff = get_pixel_cnt_diff(ii)
        row_diff_m = int(round(res * row_diff))
        col_diff_m = int(round(res * col_diff))
        row_l.append(row_diff_m)
        col_l.append(col_diff_m)

    print('mean row diff in m: ', np.mean(row_l))
    print('mean col diff in m: ', np.mean(col_l))
    print('max row diff in m: ', max(row_l))
    print('max col diff in m: ', max(col_l))
