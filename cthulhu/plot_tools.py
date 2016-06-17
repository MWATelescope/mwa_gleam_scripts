#!/usr/bin/env python2

import os
import numpy as np
import numpy.ma as ma
import scipy
from scipy.fftpack import fftshift, fftfreq
from scipy.stats import ks_2samp

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
plt.rc("font", family="serif")
mpl.rcParams["font.size"] = 9

from astropy.time import Time

from reconstruct import Obsid, mask_circle


CMAP = plt.cm.hsv
COLOURS = CMAP(np.linspace(0, 1, 360))


def plot_vector_arrows(ra, dec, ra_shifts, dec_shifts, axis, norm=False):
    ## If specified, we can normalise the size of the arrows.
    if norm:
        mag = np.sqrt(ra_shifts**2 + dec_shifts**2)
        mmag = np.max(mag)
    else:
        mmag = 1
    ## Unfortunately, matplotlib's arrow function does not work with vectors.
    # For every source...
    for i in np.arange(len(ra)):
        # ... determine the angle of the vector to use as a colour ...
        angle = np.arctan2(dec_shifts[i], ra_shifts[i])
        colour = COLOURS[np.rint(np.rad2deg(angle)).astype(int)]
        # ... and plot the arrow.
        axis.arrow(ra[i], dec[i],
                   ra_shifts[i]/mmag+1e-6, dec_shifts[i]/mmag+1e-6,
                   width=np.sqrt(ra_shifts[i]**2 + ra_shifts[i]**2)/(30*mmag),
                   head_width=np.sqrt(ra_shifts[i]**2 + dec_shifts[i]**2)/(3*mmag),
                   color=colour)


def plot_source_dots(obsid, axis, size=1, colour="mag", colourbar=True, cmap="Greys"):
    if colour == "mag":
        mag = np.sqrt(obsid.ra_shifts**2 + obsid.dec_shifts**2)
        mag /= np.max(mag)
        image = axis.scatter(obsid.ra, obsid.dec, c=mag,
                             s=size, edgecolors="face", cmap=cmap)
    elif colour == "phase":
        angles = np.arctan2(obsid.dec_shifts, obsid.ra_shifts)
        colours = COLOURS[np.rint(np.rad2deg(angles)).astype(int)]
        image = axis.scatter(obsid.ra, obsid.dec, c=colours,
                             s=size, edgecolors="face", cmap=CMAP)
    else:
        raise ValueError, "Must be either 'mag' or 'phase'."
    if colourbar:
        cb = plt.colorbar(image, ax=axis, format="%.1f")
        cb.set_label("Fraction of maximum shift")


def plot_power_spectrum(obsid, axis, cmap="viridis"):
    ps = obsid.ps

    freqs = fftfreq(ps.shape[0], d=((obsid.tec_extent[0]-obsid.tec_extent[1])/ps.shape[0]))
    freq_min_max = [np.min(freqs), np.max(freqs)]
    freq_axis = np.hstack((freq_min_max, freq_min_max))

    fitted_ps_image = axis.imshow(np.arcsinh(fftshift(ps)), cmap=cmap,
                                  extent=freq_axis, origin="lower")
    cb = plt.colorbar(fitted_ps_image, ax=axis, format="%.1f")
    cb.set_label("arcsinh(Power)")


def plot_spatial_correlation(obsid, axis):
    # import pysal as ps
    # s = len(obsid.tec)
    # n = s**2
    # w = ps.lat2W(s, s, rook=False)
    # # w.transform = 'R'
    # e = np.random.random((n, 1))
    # u = scipy.linalg.inv(np.eye(n) - 0.95 * w.full()[0])
    # u = np.dot(u, e)
    # ul = ps.lag_spatial(w, u)
    # u = (u - u.mean()) / np.std(u)
    # ul = (ul - ul.mean()) / np.std(ul)
    # gu = u.reshape((s, s))

    # # axis.matshow(gu, cmap=plt.cm.YlGn)
    # axis.scatter(u, ul, linewidth=0)

    # s = len(obsid.tec)
    # w = ps.lat2W(s, s)
    # y = obsid.tec.flatten()
    # obsid.g = ps.Gamma(y, w).p_sim_g

    corr = scipy.signal.correlate(obsid.tec, obsid.tec, mode="same")
    axis.imshow(corr)


def setup_subplot(axis, title, xlabel, ylabel, grid=True):
    axis.set_title(title, fontsize=10)
    axis.set_xlabel(xlabel, fontsize=8)
    axis.set_ylabel(ylabel, fontsize=8)
    axis.grid(grid)
    axis.set_aspect("equal")
    axis.set_axis_bgcolor("#3f3f3f")


