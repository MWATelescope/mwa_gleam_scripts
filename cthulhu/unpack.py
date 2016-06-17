#!/usr/bin/env python2

import pickle
import numpy as np
from cthulhu.rts_log_tools import rts2dict


def unpack_data(data_file, verbosity=0):
    if isinstance(data_file, str):
        # Pickle files - can only have the four required lists.
        if data_file.endswith(".pickle"):
            with open(data_file, 'r') as f:
                unpacked = pickle.load(f)
            if verbosity > 0: print "Loaded pickle file: %s" % data_file
            return unpacked

        # Text file - can only be in a numpy.loadtxt format with
        # the four required lists.
        elif data_file.endswith(".txt"):
            ra, dec, ra_shifts, dec_shifts = np.loadtxt(data_file)
            if verbosity > 0: print "Loaded text file: %s" % data_file
            return [ra, dec, ra_shifts, dec_shifts]

        # Will perform the scraping on a specified log file.
        # N.B. This is expensive, and other tools should be used
        # to convert RTS log data into an intermediate format,
        # especially if the data is to be used more than once.
        elif data_file.endswith(".log"):
            reduced = rts2dict(data_file)
            if verbosity > 0: print "Loaded RTS log file: %s" % data_file
            return reduced

    # If data_file is actually a list of the four required lists,
    # then we only need to return data_file.
    return data_file
