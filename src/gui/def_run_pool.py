
import sys
import os
import json
import time
import cantera as ct
import shutil
import copy
from collections import defaultdict
from multiprocessing import Pool
from tqdm import tqdm

from src.core.def_tools import *
from src.ct.def_ct_tools import Xstr
from src.zk.zerork import zerork, zerork_S_curve, zerork_premix, zerork_sensitivity
from src.ct.senkin import senkin
from src.ct.psr import S_curve
from src.ck.def_cheminp import skeletal
from src.ct.ck2yaml_GPS import ck2yaml

from src.ct.def_ct_tools import load_raw
from src.ct.def_lwsoln import get_lwsoln
from src.core.def_GPS import GPS_algo
from src.core.def_build_graph import build_flux_graph


""" >>>>>>>>>>>>>------------------------------------------------
0.3. run
     called by: window_main, headless_main
"""

def PoolWrapper(*args, **kwargs):
    p = None
    try:
        p = int(os.environ['GPS_NUM_PROCS'])
    except:
        p = None
    if p:
        if(p>1):
            return Pool(p, *args, **kwargs)
        else:
            class serial_pool(object):
                def __init__(self):
                    self.imap = map
                    self.imap_unordered = map
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    return
            return serial_pool()
    else:
        return Pool(*args, **kwargs)

class dialog_progress(object):

    def set_value(self, task, value):
        tasks = ['train','GPS','test']
        bars = [self.w.bar_train, self.w.bar_GPS, self.w.bar_test]
        bar = bars[tasks.index(task)]
        bar.setValue(int(value))
        self.parent.app.processEvents()

    def set_info(self, new_info):
        from PyQt5.QtGui import QTextCursor
        str_time = '[' + time.strftime("%H:%M:%S") + '] '
        new_info = str_time + new_info.replace(self.dir_public,'').strip('/') + '\n'
        #self.f.write(str(new_info))

        old_info = self.w.txt_info.toPlainText()
        self.w.txt_info.setText(old_info + new_info)
        self.w.txt_info.moveCursor(QTextCursor.End)
        self.parent.app.processEvents()

    def act_verbose(self):
        if self.verbose:
            self.w.btn_verbose.setText('verbose')
            self.verbose = False
        else:
            self.w.btn_verbose.setText('concise')
            self.verbose = True


    def act_stop(self):
        from PyQt5.QtWidgets import QMessageBox, QWidget
        self.stop = True
        msg = 'will stop after finishing current sub-task'
        QMessageBox.information(QWidget(),'',msg)

    def close(self):
        self.w.accept()

    def __init__(self, parent):
        from PyQt5 import uic
        ui_name = 'progress.ui'
        self.parent = parent
        self.stop = False
        self.verbose = False
        self.dir_public = self.parent.project['dir_public']
        self.f = open(os.path.join(self.dir_public,'log.txt'),'w')

        self.w = uic.loadUi(os.path.join(parent.dir_ui, ui_name))
        self.w.btn_stop.clicked.connect(self.act_stop)
        self.w.btn_verbose.clicked.connect(self.act_verbose)

        tasks = ['train','GPS','test']
        for task in tasks:
            self.set_value(task,0)

        self.parent.app.processEvents()
        self.w.show()


class dialog_progress_headless(object):
    def set_value(self, task, value):
        pass
    def set_info(self, new_info):
        pass
    def act_verbose(self):
        pass
    def act_stop(self):
        pass
    def close(self):
        pass
    class _w(object):
        class label(object):
            def __init__(self):
                pass
            def setText(*args,**kwargs):
                pass
        def __init__(self):
            self.label_test = self.label()
            self.label_GPS = self.label()
    def __init__(self, parent):
        self.parent = parent
        self.stop = False
        self.verbose = False
        self.w = self._w()


def write_sk_inp(species_kept, dir_mech_de, dir_mech_sk, notes):

    species_kept = list(species_kept)
    n_sp = len(species_kept)
    print('total: '+str(n_sp))

    notes.append('! number of species = '+str(n_sp))
    skeletal(dir_mech_de, dir_mech_sk, species_kept, notes=notes)
    ck2yaml(dir_mech_sk)

    f = open(os.path.join(dir_mech_sk,'ns.txt'),'w')
    f.write(str(n_sp))
    f.close()


