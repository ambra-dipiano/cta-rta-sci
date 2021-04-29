# *******************************************************************************
# Copyright (C) 2020 INAF
#
# This software is distributed under the terms of the BSD-3-Clause license
#
# Authors:
# Ambra Di Piano <ambra.dipiano@inaf.it>
# *******************************************************************************

import os
import astropy.units as u
import healpy as hp
import numpy as np
from astropy.io import fits
from os.path import join, expandvars

# center of fov from FITS ---!
def get_pointing(fits_file):
    '''Given a template, returns the target coordinates.'''
    with fits.open(fits_file) as hdul:
        ra = hdul[0].header['RA']
        dec = hdul[0].header['DEC']
    return (ra, dec)

# center of fov from FITS ---!
def get_offset(fits_file, merger_map):
    '''Given a template and a merger map, returns the offset (in RA and DEC) between the maximum sky localisation probability and the target coordinates.'''
    true = get_pointing(fits_file)
    alert = get_alert_pointing_gw(merger_map)
    return (true[0]-alert[0], true[1]-alert[1])

# retrieve telescope pointing coordinates from alert probability map ---!
def get_alert_pointing_compressed(merger_map):
    '''Given a compressed merger map, it returns the maximum sky localisation probability coordinates.'''
    # load map ---!
    merger_map = merger_map.replace('.gz','')
    os.system(f'gunzip {merger_map}.gz')
    map = hp.read_map(merger_map, dtype=None)
    pixels = len(map)
    axis = hp.npix2nside(pixels)
    # search max prob coords ---!
    pmax = np.argmax(map)
    theta, phi = hp.pix2ang(axis, pmax)
    pointing = (np.rad2deg(phi), np.rad2deg(0.5 * np.pi - theta))
    os.system(f'gzip {merger_map}')
    return pointing

# retrieve telescope pointing coordinates from alert probability map ---!
def get_alert_pointing_gw(merger_map):
    '''Given a merger map, it returns the maximum sky localisation probability coordinates.'''
    if not os.path.isfile(merger_map):
        raise ValueError(f'Merger map {merger_map} not found.')
    # load map ---!
    map = hp.read_map(merger_map, dtype=None)
    pixels = len(map)
    axis = hp.npix2nside(pixels)
    # search max prob coords ---!
    pmax = np.argmax(map)
    theta, phi = hp.pix2ang(axis, pmax)
    pointing = (np.rad2deg(phi), np.rad2deg(0.5 * np.pi - theta))
    return pointing

def increase_exposure(start, stop, function='double'):
    '''Increse the exposure time with a given function: double, power2, times10.'''
    if function.lower() == 'double':
        y = [start]
        i = 0
        while y[i] < stop:
            y.append(y[i]*2)
            i += 1
    elif function.lower() == 'power':
        y = [start]
        i = 0
        while y[i] < stop:
            y.append(y[0]**(i+2))
            i += 1
    elif function.lower() == 'times10':
        y = [start]
        i = 0
        while y[i] < stop:
            y.append(y[i]*10)
            i += 1
    elif function.lower() == 'linear':
        y = [start]
        i = 0
        while y[i] < stop:
            y.append(start*(i+2))
            i += 1    # check stop
    if y[-1] > stop:
        y[-1] = stop
    elif y[-1] < stop:
        y.append(stop)
    return y

# compute integral photon flux for PL model ---!
def phflux_powerlaw(gamma, k0, e0=1, erange=(0.03, 150.0), unit='TeV'):
    '''Compute the integrated photon flux for a single power law spectral model.'''
    if unit == 'eV':
        conv = 1e-6
    elif unit == 'keV':
        conv = 1e-3
    elif unit == 'MeV':
        conv = 1
    elif unit == 'GeV':
        conv = 1e3
    else:
        conv = 1e6
    e1 = erange[0] * conv
    e2 = erange[1] * conv
    delta = gamma + 1
    factor = k0 / (e0**gamma * delta)
    flux = factor * (e2**delta - e1**delta)
    return flux

# compute integral energy flux for PL model ---!
def enflux_powerlaw(gamma, k0, e0=1, erange=(0.03, 150.0), unit='TeV'):
    '''Compute the integrated energy flux for a single power law spectral model.'''
    if unit == 'eV':
        conv = 1.60218e-12
    elif unit == 'keV':
        conv = 1.60218e-9
    elif unit == 'MeV':
        conv = 1.60218e-6
    elif unit == 'GeV':
        conv = 1.60218e-3
    else:
        conv = 1.60218
    e1 = erange[0] * conv
    e2 = erange[1] * conv
    k0 *= conv
    e0 *= conv
    delta = gamma+1
    factor = k0 / (e0**gamma * delta)
    flux = factor * (e2**delta - e1**delta)
    return flux

