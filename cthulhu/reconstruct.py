#!/usr/bin/env python2

import os
import sys
import argparse

import numpy as np
import scipy.stats as stats
from scipy import signal
from scipy.fftpack import fft2, ifft2, fftshift, fftfreq
from scipy.interpolate import griddata
from scipy.spatial import distance

from pyGrad2Surf import g2s as g2s


def mask_circle(matrix, radius, mask=1):
    h, w = matrix.shape
    centre = np.array(matrix.shape)/2
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    d = (x - centre[0])**2 + (y - centre[1])**2
    m = d < radius**2
    if mask == 1:
        matrix[np.where(m)] = 0
    else:
        matrix[~np.where(m)] = 0
    return matrix


class Obsid(object):
    """
    Every obsid has at least four vectors associated with sources:
    - RA positions
    - Dec positions
    - RA shifts
    - Dec shifts

    Optionally, for diagnostics, the obsid value and filename can be supplied.
    """

    def __init__(self, data, filename=""):
        if isinstance(data, dict):
            ra = data["ra"]
            dec = data["dec"]
            ra_shifts = data["ra_shifts"]
            dec_shifts = data["dec_shifts"]

            # Use the obsid if supplied.
            try:
                self.obsid = data["metadata"]["obsid"]
            # Otherwise, use the filename.
            except NameError:
                self.obsid = '.'.join(filename.split('/')[-1].split('.')[:-1])

        # If there are four elements in the unpacked data, assume it's:
        # [ra, dec, ra_shifts, dec_shifts]
        elif len(data) == 4:
            ra, dec, ra_shifts, dec_shifts = data
            if not (len(ra) == len(dec) and
                    len(ra) == len(ra_shifts) and
                    len(ra) == len(dec_shifts)):
                raise ValueError("Unpacked data contains four lists, but "
                                 "they are not all the same size.")
            self.obsid = '.'.join(filename.split('/')[-1].split('.')[:-1])

        self.ra         = ra
        self.dec        = dec
        self.ra_shifts  = ra_shifts
        self.dec_shifts = dec_shifts
        # self.ra_shifts  = np.random.normal(scale=1.1/data["flux_densities"]/3600)
        # self.dec_shifts = np.random.normal(scale=1.0/data["flux_densities"]/3600)
        # from cthulhu.rts_log_tools import convert_and_shift
        # print np.arcsin(1.0/data["flux_densities"])
        # self.ra_shifts, self.dec_shifts = convert_and_shift(data["sources"], data["metadata"], ra, dec, 1.1/data["flux_densities"], 1.0/data["flux_densities"], data["sources"])


        ## For MWA data, many sources may lie in the sidelobes. Here, we attempt
        ## to isolate sources only in the primary beam.
        # Use all the sources to find an approximate centre.
        bulk_centre_ra = np.mean(ra)
        bulk_centre_dec = np.mean(dec)

        ## Determine the radius of the primary beam.
        # Histogram the distances between the mean centre point and every source,
        # then step through the histogram until the incremental sum is less than 5%.
        distances = distance.cdist([[bulk_centre_ra, bulk_centre_dec]], zip(ra, dec)).flatten()
        hist, bin_edges = np.histogram(distances, bins=50, range=(0, 125))
        old_count, new_count, index = float(hist[0]), float(np.sum(hist[0:2])), 1
        while (new_count - old_count)/old_count > 0.05:
            index += 1
            old_count = new_count
            new_count += hist[index]
        self.radius = bin_edges[index]

        ## Recalculate the centre, based on the sources within the radius,
        ## and specify the sources to be used for analysis.
        filtered = np.array([[a, b, c, d] for a,b,c,d,e
                             in zip(ra, dec, ra_shifts, dec_shifts, distances) if e < self.radius])
        self.fra         = filtered[:, 0]
        self.fdec        = filtered[:, 1]
        self.fra_shifts  = filtered[:, 2]
        self.fdec_shifts = filtered[:, 3]
        self.ra_centre   = np.mean(self.fra)
        self.dec_centre  = np.mean(self.fdec)


    def reconstruct_tec(self, crop=True, g2s_method=g2s, interp_method="linear"):
        # def get_semiregular_sequence(vector, N):
        #     ## Blame Steven.
        #     pdf = stats.gaussian_kde(vector)
        #     n = len(vector)
        #     x = np.sort(pdf.resample(2*n).flatten())
        #     x = x[np.logical_and(x > vector.min(),
        #                          x < vector.max())]
        #     y = len(x) % N
        #     if y == 0: y = N
        #     start = np.random.randint(0, high=y)
        #     return x[start::len(x)/N]

        # n = np.ceil(np.sqrt(len(self.ra))).astype(int)
        # x = get_semiregular_sequence(self.fra, n)
        # y = get_semiregular_sequence(self.fdec, n)
        # grid_x, grid_y = np.meshgrid(x, y)

        grid_y, grid_x = np.mgrid[-self.radius:self.radius:101j,
                                  -self.radius:self.radius:101j]
        grid_x += self.ra_centre
        grid_y += self.dec_centre

        ## Use griddata to interpolate a grid to the both the RA and Dec shifts.
        ## Negatives are required for a physically realistic representation -
        ## source shifts move from high surface values to low surface values.
        ## Flipping left-right reflects RA increasing right-to-left.
        self.grid_dra = np.flipud(np.fliplr(griddata(np.vstack((self.ra, self.dec)).T, self.ra_shifts,
                                            (grid_x, grid_y), method=interp_method, fill_value=0)))
        self.grid_ddec = np.flipud(np.fliplr(griddata(np.vstack((self.ra, self.dec)).T, self.dec_shifts,
                                             (grid_x, grid_y), method=interp_method, fill_value=0)))
        # Finally, use the specified g2s method on the interpolated grids.
        self.tec = np.flipud(g2s_method(grid_x[0,:], grid_y[:,0], self.grid_dra, self.grid_ddec))

        ## Remove the "constant" degeneracy from the TEC.
        self.tec -= np.mean(self.tec)
        self.tec_extent = (self.ra_centre+self.radius,
                           self.ra_centre-self.radius,
                           self.dec_centre-self.radius,
                           self.dec_centre+self.radius)

        if crop:
            self.crop_tec()


    def crop_tec(self, crop_factor=1./np.sqrt(2)):
        ## Before performing any statistics, it's a good idea to mask or crop
        ## the regions of the matrices that less sources.
        self.tec_extent = (self.ra_centre+self.radius*crop_factor,
                           self.ra_centre-self.radius*crop_factor,
                           self.dec_centre-self.radius*crop_factor,
                           self.dec_centre+self.radius*crop_factor)
        def cropper(matrix):
            length = len(matrix)
            cropped_length = int(length * crop_factor)
            return matrix[(length-cropped_length)/2:length-(length-cropped_length)/2, 
                          (length-cropped_length)/2:length-(length-cropped_length)/2]
        self.tec = cropper(self.tec)
        self.grid_dra = cropper(self.grid_dra)
        self.grid_ddec = cropper(self.grid_ddec)


    def obsid_metric(self):
        try:
            self.tec
        except AttributeError:
            self.reconstruct_tec()
            self.crop_tec()

        try:
            self.non_dc_power
        except AttributeError:
            self.tec_power_spectrum()

        self.s1 = [np.median(np.abs(self.ra_shifts)), "median(abs(ra_shifts))"]
        self.s2 = [np.median(np.abs(self.dec_shifts)), "median(abs(dec_shifts))"]
        self.s3 = [np.std(self.ra_shifts), "std(ra_shifts)"]
        self.s4 = [np.std(self.dec_shifts), "std(dec_shifts)"]
        self.s5 = [np.std(self.tec), "std(TEC)"]
        self.hessian = hessian(self.tec)
        self.s6 = [np.std(np.abs(self.hessian[0, 0]) + np.abs(self.hessian[0, 1]) + np.abs(self.hessian[1, 1])), "std(hessian)"]
        from scipy import ndimage
        laplacian = ndimage.filters.laplace(self.tec)
        self.s14 = [np.std(laplacian), "std($\mathcal{L}$(TEC))"]
        # print "ndimage laplacian: %s" % np.std(laplacian)
        # print (np.trace(self.hessian[0, 0]) + np.trace(self.hessian[1, 1]))

        self.s7 = stats.skew(self.ra_shifts, axis=None)
        self.s8 = stats.skew(self.dec_shifts, axis=None)
        self.s9 = stats.kurtosis(self.ra_shifts, axis=None)
        self.s10 = stats.kurtosis(self.dec_shifts, axis=None)
        self.s11 = stats.skew(self.tec, axis=None)
        self.s12 = stats.kurtosis(self.tec, axis=None)
        self.s13 = self.non_dc_power

        self.metrics = [self.s1, self.s2, self.s5, self.s14]
        # self.metric_weights = [16.7395, 8.8566, 6.0798, -17.6258]
        self.metric_weights = [16.7395, 8.8566, 6.0798, 10]
        # self.metric_weights = np.ones(len(self.metrics))
        self.metric = np.sum([x[0]*y for x, y in zip(self.metrics, self.metric_weights)])


    def tec_power_spectrum(self):
        w = signal.blackman(self.tec.shape[0])
        w = np.outer(w, w)

        ps = np.abs(fft2(self.tec*w))**2
        # ps = np.abs(fft2(matrix))**2

        def non_dc_power(ps):
            ps_shifted = fftshift(ps)
            h, w = ps_shifted.shape
            c = len(ps)/2
            x, y = np.meshgrid(np.arange(w), np.arange(h))
            d = (x - c)**2 + (y - c)**2

            r = 1

            powers = []
            while r < len(ps)/4:
                m = d < r**2
                powers.append(np.sum(ps_shifted[np.where(m)])-np.sum(powers))
                r += 1
            return np.sum(powers[3:])/np.sum(powers[0:3])

        self.ps = ps
        self.non_dc_power = non_dc_power(ps)


    def tec_residuals(self):
        matrix_length = len(self.tec)
        ddec, dra = np.gradient(self.tec)

        visible = np.array([(a, b, c, d) for a,b,c,d
                            in zip(self.ra, self.dec, self.ra_shifts, self.dec_shifts)
                            if  a > self.tec_extent[1] and a < self.tec_extent[0] 
                            and b > self.tec_extent[2] and b < self.tec_extent[3]])
        v_ra         = visible[:, 0]
        v_dec        = visible[:, 1]
        v_ra_shifts  = visible[:, 2]
        v_dec_shifts = visible[:, 3]

        ## RA = ax + b
        ## where x is the matrix coordinate
        ## a = (RA extent)/(Matrix length), b = RA value @ Matrix[0]
        a = (self.tec_extent[0] - self.tec_extent[1])/matrix_length
        b = self.tec_extent[0]
        x = ((b - v_ra)/a).astype(int)
        a = (self.tec_extent[3] - self.tec_extent[2])/matrix_length
        b = self.tec_extent[2]
        y = ((v_dec - b)/a).astype(int)

        def printer(index):
            print v_ra[index], v_dec[index],\
                x[index], y[index],\
                v_ra_shifts[index], v_dec_shifts[index],\
                dra[x[index], y[index]],\
                ddec[x[index], y[index]]
        # printer(0)
        # printer(1)
        # printer(2)
        # printer(3)

        # tec_ra_shifts = dra[y, x]
        # tec_dec_shifts = ddec[y, x]
        tec_ra_shifts = self.grid_dra[y, x]
        tec_dec_shifts = self.grid_ddec[y, x]

        self.dra = dra
        self.ddec = ddec
        self.rra = v_ra
        self.rdec = v_dec
        self.rra_shifts = v_ra_shifts + tec_ra_shifts
        self.rdec_shifts = v_dec_shifts + tec_dec_shifts


    def save_tec_fits(self, filename=None, verbosity=0, overwrite=False):
        if not filename:
            if not os.path.exists("fits_files"):
                os.mkdir("fits_files")
            filename = "fits_files/%s.fits" % self.obsid

        if not overwrite and os.path.exists(filename):
            return
        elif overwrite and os.path.exists(filename):
            os.remove(filename)

        from astropy.io import fits
        hdu = fits.PrimaryHDU(self.tec)
        hdulist = fits.HDUList([hdu])
        hdulist.writeto(filename)
        if verbosity > 0: print "Saved: "+filename


def hessian(x):
    """
    Calculate the hessian matrix with finite differences
    Parameters:
        - x : ndarray
    Returns:
        an array of shape (x.dim, x.ndim) + x.shape
        where the array[i, j, ...] corresponds to the second derivative x_ij
    http://stackoverflow.com/a/31207520/6263858

    N.B. For 2D matrices (i.e. this work), hessian[0, 0] corresponds to d2/dy2, not d2/dx2.
    """
    x_grad = np.gradient(x)
    hessian = np.empty((x.ndim, x.ndim) + x.shape, dtype=x.dtype)
    for k, grad_k in enumerate(x_grad):
        # iterate over dimensions
        # apply gradient again to every component of the first derivative.
        tmp_grad = np.gradient(grad_k)
        for l, grad_kl in enumerate(tmp_grad):
            hessian[k, l, :, :] = grad_kl
    return hessian