CANTERA = bool(os.getenv("GPS_CANTERA", False))
def find_raw(dir_desk, fuel, oxid, phi, atm, T0, reactor, n_digit):
    
    dir_raw = cond2dir(dir_desk, fuel['name'], oxid['name'], phi, atm, T0, reactor, n_digit)

    if not os.path.exists(dir_raw):
        os.makedirs(dir_raw)

    path_yaml = os.path.join(dir_desk,"mech","chem.yaml")
    if CANTERA:
        soln = ct.Solution(path_yaml)
        soln_in = ct.Solution(path_yaml)

        X0 = Xstr(soln, fuel['composition'], phi, oxid['composition'])    
        if reactor == 'autoignition':
            senkin(soln, atm, T0, X0, if_half=True, dir_raw=dir_raw, if_fine=False)
        elif reactor == 'autoignition fine':
            senkin(soln, atm, T0, X0, if_half=True, dir_raw=dir_raw, if_fine=True)
        elif reactor == 'autoignition full':
            senkin(soln, atm, T0, X0, if_half=False, dir_raw=dir_raw, if_fine=False)
        elif reactor == 'PSR extinction':
            S_curve(soln_in, soln, atm, T0, X0, dir_raw=dir_raw)
        elif reactor == 'Premix':
            raise RuntimeError("Premix not supported when using Cantera")
            
    else:
        soln = get_lwsoln(path_yaml)
        if 'autoignition' in reactor:
            #TODO: Full (which runs to equilibrium)
            is_fine=False
            if 'fine' in reactor:
                is_fine = True
            if 'sensitivity' in reactor:
                zerork_sensitivity(dir_desk, atm, T0, fuel['composition'], oxid['composition'], phi,
                       soln.species_names, soln.reaction_equations(), dir_raw=dir_raw,
                       is_fine=is_fine)
            else:
                zerork(dir_desk, atm, T0, fuel['composition'], oxid['composition'], phi,
                       soln.species_names, soln.reaction_equations(), dir_raw=dir_raw,
                       is_fine=is_fine)
        elif reactor == 'PSR extinction':
            zerork_S_curve(dir_desk, atm, T0, fuel['composition'], oxid['composition'], phi,
                   soln.species_names, soln.reaction_equations(), dir_raw=dir_raw)
        elif reactor == 'Premix':
            zerork_premix(dir_desk, atm, T0, fuel['composition'], oxid['composition'], phi,
                   soln.species_names, soln.reaction_equations(), dir_raw=dir_raw)


""" ------------------------------------------------------
      dP                     oo          
      88                                 
    d8888P 88d888b. .d8888b. dP 88d888b. 
      88   88'  `88 88'  `88 88 88'  `88 
      88   88       88.  .88 88 88    88 
      dP   dP       `88888P8 dP dP    dP 
"""


def run_train(parent, progress=None):
    dir_de = os.path.join(parent.project['dir_public'],'detailed')

    list_train = []
    for db_name in parent.project['database'].keys():
        if parent.project['database'][db_name]['train']:
            list_train.append(db_name)

    list_train = sorted(list_train)

    v = 0
    raw_single_mech(list_train, parent, 100, v, dir_de)
    return True



""" >>>>>>>>>>>>>------------------------------------------------
"""

def do_run(inputs):
    fuel_name, fuel, oxid_name, oxid, phi, atm, T0, dir_desk, reactor, n_digit, check_only = inputs

    dir_raw = cond2dir(dir_desk, fuel_name, oxid_name, phi, atm, T0, \
        reactor, n_digit)
    path_raw = os.path.join(dir_raw,'raw.npz')

    if not os.path.exists(path_raw) and not check_only:
        find_raw(dir_desk, fuel, oxid, phi, atm, T0, reactor, n_digit)

    return path_raw


def raw_single_mech(list_db, parent, dv_mech, v, dir_desk, bar='train',
                    reactor_modifier = "", check_only=False):

    for db_name in list_db:

        database = parent.project['database'][db_name]
        phi_list = database['phi']
        T0_list = database['T0']
        atm_list = database['atm']
        fuel_list = database['fuel']
        oxid_list = database['oxid']
        reactor = database['reactor'] + reactor_modifier

        inputs_array = []
        for fuel_name in fuel_list:
            fuel = parent.project['fuel'][fuel_name]
            for oxid_name in oxid_list:
                oxid = parent.project['oxid'][oxid_name]
                for phi in phi_list:
                    for atm in atm_list:
                        for T0 in T0_list:
                            inputs_array.append([fuel_name, fuel, oxid_name,
                            oxid, phi, atm, T0, dir_desk, reactor,
                            parent.n_digit, check_only])

        with PoolWrapper() as p:
            raws = list(tqdm(p.imap_unordered(do_run, inputs_array), total=len(inputs_array), desc=f"{db_name}({reactor})"))

    return raws


