#!/usr/bin/env python2

import os
import re
import pickle
from collections import OrderedDict as odict
import multiprocessing as mp

import numpy as np
np.seterr(all="raise")

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, SkyCoord, ICRS


FLAGGING = True
MWA_LOCATION = EarthLocation(lat=-26.756528*u.deg, lon=116.670810*u.deg)

regex_sources_copols_stations = r'NewGainModel: new set of gain models with (\d+) sources, (\d+) copols, (\d+) stations'
regex_iterations = r'global args: do_rts: 1, n_iter: (\d+),'
regex_obsid = r'\s*base file,freq:\s+/scratch2/astronomy883/MWA/data/(\d+)/'

# These regular expressions grab ionospheric data
regex_current = r'\(iter\s+(\d+):\d+\)\s+{l\s*(\S+),m\s*(\S+)}'
regex_total = r'\(iter\s+(\d+):\d+\).*\(TOTAL OFFSET\s+\{l\s*(\S+),m\s*(\S+)\}'
# ... az:za coordinates ...
regex_azza = r'az:za=\s*(\S+):\s*(\S+)\):'
# ... phase centre ...
regex_phase = r'\s*primary beam pointing centre: ha = (-?\d+\.\d+) hrs, dec = (-?\d+\.\d+) deg'
# ... obsid ...
regex_obsid = r'\s*base file,freq:\s+/scratch2/astronomy883/MWA/data/(\d+)/'
# ... and source rank.
regex_rank = r'(\S+) \(rank=(\d+\.\d+)\) I=(\d+\.\d+e.\d+),'


def azza2radec(azza_array, obs_time):
    az, za = azza_array
    altaz = SkyCoord(az=az*u.deg, alt=(90-za)*u.deg, frame="altaz",
                     obstime=obs_time, location=MWA_LOCATION)
    return [altaz.icrs.fk5.ra.deg, altaz.icrs.fk5.dec.deg]


def convert_and_shift(sources, metadata, ra, dec, l_shifts, m_shifts, source_names):
    ra = np.deg2rad(ra)
    dec = np.deg2rad(dec)
    # phase_centre is structured [RA, Dec] in [hrs, deg]
    phase_centre = metadata["primary_beam_pointing_centre"]
    ra_reference = np.deg2rad(phase_centre[0] * 15)
    dec_reference = np.deg2rad(phase_centre[1])
    ra_offset = ra - ra_reference

    ## Coordinate transformations: pg. 388 of Synthesis Imaging in Radio Astronomy II.
    # Determine (l, m) from (RA, Dec).
    l = np.cos(dec)*np.sin(ra_offset)
    l += l_shifts
    m = np.sin(dec)*np.cos(dec_reference) - np.cos(dec)*np.sin(dec_reference)*np.cos(ra_offset)
    m += m_shifts

    # Determine new (RA, Dec) coordinates from the shifted (l, m)
    # It appears that 1-l**2-m**2 is not always > 0: cap it.
    rabbit = 1-l**2-m**2
    rabbit[np.where(rabbit<0)] = 0
    ra_shifted = np.arctan(l/(np.sqrt(rabbit)*np.cos(dec_reference) - m*np.sin(dec_reference))) + ra_reference
    ra_shifted = (np.rad2deg(ra_shifted) + 180) % 360 - 180
    dec_shifted = np.arcsin(m*np.cos(dec_reference)+np.sqrt(rabbit)*np.sin(dec_reference))
    dec_shifted = np.rad2deg(dec_shifted)

    ra = np.rad2deg(ra)
    dec = np.rad2deg(dec)
    ra_shifts = (ra_shifted - ra)*np.cos(np.deg2rad(dec))
    dec_shifts = dec_shifted - dec

    # Feed data back into the sources dictionary with a loop
    for i, s in enumerate(source_names):
        # Just make sure we're using the right source...
        np.testing.assert_approx_equal(sources[s]["dec"], dec[i])
        sources[s]["l"] = l[i]
        sources[s]["m"] = m[i]
        sources[s]["ra_mean_shift"] = ra_shifts[i]
        sources[s]["dec_mean_shift"] = dec_shifts[i]

    return ra_shifts, dec_shifts


