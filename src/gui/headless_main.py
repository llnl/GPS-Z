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
    def init_es_default(self):
        alias_fuel = '!fuel!'
        self.alias_fuel = alias_fuel
        es_traced = ['C','c','H','h','O','o']
        es_e = dict()
        es_e['C'] = {'only_hub':False, 'source':[alias_fuel],'target':['CO2']}
        es_e['H'] = {'only_hub':False, 'source':[alias_fuel],'target':['H2O']}
        es_e['c'] = {'only_hub':False, 'source':[alias_fuel],'target':['co2']}
        es_e['h'] = {'only_hub':False, 'source':[alias_fuel],'target':['h2o']}
        es_e['!other!'] = {'only_hub':True, 'source':[],'target':[]}    

        if bool(self.project['es']) == False:
            dir_public = self.project['dir_public']
            dir_desk = os.path.join(dir_public,'detailed')
            path_yaml = os.path.join(dir_desk,'mech','chem.yaml')
            soln = ct.Solution(path_yaml)

            element = dict()
            for e in soln.element_names:
                if e in es_e.keys():
                    element[e] = copy.copy(es_e[e])
                else:
                    element[e] = copy.copy(es_e['!other!'])

                if e in es_traced:
                    element[e]['traced'] = True
                else:
                    element[e]['traced'] = False

                element[e]['cust'] = False
                element[e]['name'] = e

            es = dict()
            es['name'] = 'default'
            es['element'] = element
            self.project['es']['default'] = es

    def __init__(self):
        # self.variables ============================
        self.dir_parent = os.getcwd()

        self.chr_not_allowed = [chr(92), '/', ':','*','?','"','<','>','|','+']
        self.ign_list = [
            'autoignition',
            'autoignition fine',
            'autoignition full',
            ]
        self.psr_list = [
            'PSR extinction',
            ]
        self.other_list = [
            'Premix',
            'DNS'
            ]
        self.reactor_list = self.ign_list + self.psr_list + self.other_list

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

        self.init_es_default()

        train_name = ''
        for db_name in sorted(self.project['database'].keys()):
            if self.project['database'][db_name]['train']:
                train_name += (add_bracket(db_name)+' + ')
        self.train_name = train_name[:-3]

        run_train(self)
        run_GPS(self)
        #TODO:
        #run_test(self, None)

if __name__ == '__main__':
    set_start_method(os.getenv('GPS_MP_START_METHOD'))

    headless_main()