""" ------------------------------------------------------
     .88888.   888888ba  .d88888b  
    d8'   `88  88    `8b 88.    "' 
    88        a88aaaa8P' `Y88888b. 
    88   YP88  88              `8b 
    Y8.   .88  88        d8'   .8P 
     `88888'   dP         Y88888P  
                                   
"""

def do_GPS_run(inputs):
    dir_raw, elem, i_pnt, \
        source, target, K_list, alpha_list, beta_list, iso, \
        gamma_list, fuel_name, oxid_name, dir_de = inputs

    path_yaml = os.path.join(dir_de,"mech","chem.yaml")
    soln = get_lwsoln(path_yaml)

    raw = load_raw(os.path.join(dir_raw,'raw.npz'))
    T = raw['temperature']
    axis0 = raw['axis0']

    flux_graph = build_flux_graph(soln, raw, elem,  path_save=None, overwrite=False,
                                  i0=i_pnt, i1=i_pnt, constV=False)

    collected_results = []
    for K in K_list:
        for beta in beta_list:
            for alpha in alpha_list:
                for gamma in gamma_list:
                    GPS_notes = 'T = '+str(T[i_pnt])+', axis0 = '+str(axis0[i_pnt])+\
                            ' ('+str(min(axis0))+' ~ '+str(max(axis0))+')'

                    GPS_results = GPS_algo(soln, flux_graph, source, target, \
                        path_save=None, K=K, alpha=alpha, beta=beta, \
                        normal='max', iso=iso, overwrite=True, raw=dir_raw, \
                        notes=GPS_notes, gamma=gamma)
                    species_kept = set(GPS_results['species'].keys())
                    collected_results.append(species_kept)

    return collected_results


