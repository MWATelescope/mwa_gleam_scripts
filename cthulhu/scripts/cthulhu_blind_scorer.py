#!/usr/bin/env python2

from glob import glob as glob
import random

import numpy as np
import matplotlib.pyplot as plt

from cthulhu.reconstruct import Obsid
from cthulhu.unpack import unpack_data
from cthulhu.plot_tools import setup_subplot, plot_vector_arrows


if __name__ == "__main__":
    files = glob("pickles/*.pickle")

    print "Saving scores to scores.txt"
    f = open("scores.txt", "aw")
    fig, ax = plt.subplots()
    count = 0
    while True:
        random_file = random.choice(files)
        unpacked = unpack_data(random_file)

        obs = Obsid(unpacked)
        obs.reconstruct_tec()

        setup_subplot(ax, "Reconstructed TEC field", "RA (deg)", "Dec (deg)")
        plot_vector_arrows(obs.ra, obs.dec, obs.ra_shifts, obs.dec_shifts, ax)
        tec = ax.imshow(np.arcsinh(obs.tec), extent=obs.tec_extent,
                        cmap="plasma", vmin=-2, vmax=2, origin="lower")
        try:
            cb = plt.colorbar(tec, ax=ax, format="%.2f", cax=cb.ax)
        except:
            cb = plt.colorbar(tec, ax=ax, format="%.2f")
        cb.set_label("arcsinh(TEC)")
        plt.show(block=False)

        try:
            score = raw_input("Score between 1 (best) and 10 (worst), or enter to exit: ")
            if len(score) == 0:
                break
            elif int(score) >= 1 and int(score) <= 10:
                f.write("%s: %s\n" % (obs.obsid, score))
        except:
            continue

        plt.cla()
        cb.ax.clear()
        count += 1

    print "%s scores added." % count
    f.close()