# returns a random total delay time (slew time + gw latency) within given ranges ---!
def totalDelay(slew=(0,50), gw_latency=(0,36000)):
    '''Returns random delay accounting for given delay and alert latency within ranges.'''
    tslew = np.random.uniform(slew[0], slew[1], 1)
    tgw = np.random.uniform(gw_latency[0], gw_latency[1])
    delay = tslew + tgw
    return delay

# get wobble pointing for given target
def wobble_pointing(target, nrun, clockwise=True, offset=0.5):
    '''Returns wobble pointing coordinates with given offset (in DEC).'''
    if clockwise:
        wobble = [(0., offset), (-offset, 0.), (0., -offset), (offset, 0.)]
    else:
        wobble = [(0., offset), (offset, 0.), (0., -offset), (-offset, 0.)] 
    wobble_index = nrun % 4
    print(wobble[wobble_index])
    pointing = (target[0] + wobble[wobble_index][0], target[1] + wobble[wobble_index][1])
    return pointing

# get mergermap file
def get_mergermap(run, path):
    '''Gets merger map of runid.'''
    runid = run.split('_')
    merger = f'{runid[0]}_Merger{runid[1]}_skymap.fits'
    if merger in os.listdir(path):
        return os.path.join(path, merger)
    elif merger+'.gz' in os.listdir(path):
        os.system(f"gunzip {join(path, merger)}.gz")
        return os.path.join(path, merger)
    else:
        print(f'Merger map {merger} for not found in path: {path}.')
        return None

def compute_prefactor(flux, erange, gamma=-2.4, e0=1e6, unit='MeV'):
    '''Compute the prefactor k0 from photon flux for a simple power law spectral model.'''
    if unit == 'eV':
        conv = 1e-6
    elif unit == 'keV':
        conv = 1e-3
    elif unit == 'MeV':
        conv = 1
    elif unit == 'GeV':
        conv = 1e3
    else:
        conv = 1e6

    e1 = erange[0] * conv
    e2 = erange[1] * conv
    delta = gamma + 1
    factor = flux / (e2**delta - e1**delta)
    k0 = factor * (e0**gamma * delta)
    return k0

def compute_phcount(texp, irf, k0, offset=1.638, eTeV=[0.03, 150.0], nbin=1000):
    '''Compute the photon count from the prefactor, for given irf, off-axs angle, and energy range.'''
    with fits.open(irf) as h:
        aeff = h['EFFECTIVE AREA'].data

    elow = aeff['ENERG_LO'][0] # TeV
    ehigh = aeff['ENERG_HI'][0] # TeV
    thetalo = aeff['THETA_LO'][0] # deg
    thetahi = aeff['THETA_HI'][0] # deg
    area = aeff['EFFAREA'][0] # m2
    # energy in TeV
    x = (elow+ehigh)/2
    y = (thetalo+thetahi)/2
    z = area
    # interpolate
    f = interp2d(x, y, z, kind='linear')
    yref = offset
    eref = np.logspace(np.log10(eTeV[0]), np.log10(eTeV[1]), nbin)
    s = 0
    for i in range(len(eref)-1):
        # aeff at energy bin edges; convert m2 -> cm2
        a1 = f(eref[i], yref) * 10**4 # cm2
        a2 = f(eref[i+1], yref) * 10**4 # cm2
        # delta ph = prefactor * exposure * mean aeff * delta energy (convert TeV -> MeV)
        ph = k0 * texp * (a1+a2)/2 * (eref[i+1]-eref[i])*1e6 # dph = ph/cm2/s/MeV * s * <cm2> * dMeV
        # sum photons in bins
        s += float(ph) # sum dph
    return s

def phmOptions(cfg, texp, target, pointing, index=-2.4, bkg_method="reflection", radius=0.2, pixsize=0.05, runid='crab', verbose=0):
    opts = {}
    opts['verbose'] = verbose
    opts['irf_file'] = join(expandvars('$CTOOLS'), f"share/caldb/data/cta/{cfg.get('caldb')}/bcf/{cfg.get('irf')}/irf_file.fits")
    opts['source_ra'] = target[0]
    opts['source_dec'] = target[1]
    opts['pointing_ra'] = pointing[0]
    opts['pointing_dec'] = pointing[1]
    opts['region_radius'] = radius
    opts['background_method'] = bkg_method
    opts['save_off_regions'] = f"{expandvars(cfg.get('data'))}/rta_products/{runid}/off_regions.reg"
    opts['energy_min'] = cfg.get('emin')
    opts['energy_max'] = cfg.get('emax')
    opts['pixel_size'] = pixsize
    opts['begin_time'] = cfg.get('delay')
    opts['end_time'] =  cfg.get('delay') + texp
    opts['step_time'] = texp
    opts['power_law_index'] = index
    return opts