def run_GPS(parent, progress=None):
    min_dT = parent.min_dT

    dir_public = parent.project['dir_public']
    dir_de = os.path.join(dir_public,'detailed')
    def get_soln_species(dir_de):
        path_yaml = os.path.join(dir_de,"mech","chem.yaml")
        soln = get_lwsoln(path_yaml) 
        return soln.species
    soln_species = get_soln_species(dir_de)

    list_train = []
    train_name = parent.train_name
    for db_name in parent.project['database'].keys():
        if parent.project['database'][db_name]['train']:
            list_train.append(db_name)

    list_GPS = []
    for GPS_name in parent.project['GPS'].keys():
        if parent.project['GPS'][GPS_name]['checked']:
            list_GPS.append(GPS_name)

    if bool(list_GPS) == False:
        return False

    # for different GPS settings ============================

    for GPS_name in list_GPS:

        GPS = parent.project['GPS'][GPS_name]
        alpha_list = GPS['alpha']
        beta_list = GPS['beta']
        K_list = GPS['K']
        must_keep = GPS['must_keep']

        es_name = GPS['es']
        es = parent.project['es'][es_name]
        traced_list = []
        for e in es['element'].keys():
            if es['element'][e]['traced']:
                traced_list.append(e)

        if GPS['iso_enable']:
            iso_name = GPS['iso']
            iso = parent.project['iso'][iso_name]
            gamma_list = GPS['gamma']
        else:
            iso_name = None
            iso = None
            gamma_list = [None]

        inputs_array = []

        for db_name in list_train:

            database = parent.project['database'][db_name]
            phi_list = database['phi']
            T0_list = database['T0']
            atm_list = database['atm']
            fuel_list = database['fuel']
            oxid_list = database['oxid']
            reactor = database['reactor']

            for fuel_name in fuel_list:
                for oxid_name in oxid_list:
                    for phi in phi_list:
                        for atm in atm_list:
                            for T0 in T0_list:

                                fuel = parent.project['fuel'][fuel_name]
                                oxid = parent.project['oxid'][oxid_name]

                                e_available = set()
                                for sp in fuel['composition'].keys():
                                    e_available |= set(soln_species(sp).composition.keys())
                                for sp in oxid['composition'].keys():
                                    e_available |= set(soln_species(sp).composition.keys())

                                dir_raw = cond2dir(dir_de, fuel_name, \
                                    oxid_name, phi, atm, T0, \
                                    reactor, parent.n_digit)
                                if 'DNS' in reactor:
                                    dir_raw = os.path.join(dir_raw, database['case'][0])

                                dir_graph = os.path.join(dir_raw,'graph')

                                raw_name = cond2dir('', fuel_name, \
                                    oxid_name, phi, atm, T0, \
                                    reactor, parent.n_digit)

                                if 'DNS' in reactor:
                                    raw_name += '/' + database['case'][0]

                                raw = load_raw(os.path.join(dir_raw,'raw.npz'))
                                T = raw['temperature']
                                axis0 = raw['axis0']
                                n_pnt = len(raw['axis0'])

                                #print('dir_raw = '+str(dir_raw))
                                #print('n_point = '+str(n_pnt))

                                # for different time instance ================

                                flag = False
                                # -----------------------------------------------
                                # I only consider the points where T and T0 has
                                # some difference, which means there're reactions
                                # performing GPS on chemically frozen state, or
                                # equilibirum state (for PSR), does not give too
                                # much useful information
                                #
                                # once a point is sampled, flag = True
                                # -----------------------------------------------

                                for i_pnt in range(len(T)):

                                    if flag == False:
                                        if abs(T[i_pnt]-T[0])>min_dT:
                                            flag = True
                                        else:
                                            continue

                                    for e in traced_list:
                                        if e not in e_available:
                                            continue

                                        sources = copy.copy(es['element'][e]['source'])

                                        if bool(sources) == False:
                                            sources = [None]
                                        if parent.alias_fuel in sources:
                                            del sources[sources.index(parent.alias_fuel)]

                                            for sp in fuel['composition'].keys():
                                                atoms = soln_species(sp).composition.keys()
                                                if e in atoms:
                                                    sources += [sp]

                                        targets = es['element'][e]['target']
                                        if bool(targets) == False:
                                            targets = [None]

                                        for target in targets:
                                            for source in sources:
                                                inputs_array.append([dir_raw, e, i_pnt,
                                                    source, target, K_list, alpha_list,
                                                    beta_list, iso, gamma_list,
                                                    fuel_name, oxid_name, dir_de])

        with PoolWrapper() as p:
            results = list(tqdm(p.imap(do_GPS_run, inputs_array),total=len(inputs_array), desc="GPS"))

        species_sets = defaultdict(set)
        for i, o in zip(inputs_array, results):
            dir_raw, elem, i_pnt, \
                source, target, K_list, alpha_list, beta_list, iso, \
                gamma_list, fuel_name, oxid_name, dir_de = i

            omat = np.array(o).reshape( (len(K_list), len(beta_list),
                                          len(alpha_list), len(gamma_list) ) )
            for ik, K in enumerate(K_list):
                for ib, beta in enumerate(beta_list):
                    for ia, alpha in enumerate(alpha_list):
                        for ig, gamma in enumerate(gamma_list):
                            dir_sk = para2dir_GPS(dir_public, train_name, \
                                alpha=alpha, K=K, beta=beta, \
                                es_name=es_name, iso_name=iso_name, \
                                d=parent.n_digit, gamma=gamma)

                            species_kept = set(must_keep)

                            fuel = parent.project['fuel'][fuel_name]
                            oxid = parent.project['oxid'][oxid_name]
                            species_kept |= set(fuel['composition'].keys())
                            species_kept |= set(oxid['composition'].keys())

                            new_kept = omat[ik,ib,ia,ig]
                            species_kept |= new_kept
                            species_sets[dir_sk]  |= species_kept


        for K in K_list:
            for beta in beta_list:
                for alpha in alpha_list:
                    for gamma in gamma_list:
                        dir_sk = para2dir_GPS(dir_public, train_name, \
                            alpha=alpha, K=K, beta=beta, \
                            es_name=es_name, iso_name=iso_name, \
                            d=parent.n_digit, gamma=gamma)
                        dir_mech_de = os.path.join(dir_de,'mech')
                        dir_mech_sk = os.path.join(dir_sk,'mech')

                        species_kept = species_sets[dir_sk]

                        notes = ['! generated by global pathway selection, Gao et al,'+ \
                                  ' Combustion and flame, 167 (2016) 238-247']
                        notes.append('! alpha = ' + str(alpha) + ', K = ' + str(K) + \
                                     ', beta = ' + str(beta))
                        notes.append('! training database: '+train_name)

                        # generate chem.inp ***************
                        write_sk_inp(species_kept, dir_mech_de, dir_mech_sk, notes)

    return True