def generate_diagnostic_figure(obsid, verbosity=0, overwrite=False):
    if not os.path.exists("plots"):
        os.mkdir("plots")

    filename = "plots/%s.png" % obsid.obsid
    if not overwrite and os.path.exists(filename):
        if verbosity > 0:
            print "Not overwriting and the file exists; no plot saved."
        return

    fig, ax = plt.subplots(2, 2, figsize=(12, 9))
    plt.subplots_adjust(hspace=0.25, left=0.05, right=0.95, top=0.95, bottom=0.07)

    # If the obsid is an int, then it's a proper obsid.
    if isinstance(obsid.obsid, int):
        setup_subplot(ax[0, 0],
                      "Obsid: %s (%s)\nMetric: %s" %
                      (obsid.obsid, Time(obsid.obsid, format="gps").iso, obsid.metric),
                      "RA (deg)", "Dec (deg)")
    # Otherwise, it's a placeholder.
    elif isinstance(obsid.obsid, str):
        # Try to convert to an int and a GPS time.
        try:
            obsid.obsid = int(obsid.obsid)
            setup_subplot(ax[0, 0],
                          "Obsid: %s (%s)\nMetric: %s" %
                          (obsid.obsid, Time(obsid.obsid, format="gps").iso, obsid.metric),
                          "RA (deg)", "Dec (deg)")
        except ValueError:
            setup_subplot(ax[0, 0],
                          "File: %s\nMetric: %s" %
                          (obsid.obsid, obsid.metric),
                          "RA (deg)", "Dec (deg)")
    ax[0, 0].set_xlim([obsid.ra_centre+obsid.radius, obsid.ra_centre-obsid.radius])
    ax[0, 0].set_ylim([obsid.dec_centre-obsid.radius, obsid.dec_centre+obsid.radius])
    plot_vector_arrows(obsid.ra, obsid.dec, obsid.ra_shifts, obsid.dec_shifts, ax[0, 0])

    setup_subplot(ax[0, 1], "Power spectrum", "$k_{RA}$ (deg$^{-1}$)", "$k_{Dec}$ (deg$^{-1}$)")
    # plot_power_spectrum(obsid, ax[0, 1])

    from scipy import ndimage
    ax[0, 1].imshow(np.arcsinh(ndimage.filters.laplace(obsid.tec)),
                               origin="lower", cmap="plasma", vmin=-0.5, vmax=0.5)

    setup_subplot(ax[1, 0], "Reconstructed TEC field", "RA (deg)", "Dec (deg)")
    plot_vector_arrows(obsid.ra, obsid.dec, obsid.ra_shifts, obsid.dec_shifts, ax[1, 0], norm=True)
    # plot_vector_arrows(obsid.rra, obsid.rdec, obsid.rra_shifts, obsid.rdec_shifts, ax[1, 0])

    # from scipy.interpolate import SmoothBivariateSpline as spline
    # tec_spline = spline([len(obsid.tec), len(obsid.tec)-1, 1, 0],
    #                     [0, 1, len(obsid.tec)-1, len(obsid.tec)],
    #                     obsid.tec, s=0, kx=1, ky=1)
    # x_grid, y_grid = np.meshgrid(np.arange(len(obsid.tec)), np.arange(len(obsid.tec)))
    # flattened_tec = obsid.tec - tec_spline.ev(x_grid, y_grid, dx=1, dy=0)

    tec = ax[1, 0].imshow(np.arcsinh(obsid.tec), extent=obsid.tec_extent,
                          cmap="plasma", vmin=-2, vmax=2, origin="lower")
    cb = plt.colorbar(tec, ax=ax[1, 0], format="%.2f")
    cb.set_label("arcsinh(TEC)")

    fig.delaxes(ax[1, 1])
    def stat_plotter((value, desc), y_value, fontsize=12):
        plt.figtext(0.55, y_value, desc + ':', fontsize=fontsize)
        if isinstance(value, float):
            plt.figtext(0.75, y_value, "%.4f" % value, fontsize=fontsize)
        else:
            plt.figtext(0.75, y_value, value, fontsize=fontsize)

    def weight_plotter(value, y_value, fontsize=12):
        if isinstance(value, float):
            plt.figtext(0.85, y_value, "%.4f" % value, fontsize=fontsize)
        else:
            plt.figtext(0.85, y_value, value, fontsize=fontsize)

    height = 0.45
    stat_plotter(("$s_i$", "Statistic and weight"), height, fontsize=14)
    weight_plotter("$w_i$", height, fontsize=14)
    height -= 0.03
    for i in xrange(len(obsid.metrics)):
        stat_plotter(obsid.metrics[i], height)
        weight_plotter(obsid.metric_weights[i], height)
        height -= 0.03

    stat_plotter((obsid.metric, "Metric"), 0.15, fontsize=14)
    stat_plotter(("$\sum_{i=1}^%s \/ w_i s_i$" % len(obsid.metrics), "Metric calculation"),
                 0.08, fontsize=14)

    filename = "plots/%s.png" % obsid.obsid
    plt.savefig(filename, dpi=200)
    if verbosity > 0: print "Saved: "+filename
    plt.close()


def raw_and_tec(obsid, filename=None):
    if not filename:
        print "No filename supplied, exiting."
        pass

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    # plt.subplots_adjust(hspace=0.25, left=0.05, right=0.95, top=0.95, bottom=0.07)
    
    setup_subplot(ax[0], "Obsid: %s\nMetric: %.4f" % (obsid.obsid, obsid.metric),
                  "RA (deg)", "Dec (deg)")
    ax[0].set_xlim([obsid.ra_centre+obsid.radius, obsid.ra_centre-obsid.radius])
    ax[0].set_ylim([obsid.dec_centre-obsid.radius, obsid.dec_centre+obsid.radius])
    plot_vector_arrows(obsid.ra, obsid.dec, obsid.ra_shifts, obsid.dec_shifts, ax[0])

    setup_subplot(ax[1], "Reconstructed TEC field\n(values centred at 0, vectors normalised)", "RA (deg)", "Dec (deg)")
    plot_vector_arrows(obsid.ra, obsid.dec, obsid.ra_shifts, obsid.dec_shifts, ax[1], norm=True)
    tec = ax[1].imshow(np.arcsinh(obsid.tec), extent=obsid.tec_extent,
                       cmap="plasma", vmin=-2, vmax=2, origin="lower")
    cb = plt.colorbar(tec, ax=ax[1], format="%.2f")
    cb.set_label("arcsinh(TEC)")

    plt.savefig(filename, dpi=200)
    plt.close()