def scrape_log_info(log):
    info = {}
    if "master.log" in log:
        return None
    with open(log, 'r') as f:
        for l in f:
            if "NewGainModel" in l:
                try:
                    # For some reason, the "NewGainModel" line can appear twice.
                    # Ignore the second line.
                    source_count
                    continue
                except NameError:
                    matches = re.search(regex_sources_copols_stations, l)
                    source_count = int(matches.group(1))
                    copols = int(matches.group(2))
                    stations = int(matches.group(3))
                    # If the source count is 1, this is a useless log.
                    if source_count == 1:
                        return None
            elif "global args" in l:
                iterations = int(re.search(regex_iterations, l).group(1))
            elif "base file,freq:" in l:
                obsid = re.search(regex_obsid, l).group(1)

                info["log"] = log
                info["obsid"] = obsid
                info["source_count"] = source_count
                info["copols"] = copols
                info["stations"] = stations
                info["iterations"] = iterations
                info["file_size"] = os.path.getsize(log)
                return info


def filter_logs(logs, verbosity=0):
    obsids = {}

    for l in logs:
        log_info = scrape_log_info(l)
        # If the output is not None, we have useful information.
        if log_info:
            obsid = log_info["obsid"]
            if not obsid in obsids:
                obsids[obsid] = {}
                obsids[obsid]["logs"] = [l]
                obsids[obsid]["source_counts"] = [log_info["source_count"]]
                obsids[obsid]["copols"] = [log_info["copols"]]
                obsids[obsid]["stations"] = [log_info["stations"]]
                obsids[obsid]["iterations"] = [log_info["iterations"]]
                obsids[obsid]["file_size"] = [log_info["file_size"]]
                obsids[obsid]["scores"] = [log_info["source_count"]*log_info["copols"]*log_info["stations"]*log_info["iterations"]*os.path.getsize(l)]
            else:
                obsids[obsid]["logs"].append(l)
                obsids[obsid]["source_counts"].append(log_info["source_count"])
                obsids[obsid]["copols"].append(log_info["copols"])
                obsids[obsid]["stations"].append(log_info["stations"])
                obsids[obsid]["iterations"].append(log_info["iterations"])
                obsids[obsid]["file_size"].append(log_info["file_size"])
                obsids[obsid]["scores"].append(log_info["source_count"]*log_info["copols"]*log_info["stations"]*log_info["iterations"]*log_info["file_size"])

    filtered_logs = []
    for o in obsids:
        obsids[o]["best_log"] = [0, ""]
        for i in xrange(len(obsids[o]["logs"])):
            if obsids[o]["scores"][i] > obsids[o]["best_log"][0]:
                obsids[o]["best_log"] = [obsids[o]["scores"][i], obsids[o]["logs"][i]]
        filtered_logs.append(obsids[o]["best_log"][1])

    if verbosity > 0:
        for o in obsids:
            print "%s:" % o
            for i in xrange(len(obsids[o]["logs"])):
                if obsids[o]["logs"][i] == obsids[o]["best_log"][1]:
                    print "\t[%s],\t%i,\t%i,\t%i,\t%i" % (obsids[o]["logs"][i], obsids[o]["source_counts"][i], obsids[o]["iterations"][i], obsids[o]["file_size"][i], obsids[o]["scores"][i]/1e12)
                else:
                    print "\t%s,\t%i,\t%i,\t%i,\t%i" % (obsids[o]["logs"][i], obsids[o]["source_counts"][i], obsids[o]["iterations"][i], obsids[o]["file_size"][i], obsids[o]["scores"][i]/1e12)
        print ""
    return filtered_logs


