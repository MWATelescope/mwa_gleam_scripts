#!/usr/bin/env python2

import sys
import numpy as np
import matplotlib.pyplot as plt

obsid, med_ra, med_dec, std_ra, std_dec, std_tec, non_dc = np.loadtxt(sys.argv[1], unpack=True)

fig, ax = plt.subplots(2, 3, figsize=(16, 9))

ax[0, 0].hist(np.log(med_ra), bins=50)
ax[0, 0].set_title("median ra")

ax[1, 0].hist(np.log(med_dec), bins=50)
ax[1, 0].set_title("median dec")

ax[0, 1].hist(np.log(std_ra), bins=50)
ax[0, 1].set_title("std ra")

ax[1, 1].hist(np.log(std_dec), bins=50)
ax[1, 1].set_title("std dec")

ax[0, 2].hist(np.log(std_tec), bins=50)
ax[0, 2].set_title("std tec")

# ax[0, 2].hist(std_tec, bins=50)
# ax[0, 2].set_title("std tec")

# ax[1, 2].hist(non_dc, bins=50)
# ax[1, 2].set_title("non-dc power")

ax[1, 2].scatter(np.log(non_dc), np.log(std_tec))
# ax[1, 2].set_title("non-dc power")

plt.show()
plt.savefig("stats.png")
