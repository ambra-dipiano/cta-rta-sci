# *******************************************************************************
# Copyright (C) 2021 INAF
#
# This software is distributed under the terms of the BSD-3-Clause license
#
# Authors:
# Ambra Di Piano <ambra.dipiano@inaf.it>
# *******************************************************************************

import numpy as np
import os, argparse
from time import time
from astropy.io import fits
from multiprocessing import Pool
from os.path import isdir, isfile, join, expandvars

from RTAscience.cfg.Config import Config
from RTAscience.lib.RTAManageXml import ManageXml
from RTAscience.lib.RTACtoolsSimulation import RTACtoolsSimulation
from RTAscience.lib.RTAUtils import get_pointing, get_mergermap, get_alert_pointing_gw


def main(args):

    cfg = Config(args.cfgfile)

    # general ---!
    if cfg.get('simtype').lower() != 'bkg':
        raise ValueError('This script only allows bakground simulations')
    trials = cfg.get('trials')  # trials
    tobs = cfg.get('tobs')  # total obs time (s)

    # paths ---!
    datapath = cfg.get('data')
    if not isdir(datapath):  # main data folder
        raise ValueError('Please specify a valid path')
    if not isdir(join(datapath, 'obs')):  # obs parent folder
        os.mkdir(join(datapath, 'obs'))
    bkgpath = join(datapath, 'obs', 'backgrounds')
    if not isdir(bkgpath):
        os.mkdir(bkgpath)
    # background model ---!
    bkg_model = expandvars(cfg.get('bkg'))  # XML background model

    # ------------------------------------------------------- loop runid --- !!!
    pointing = [0., 0.]
    if pointing[1] < 0:
        pointing[0] += 0.0
        pointing[1] += -cfg.get('offset')
    else:
        pointing[0] += 0.0
        pointing[1] += cfg.get('offset')

    # ---------------------------------------------------- loop trials ---!!!
    if args.mp_enabled:
            
        with Pool(args.mp_threads) as p:
            times = p.map(simulateTrial, [ (i, cfg, pointing, bkg_model, bkgpath, tobs) for i in range(trials)])

    else:
        
        for i in range(trials):
            times = simulateTrial((i, cfg, pointing, bkg_model, bkgpath, tobs))

    if len(times) > 1:
        print(f"Trial elapsed time (mean): {np.array(times).mean()}")
    else:
        print(f"Trial elapsed time: {times[0]}")    

    print('\n... done.\n')


def simulateTrial(trial_args):

    start_t = time()
    i=trial_args[0]
    cfg=trial_args[1]
    pointing=trial_args[2]
    bkg_model=trial_args[3]
    bkgpath=trial_args[4]
    tobs=trial_args[5]

    count = cfg.get('start_count') + i + 1
    name = f'bkg{count:06d}'
    # setup ---!
    sim = RTACtoolsSimulation()
    sim.configure(cfg)
    sim.seed = count
    sim.pointing = pointing
    sim.caldb = cfg.get('caldb')
    sim.irf = cfg.get('irf')
    sim.roi = cfg.get('roi')

    print('Simulate empty fields')
    sim.seed = count
    sim.t = [0, tobs]
    bkg = os.path.join(bkgpath, f'{name}.fits')
    sim.model = bkg_model
    sim.output = bkg
    sim.run_simulation()


    elapsed_t = time()-start_t
    print(f"Trial {count} took {elapsed_t} seconds.")
    print('.. done')

    return (count, elapsed_t)


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Simulate empty fields.')
    parser.add_argument('-f', '--cfgfile', type=str, required=True, help="Path to the yaml configuration file")
    parser.add_argument('-mp', '--mp-enabled', type=str, default='false', help='To parallelize trials loop')
    parser.add_argument('-mpt', '--mp-threads', type=int, default=4, help='The size of the threads pool') 
    args = parser.parse_args()

    main(args)