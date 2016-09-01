#!/usr/bin/env python2

import sys
import argparse
import multiprocessing as mp

import threading
import fasteners

from cthulhu.reconstruct import Obsid
from cthulhu.unpack import unpack_data
from cthulhu.plot_tools import generate_diagnostic_figure, raw_and_tec

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbosity", action="count",
                    help="Level of verbosity.")
parser.add_argument("-o", "--overwrite", action="store_true",
                    help="Ignore the presence of an existing file.")
parser.add_argument("-f", "--field", default="EoR0",
                    help="Reject data from a field other than the one specified. " \
                    "Currently only works for 'EoR0'.")
parser.add_argument("files", nargs='*', help="Files to be processed. " \
                    "See cthulhu.unpack_data for appropriate formats.")
args = parser.parse_args()


class Display_safely(object):
    def __init__(self, string):
        self._lock = threading.Lock()
        self.string = string

    @fasteners.locked
    def display(self):
        print self.string
        sys.stdout.flush()


def unpack_model_plot(data_file):
    if args.verbosity > 2:
        print "Attempting to unpack: %s" % data_file

    unpacked = unpack_data(data_file, verbosity=args.verbosity)
    if len(unpacked["ra"]) < 500:
        if args.verbosity > 0:
            print "%s: Less than 500 sources, skipping." % data_file
        return
    elif args.field == "EoR0":
        import numpy as np
        if np.abs(np.mean(unpacked["ra"])) > 10:
            if args.verbosity > 0:
                print "%s: Not EoR0, skipping." % data_file
            return

    obs = Obsid(unpacked, data_file)
    obs.obsid_metric()
    # obs.tec_residuals()
    obs.save_tec_fits(verbosity=args.verbosity, overwrite=args.overwrite)
    generate_diagnostic_figure(obs, verbosity=args.verbosity, overwrite=args.overwrite)
    # raw_and_tec(obs, "%s.png" % obs.obsid)

    string = str(obs.obsid)
    for x in obs.metrics:
        string += " %.4f" % x[0]
    Display_safely(string).display()
    if args.verbosity > 0: print "Finished: %s" % obs.obsid


if __name__ == "__main__":
    # Check that arguments are sane.
    if args.field == "EoR0":
        pass
    elif len(args.field) > 0:
        exit("Unknown field specified.")

    if args.verbosity > 1:
        for f in args.files:
            unpack_model_plot(f)
    else:
        mp.Pool().map(unpack_model_plot, args.files)