def rts2dict(log):
    # Dictionaries for various data.
    sources = odict()
    ranks = odict()
    metadata = odict()
    # Lists for order-critical data.
    ra, dec, flux_densities, source_names = [], [], [], []

    print "Reading log file: %s ..." % log,
    # Master logs have no useful data.
    if "_master.log" in log:
        print "skipping; master log file."
        return
    with open(log, 'r') as f:
        for i, l in enumerate(f):
            ## Special cases.
            # The "NOT USED" string only appears in the small (useless?) logs.
            if "NOT USED" in l:
                print "skipping, due to the presence of 'NOT USED'."
                return

            if i < 100 and "initial time:" in l:
                t = float(l.split(" ")[-1])
                metadata["time"] = t
            if i < 100 and "base file,freq:" in l:
                obsid = re.search(regex_obsid, l).group(1)
                metadata["obsid"] = int(obsid)
            if i < 100 and "primary beam pointing centre" in l:
                phase_pair = re.search(regex_phase, l)
                p = [float(phase_pair.group(1)), float(phase_pair.group(2))]
                metadata["primary_beam_pointing_centre"] = p
            elif "rank" in l:
                rank_info = re.search(regex_rank, l)
                if rank_info.group(1) not in ranks:
                    ranks[rank_info.group(1)] = [float(rank_info.group(2)),
                                                 float(rank_info.group(3))]
            ## Actual data
            elif "#iono#" in l:
                array = l.split(" ")
                source = array[3]
                ## If we haven't seen this source before, add it.
                if source not in sources:
                    number = array[2].split("[")[1].split("]")[0]
                    azza_pair = re.search(regex_azza, l)
                    azza_array = [float(azza_pair.group(1)), float(azza_pair.group(2))]
                    ra_pos, dec_pos = azza2radec(azza_array, Time(t, format="jd"))
                    sources[source] = {"source_number": number,
                                       "azza": azza_array,
                                       "azza_time": t,
                                       "l": np.float(0),
                                       "m": np.float(0),
                                       "l_shifts": [],
                                       "m_shifts": [],
                                       "l_mean_shift": np.float(0),
                                       "m_mean_shift": np.float(0),
                                       "ra": ra_pos,
                                       "dec": dec_pos,
                                       "ra_shifts": [],
                                       "dec_shifts": [],
                                       "ra_mean_shift": np.float(0),
                                       "dec_mean_shift": np.float(0),
                                       "rank": ranks[source][0],
                                       "flux_density": ranks[source][1]}

                ## Capture the offset due to the ionosphere on this line.
                ## Note that if "offset too big!!" is on the line, no
                ## ionospheric information is present - pretend there's an
                ## NaN instead.
                if "offset too big!!" in l:
                    l_shift, m_shift = np.nan, np.nan
                else:
                    ## If for some reason you want to ionosphere shift since
                    ## the last iteration, this line captures that.
                    # current = re.search(regex_current, l)

                    current = re.search(regex_total, l)
                    l_shift, m_shift = float(current.group(2)), float(current.group(3))

                ## Don't forget to convert to degrees.
                sources[source]["l_shifts"].append(l_shift/3600)
                sources[source]["m_shifts"].append(m_shift/3600)
    print "done."

    ## We now have a populated sources dictionary, with coordinates and shifts for each.
    ## Do a little more work to convert (l,m) to (RA,Dec).
    l_shifts, m_shifts = [], []
    ## Assign a mean l & m shift
    for s in sources:
        # Some sources have no data. Delete them here.
        if len(sources[s]["l_shifts"]) < 4 or len(sources[s]["m_shifts"]) < 4:
            del sources[s]
            continue
        elif not any(np.isfinite(sources[s]["l_shifts"])):
            del sources[s]
            continue
        elif not any(np.isfinite(sources[s]["m_shifts"])):
            del sources[s]
            continue
        elif FLAGGING and not any(np.isfinite(sources[s]["l_shifts"][2:])):
            del sources[s]
            continue
        elif FLAGGING and not any(np.isfinite(sources[s]["m_shifts"][2:])):
            del sources[s]
            continue

        if FLAGGING:
            # Ignore the first three datums.
            sources[s]["l_mean_shift"] = np.nanmean(sources[s]["l_shifts"][2:])
            sources[s]["m_mean_shift"] = np.nanmean(sources[s]["m_shifts"][2:])
        else:
            sources[s]["l_mean_shift"] = np.nanmean(sources[s]["l_shifts"])
            sources[s]["m_mean_shift"] = np.nanmean(sources[s]["m_shifts"])

        ## Add data to lists to preserve orders.
        l_shifts.append(sources[s]["l_mean_shift"])
        m_shifts.append(sources[s]["m_mean_shift"])
        ## While we're here, make RA friendly about 0.
        ra.append(((sources[s]["ra"]) + 180) % 360 - 180)
        dec.append(sources[s]["dec"])
        flux_densities.append(sources[s]["flux_density"])
        source_names.append(s)

    # numpy-ise the lists for performance
    ra = np.array(ra)
    dec = np.array(dec)
    l_shifts = np.array(l_shifts)
    m_shifts = np.array(m_shifts)
    flux_densities = np.array(flux_densities)
    ra_shifts, dec_shifts = convert_and_shift(sources, metadata, ra, dec, l_shifts, m_shifts, source_names)

    ## Bundle the useful bits into a new dictionary
    product = {}
    product["sources"] = sources
    product["metadata"] = metadata
    product["ra"] = ra
    product["dec"] = dec
    product["ra_shifts"] = ra_shifts
    product["dec_shifts"] = dec_shifts
    product["flux_densities"] = flux_densities
    return product


def rts2pickle(log):
    ## Run the RTS log through the sausage-machine.
    data = rts2dict(log)
    # If the output was nothing, simply return so no pickle is written.
    if not data: return

    filename = "%s.pickle" % data["metadata"]["obsid"]
    with open(filename, "w") as f:
        pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
    print "Written: %s" % filename
