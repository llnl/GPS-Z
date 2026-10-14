# -*- coding: UTF-8 -*-

import os

os.environ['OMP_NUM_THREADS'] = "1"
os.environ['OPENBLAS_NUM_THREADS'] = "1"

import sys
import json
import time
import cantera as ct
import copy
from .def_run import *
from src.ct.def_lwsoln import get_lwsoln
from multiprocessing import set_start_method

class headless_main(object):
    def __init__(self):
        set_start_method(os.getenv('GPS_MP_START_METHOD'))

        # self.variables ============================
        self.n_digit = 4
        self.min_dT = 10

        # set and exec =============================
        path_json = sys.argv[1]
        if not os.path.exists(path_json):
            raise ValueError(f"Project json file doesn't exist: {path_json}")
        self.project = json.load(open(path_json,'r'))
        dir_public = self.project['dir_public']

        # detailed chem.yaml ----------
        dir_desk = os.path.join(dir_public,'detailed')
        path_yaml = os.path.join(dir_desk,'mech','chem.yaml')
        #TODO: Make yaml instead of raising error
        if not os.path.exists(path_yaml):
            raise ValueError(f"Yaml file doesn't exist ({path_yaml}), please configure run with gui")

        #This will generate the pfile (if it doesn't exist) and cache the lwsoln
        lwsoln = get_lwsoln(path_yaml)

        if not bool(self.project['mech']['detailed']['chem']):
            self.project['mech']['detailed']['chem'] = os.path.join(dir_desk,'mech','chem.inp')
            self.project['mech']['detailed']['therm'] = os.path.join(dir_desk,'mech','therm.dat')
        
        self.project['mech']['detailed']['desk'] = dir_desk

        train_name = ''
        for db_name in sorted(self.project['database'].keys()):
            if self.project['database'][db_name]['train']:
                train_name += (add_bracket(db_name)+' + ')
        self.train_name = train_name[:-3]
        self.alias_fuel = '!fuel!'
        assert(bool(self.project['es']))

        self.progress_stream = sys.stderr

        run_train(self)
        run_GPS(self)
        run_sens(self)
        run_tune(self)
        #TODO:
        #run_test(self, None)

if __name__ == '__main__':
    headless_main()

