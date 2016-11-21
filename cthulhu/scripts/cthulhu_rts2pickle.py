#!/usr/bin/env python2

import argparse
import multiprocessing as mp
from cthulhu.rts_log_tools import rts2pickle, filter_logs

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--nofiltering", action="store_true",
                    help="Do not filter the RTS logs before pickling.")
parser.add_argument("logs", nargs='*', help="Paths to log files, and/or text " \
                    "files with paths to log files.")
args = parser.parse_args()


if __name__ == "__main__":
    ## Input is either a text file specifying log files (suffix .txt),
    ## or log files.
    if len(args.logs) == 0:
        exit("Aborting: Need log files to process.")

    logs = []
    for f in args.logs:
        if isinstance(f, str) and f.endswith(".txt"):
            with open(f) as f2:
                logs.append([l.strip() for l in f2.readlines()])
        else:
            logs.append(f)

    if not args.nofiltering:
        logs = filter_logs(logs)

    mp.Pool().map(rts2pickle, logs)