def run_sens(parent, progress=None, check_only=False):

    sens_out = {}
    for sens_name in parent.project['sens'].keys():
        sens = parent.project['sens'][sens_name]
        if sens['checked']:
            mech_name = sens['mech_name']
            if mech_name in parent.project['mech']:
                dir_desk = parent.project['mech'][mech_name]['desk']
            else:
                assert(mech_name[0:3] == "GPS")
                gps_mechs = get_GPS_mechs(parent.project)
                dir_desk = gps_mechs[mech_name]
            list_dbs = parent.project['sens'][sens_name]['databases']
            v = 0
            raws = raw_single_mech(list_dbs, parent, 100, v, dir_desk,
                            reactor_modifier='+sensitivity',
                            check_only=check_only)
            sens_out[sens_name] = {'mech_name': mech_name}
            sens_out[sens_name]['srels'] = None
            #Note: Each sensitivity job will be sorted based on srel, but we need to merge them.
            #Here we will store maximum sensitivity over all conditions to sort later
            for path_raw in raws:
                sens_data = np.load(path_raw)
                idxs, srels, eqs = sens_data['indexes'], sens_data['srel'], sens_data['equations']
                if(not sens_out[sens_name]['srels']):
                    sens_out[sens_name]['srels'] = np.zeros_like(srels)
                    sens_out[sens_name]['eqs'] = ['']*len(eqs)
                for idx, srel, eq in zip(idxs, srels, eqs):
                    sens_out[sens_name]['srels'][idx-1] = max(srel,sens_out[sens_name]['srels'][idx-1])
                    sens_out[sens_name]['eqs'][idx-1] = eq

    return sens_out


""" ------------------------------------------------------
          dP                       dP   
          88                       88   
        d8888P .d8888b. .d8888b. d8888P 
          88   88ooood8 Y8ooooo.   88   
          88   88.  ...       88   88   
          dP   `88888P' `88888P'   dP   
"""


def run_test(parent, progress=None):

    dir_public = parent.project['dir_public']

    list_test = []
    for db_name in parent.project['database'].keys():
        if parent.project['database'][db_name]['test']:
            list_test.append(db_name)

    #  ============================
    #          dP            dP            oo dP                dP 
    #          88            88               88                88 
    #    .d888b88 .d8888b. d8888P .d8888b. dP 88 .d8888b. .d888b88 
    #    88'  `88 88ooood8   88   88'  `88 88 88 88ooood8 88'  `88 
    #    88.  .88 88.  ...   88   88.  .88 88 88 88.  ... 88.  .88 
    #    `88888P8 `88888P'   dP   `88888P8 dP dP `88888P' `88888P8 
                                                          
    dir_de = os.path.join(dir_public,'detailed')

    v = 0
    raw_single_mech(list_test, parent, 100, v, dir_de, 'test')

    #  ============================
    #     .88888.   888888ba  .d88888b  
    #    d8'   `88  88    `8b 88.    "' 
    #    88        a88aaaa8P' `Y88888b. 
    #    88   YP88  88              `8b 
    #    Y8.   .88  88        d8'   .8P 
    #     `88888'   dP         Y88888P  
                                       
    list_GPS = []
    for GPS_name in parent.project['GPS'].keys():
        if parent.project['GPS'][GPS_name]['checked']:
            list_GPS.append(GPS_name)

    v = 0

    if bool(list_GPS):

        dv_GPS = 100.0/len(list_GPS)

        for GPS_name in list_GPS:

            GPS = parent.project['GPS'][GPS_name]
            alpha_list = GPS['alpha']
            beta_list = GPS['beta']
            K_list = GPS['K']
            es_name = GPS['es']
            if GPS['iso_enable']:
                iso_name = GPS['iso']
                gamma_list = GPS['gamma']
            else:
                iso_name = None
                gamma_list = [None]


            dv_kab = 1.0 * dv_GPS/ (len(K_list) * len(beta_list) * len(alpha_list) * len(gamma_list))

            for K in K_list:
                for beta in beta_list:
                    for alpha in alpha_list:
                        for gamma in gamma_list:

                            dir_sk = para2dir_GPS(dir_public, train_name, \
                                    alpha=alpha, K=K, beta=beta, \
                                    es_name=es_name, iso_name=iso_name, \
                                    d=parent.n_digit, gamma=gamma)

                            path_yaml = os.path.join(dir_sk,'mech','chem.yaml')

                            v = raw_single_mech(list_test, parent, dv_kab, v, dir_sk, 'train')

    #  ============================
    #               dP   dP                         
    #               88   88                         
    #    .d8888b. d8888P 88d888b. .d8888b. 88d888b. 
    #    88'  `88   88   88'  `88 88ooood8 88'  `88 
    #    88.  .88   88   88    88 88.  ... 88       
    #    `88888P'   dP   dP    dP `88888P' dP       

    for name in parent.project['mech'].keys():
        sk = parent.project['mech'][name]
        if name != 'detailed' and sk['checked']:
            dir_sk = sk['desk']
            path_yaml = os.path.join(dir_sk,'mech','chem.yaml')
            if name not in parent.soln.keys():
                parent.soln[name] = ct.Solution(path_yaml)
                parent.soln_in[name] = ct.Solution(path_yaml)

            v = 0
            raw_single_mech(list_test, parent, 100, v, dir_sk, 'test')


