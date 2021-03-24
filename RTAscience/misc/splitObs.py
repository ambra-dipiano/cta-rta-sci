# *******************************************************************************
# Copyright (C) 2020 INAF
#
# This software is distributed under the terms of the BSD-3-Clause license
#
# Authors:
# Ambra Di Piano <ambra.dipiano@inaf.it>
# *******************************************************************************

import astropy.units as u
import numpy as np
from astropy.time import Time
import astropy.io.fits as fits
from gammapy.data import DataStore
import os
from os.path import join

path = os.path.join(os.path.expandvars('$DATA'), 'obs/crab/')
filename = 'crab_offax.fits'
nameroot = 'crab_offax'
fitsfile = join(path, filename)
nbins = 1

data_store = DataStore.from_events_files([fitsfile])
observations = data_store.get_observations()
print(data_store.info())

# split 
start = observations[0].gti.time_start
duration = observations[0].gti.time_sum
times = start + np.linspace(0*u.s, duration, nbins)
time_intervals = [Time([tstart, tstop]) for tstart, tstop in zip(times[:-1], times[1:])]
bunches = observations.select_time(time_intervals)
if not os.path.exists(path):
    os.mkdir(path)
#path.mkdir(exist_ok=True)
for i, bunch in enumerate(bunches):
    if i >= 1:
        break
    hdulist = fits.HDUList([fits.PrimaryHDU()])
    hdu = fits.BinTableHDU(bunch.events.table, name="EVENTS")
    hdulist.append(hdu)
    hdu = fits.BinTableHDU(bunch.gti.table, name="GTI")
    hdulist.append(hdu)
    hdulist.writeto(join(path, f"{nameroot}_texp{round(duration.value/nbins)}s_n{i+1:02d}.fits"), overwrite=True)
    print(join(path,f"{nameroot}_texp{round(duration.value/nbins)}s_n{i+1:02d}.fits"))
