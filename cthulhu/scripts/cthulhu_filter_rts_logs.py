#!/usr/bin/env python2

import sys
from cthulhu.rts_log_tools import filter_logs


if __name__ == "__main__":
    filtered_logs = filter_logs(sys.argv[1:], verbosity=0)
    print '\n'.join(filtered_logs)
