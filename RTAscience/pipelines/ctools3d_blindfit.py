# *******************************************************************************
# Copyright (C) 2021 INAF
#
# This software is distributed under the terms of the BSD-3-Clause license
#
# Authors:
# Ambra Di Piano <ambra.dipiano@inaf.it>
# *******************************************************************************

import numpy as np
import os
import sys
import argparse
from os.path import isdir, join, isfile
from RTAscience.lib.RTACtoolsAnalysis import RTACtoolsAnalysis
from RTAscience.lib.RTAManageXml import ManageXml
from RTAscience.lib.RTAUtils import phflux_powerlaw
from RTAscience.cfg.Config import Config
from RTAscience.lib.RTAVisualise import plotSkymap

parser = argparse.ArgumentParser(description='ADD SCRIPT DESCRIPTION HERE')
parser.add_argument('-f', '--cfgfile', type=str, required=True, help="Path to the yaml configuration file")
parser.add_argument('--merge', type=str, default='true', help='Merge in single phlist (true) or use observation library (false)')
parser.add_argument('--remove', type=str, default='true', help='Keep only outputs')
parser.add_argument('--print', type=str, default='false', help='Print out results')
args = parser.parse_args()

cfg = Config(args.cfgfile)

# GRB ---!
if cfg.get('runid') == 'all':
    runids = [f.replace('.fits', '') for f in os.listdir(cfg.get('catalog')) if isfile(join(cfg.get('catalog'), f))]
elif type(cfg.get('runid')) == str:
    runids = [cfg.get('runid')]
else:
    runids = cfg.get('runid')

# general ---!
start_count = cfg.get('start_count')
trials = cfg.get('trials') 
if cfg.get('offset') == 'str':
    offset = cfg.get('offset').upper()
else:
    offset = cfg.get('offset')
# paths ---!
datapath = cfg.get('data')
if not isdir(datapath):  # main data folder
    raise ValueError('Please specify a valid path')
if not isdir(join(datapath, 'obs')):  # obs parent folder
    raise ValueError(f'Missing obs parent folder in {datapath}')
if not isdir(f"{datapath}/outputs"):
    os.mkdir(f"{datapath}/outputs")
if not isdir(f"{datapath}/rta_products"):
    os.mkdir(f"{datapath}/rta_products")
if not isdir(f"{datapath}/skymaps"):
    os.mkdir(f"{datapath}/skymaps")

# ------------------------------------------------------ loop runid --- !!!
for runid in runids:
    print(f'Processing runid: {runid}\n')
    # outputs
    logname = f"{datapath}/outputs/{runid}/{cfg.get('caldb')}-{cfg.get('irf')}_seed{start_count+1:06d}-{start_count+1+trials:06d}_flux{cfg.get('scalefluxfactor')}_offset{offset}_delay{cfg.get('delay')}.txt"
    if not isdir(f"{datapath}/outputs/{runid}"):
        os.mkdir(f"{datapath}/outputs/{runid}")
    if not isdir(f"{datapath}/rta_products/{runid}"):
        os.mkdir(f"{datapath}/rta_products/{runid}")
    png = f"{datapath}/skymaps/{runid}"
    if not isdir(png):
        os.mkdir(png)
    if isfile(logname):
        os.remove(logname)
    # grb path ---!
    grbpath = join(datapath, 'obs', runid)  
    if not isdir(grbpath):
        raise FileExistsError(f"Directory {runid} not found in {datapath}/obs")
    rtapath = f'{datapath}/rta_products/{runid}'

    # ------------------------------------------------------ loop trials ---!!!
    for i in range(trials):
        count = start_count + i + 1
        #print(f'seed = {count:06d}')
        name = f'ebl{count:06d}'
        if args.merge.lower() == 'true':
            phlist = join(grbpath, name+'.fits')
            sky = phlist.replace('.fits', '_sky.fits').replace('/obs/', '/rta_products/')
        else:
            phlist = join(grbpath, f'{name}.xml')
            sky = phlist.replace('.xml', '_sky.fits').replace('/obs/', '/rta_products/')
        candidates = sky.replace('_sky.fits', '_sources.xml')
        fit = candidates.replace('sources', 'fit')
        if args.print.lower() == 'true':
            print(f'Input observation: {phlist}')

        # ---------------------------------------------------------- loop exposure times ---!!!

        for texp in cfg.get('exposure'):
            # selection ---!
            selphlist = phlist.replace(f'{name}', f'texp{texp}s_{name}')
            grb = RTACtoolsAnalysis()
            grb.configure(cfg)
            grb.t = [cfg.get('delay'), cfg.get('delay')+texp]
            if args.print.lower() == 'true':
                print(f"Selection t = {grb.t} s")
            grb.input = phlist
            grb.output = selphlist
            if args.merge.lower() == 'true':
                grb.run_selection()
            else:
                prefix = join(grbpath, f'texp{texp}s_')
                grb.run_selection(prefix=prefix)
            # skymap ---!
            grb.input = selphlist
            grb.output = sky
            grb.run_skymap(wbin=cfg.get('skypix'), roi_factor=cfg.get('skyroifrac'))
            # blind-search ---!
            grb.sigma = cfg.get('sgmthresh')
            grb.corr_rad = cfg.get('smooth')
            grb.max_src = cfg.get('maxsrc')
            grb.input = sky
            grb.output = candidates
            grb.run_blindsearch()
            if cfg.get('plotsky'):
                plotSkymap(sky, reg=candidates.replace('.xml', '.reg'), suffix=f'{texp}s', png=png)
            # modify model
            detection = ManageXml(candidates)
            detection.modXml(overwrite=True)
            detection.setTsTrue() 
            detection.parametersFreeFixed(src_free=['Prefactor'])
            detection.closeXml()
            # fit ---!
            grb.input = selphlist
            grb.model = candidates
            grb.output = fit
            grb.run_maxlikelihood()
            # stats ---!
            results = ManageXml(fit)
            try:
                coords = results.getRaDec()
                ra = coords[0][0]
                dec = coords[1][0]
                ts = results.getTs()[0]
                sqrt_ts = np.sqrt(ts)
            except IndexError:
                sqrt_ts = np.nan
                print('Candidate not found.')
            if sqrt_ts >= 0:
                # flux ---!
                spectra = results.getSpectral()
                index, pref, pivot = spectra[0][0], spectra[1][0], spectra[2][0]
                err = results.getPrefError()[0]
                flux = phflux_powerlaw(index, pref, pivot, grb.e, unit='TeV')
                flux_err = phflux_powerlaw(index, err, pivot, grb.e, unit='TeV')
            else:
                ra, dec, ts, sqrt_ts, flux, flux_err = np.nan, np.nan, np.nan, np.nan, np.nan, np.nan

            row = f"{runid} {count} {texp} {sqrt_ts} {flux} {flux_err} {ra} {dec} {offset} {cfg.get('delay')} {cfg.get('scalefluxfactor')} {cfg.get('caldb')} {cfg.get('irf')}\n"
            if args.print.lower() == 'true':
                print(f"Results: {row}")
            if not isfile(logname):
                hdr = 'runid seed texp sqrt_ts flux flux_err ra dec offset delay scaleflux caldb irf\n'
                log = open(logname, 'w+')
                log.write(hdr)
                log.write(row)
                log.close()
            else:
                log = open(logname, 'a')
                log.write(row)
                log.close()

            del grb
    if args.remove.lower() == 'true':
        print('Remove files')
        os.system(f"rm {datapath}/obs/{runid}/*{name}*")
        os.system(f"rm {datapath}/rta_products/{runid}/*{name}*")
print('...done.\n')