""" --------------------------------------
          dP                            
          88                            
        d8888P 88    88 88d888b. .d8888b. 
          88   88    88 88'  `88 88ooood8   
          88   88.  .88 88    88 88.  ...   
          dP   `88888P8 dP    dP `88888P'   
    """
                                         
def tune_single_mech(list_db, parent, dv_mech, v, dir_desk, bar='train'):

    for db_name in list_db:

        database = parent.project['database'][db_name]
        phi_list = database['phi']
        T0_list = database['T0']
        atm_list = database['atm']
        fuel_list = database['fuel']
        oxid_list = database['oxid']
        reactor = database['reactor']

        inputs_array = []
        for fuel_name in fuel_list:
            fuel = parent.project['fuel'][fuel_name]
            for oxid_name in oxid_list:
                oxid = parent.project['oxid'][oxid_name]
                for phi in phi_list:
                    for atm in atm_list:
                        for T0 in T0_list:
                            inputs_array.append([fuel_name, fuel, oxid_name,
                            oxid, phi, atm, T0, dir_desk, reactor,
                            parent.n_digit])

        with PoolWrapper() as p:
            _ = list(tqdm(p.imap_unordered(do_run, inputs_array), total=len(inputs_array), desc=f"{db_name}({reactor})"))

    return v


def run_tune(parent):

    list_tune = []
    for db_name in parent.project['database'].keys():
        if parent.project['database'][db_name]['tune']:
            list_tune.append(db_name)

    #  ============================
    #     .88888.   888888ba  .d88888b  
    #    d8'   `88  88    `8b 88.    "' 
    #    88        a88aaaa8P' `Y88888b. 
    #    88   YP88  88              `8b 
    #    Y8.   .88  88        d8'   .8P 
    #     `88888'   dP         Y88888P  
                                       
    list_GPS = []
    for GPS_name in parent.project['GPS'].keys():
        if parent.project['GPS'][GPS_name]['checked']:
            list_GPS.append(GPS_name)

    v = 0

    if bool(list_GPS):

        dv_GPS = 100.0/len(list_GPS)

        for GPS_name in list_GPS:

            GPS = parent.project['GPS'][GPS_name]
            alpha_list = GPS['alpha']
            beta_list = GPS['beta']
            K_list = GPS['K']
            es_name = GPS['es']
            if GPS['iso_enable']:
                iso_name = GPS['iso']
                gamma_list = GPS['gamma']
            else:
                iso_name = None
                gamma_list = [None]


            dv_kab = 1.0 * dv_GPS/ (len(K_list) * len(beta_list) * len(alpha_list) * len(gamma_list))

            for K in K_list:
                for beta in beta_list:
                    for alpha in alpha_list:
                        for gamma in gamma_list:

                            dir_sk = para2dir_GPS(dir_public, train_name, \
                                    alpha=alpha, K=K, beta=beta, \
                                    es_name=es_name, iso_name=iso_name, \
                                    d=parent.n_digit, gamma=gamma)

                            path_yaml = os.path.join(dir_sk,'mech','chem.yaml')

                            reactions = None

                            tune_single_mech(list_test, parent, dv_kab, v, dir_sk, reactions, 'train')








