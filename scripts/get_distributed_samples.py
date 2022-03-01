import os
import numpy as np
from sklearn.neighbors import DistanceMetric
from progressbar import ProgressBar, Bar, ETA
#from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pdsc
import pdb

def get_lroc_metadata_from_id(lroc_id, pdsc_client=None):
    if pdsc_client is None:
        pdsc_client = pdsc.PdsClient()

    meta = pdsc_client.query_by_observation_id('lroc', lroc_id)

    if len(meta) < 0:
        raise ValueError('No metadata found for "%s"' % lroc_id)

    if len(meta) > 1:
        raise ValueError('Multiple metadata entries found for "%s"' % lroc_id)

    # Must be true given the checks above
    assert len(meta) == 1
    meta = meta.pop()
    return meta

def get_lroc_observation_from_id(lroc_id, pdsc_client=None, cacheroot=None,
        return_path=False):

    meta = get_lroc_metadata_from_id(lroc_id, pdsc_client=pdsc_client)

    return get_lroc_observation_from_meta(
        meta, cacheroot=cacheroot, return_path=return_path
    )


def get_latlon(client, lroc_id, cacheroot):
    try:
        obs_data = get_lroc_observation_from_id(lroc_id=lroc_id, pdsc_client=client, 
                                                   cacheroot=cacheroot)
    except:
        print("Error found in " + lroc_id + ", skipping.")
        return None

    loc = pdsc.get_localizer(obs_data.meta)

    latlon = loc.pixel_to_latlon(obs_data.meta.lines / 2, obs_data.meta.samples / 2)
    return latlon

def pick_next(selected, latlon):
    dist = DistanceMetric.get_metric('haversine')
    S = latlon[np.array(selected)]
    D = dist.pairwise(S, latlon)
    # Distance to closest selected point
    Dmin = np.min(D, axis=0)
    # Index of observation with farthest distance to closest selected point
    return np.argmax(Dmin)

def plot_selected(latlon):
    fig = plt.figure(figsize=(7, 5))#, dpi=300)
    ax = fig.add_subplot(111)

    m = Basemap(projection='mill')
    m.drawparallels(np.linspace(-75, 75, 7),
        labels=[True, True, False, False], fontsize=14)
    m.drawmeridians(np.linspace(-150, 150, 7),
        labels=[False, False, False, True], fontsize=14)
    m.warpimage(MAP_FILE)

    x, y = m(latlon[:, 1], latlon[:, 0])
    m.plot(x, y, 'ko', markersize=7, markeredgecolor='w')

    return fig

def main(outputfile, number, plotfile):
    np.random.seed(0)
    client = pdsc.PdsClient()
    # get the lroc NAC data
    full_data = client.query('lroc_cdr')
    nac_data = [row for row in full_data if 'NAC' in row.file_specification_name]
    # get the ids

    # loop through all the data and get the lat/lon
    
    latlon = np.deg2rad(np.array([
        get_latlon(client, i) for i in nac_data)
    ]))
    ids = np.array(ids)

    # Start with a random observation
    selected = [np.random.choice(len(ids))]
    progress = ProgressBar(widgets=['Selecting: ', Bar('='), ETA()])
    for i in progress(range(1, number)):
        selected.append(pick_next(selected, latlon))
    selected = np.array(selected)

    selected_ids = ids[selected]
    selected_pairs = []
    for i in selected_ids:
        selected_pairs.append(np.random.choice(sorted(overlaps[i])))

    with open(outputfile, 'w') as f:
        for i, j in zip(selected_ids, selected_pairs):
            f.write('%s,%s\n' % (i, j))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)

    outputfile_d = '~/PDS/lroc_proj/pdsc/outputs/lroc/output.txt'

    parser.add_argument('-o', '--outputfile', default=outputfile_d, type=str)
    parser.add_argument('-n', '--number', default=10, type=int)
    parser.add_argument('-p', '--plotfile', default=None)
    args = parser.parse_args()
    main(**vars(args))
