import os

import numpy as np
import cantera as ct

from src.ct.def_lwsoln import get_lwsoln

__author__ = 'Xiang Gao'

""" ------------------------------- """




def find_ns(dir_sk):
    path_save = os.path.join(dir_sk,'mech','ns.txt')
    try:
        f = open(path_save,'r')
        ns = int(f.read())
    except IOError:
        soln = get_lwsoln(os.path.join(dir_sk,'mech','chem.yaml'))
        ns = soln.n_species
        f = open(path_save,'w')
        f.write(str(ns))

    f.close()
    return ns



""" ------------------------------- """

def union_list(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    return list1 + list(set2 - set1)

def test_union_list():
    print(union_list([1,2,3],[3,4]))




def keys_sorted(dictionary, n_top=None):
    import heapq
    if n_top is None:
        n_top = len(dictionary.keys())
    else:
        n_top = int(n_top)
    return heapq.nlargest(n_top, dictionary, key = lambda k:dictionary[k])


""" ---------------------------------- """

def add_bracket(s):
    if s[0] != '[':
        s = '['+s

    if s[-1] != ']':
        s = s+']'  

    return s  



def num2str(num, d):
    s = str(num)
    #if '.' in s:
    #   s = s[:s.index('.')+d+1]

    return s

    
def test_num2str():
    print(num2str(0.1234, 2))
    print(num2str(12.34, 0))
    print(num2str(1000,0))



""" ---------------------------------- """


def st2name(i_pnt, e, source, target):
    name_gps = 'point '+ str(i_pnt) + ', graph '+ e
    if source is not None:
        name_gps += ', '+source + ' to '+target
    return name_gps




def para2dir_GPS(dir_public, train_name, \
    alpha=None, K=None, beta=None, \
    es_name=None, iso_name=None, \
    d=4, gamma=None):

    extra_setting = 'e[' + es_name + ']'
    if iso_name != None:
        extra_setting += (', iso[' + iso_name + ']'+'g'+str(gamma))

    para_str = 'K' + str(int(K))  +  '_b' + num2str(beta,d) + '_a' + num2str(alpha,d)
    return os.path.join(dir_public, 'GPS', train_name, para_str, extra_setting)


def get_GPS_mechs(parent, with_duplicates=False):
    dir_public = parent.project['dir_public']
    train_name = parent.train_name
    GPS_mechs = {}

    list_GPS = []
    for GPS_name in parent.project['GPS'].keys():
        if parent.project['GPS'][GPS_name]['checked']:
            list_GPS.append(GPS_name)

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

        if(len(K_list)>1 or len(beta_list)>1 or len(gamma_list)>1):
            #Over-ride to avoid eliminating different mechs with the
            #same number of species
            with_duplicates=True

        ns_last=-1
        for K in K_list:
            for beta in beta_list:
                for alpha in alpha_list:
                    for gamma in gamma_list:
                        dir_sk = para2dir_GPS(dir_public, train_name, \
                            alpha=alpha, K=K, beta=beta, \
                            es_name=es_name, iso_name=iso_name, \
                            d=parent.n_digit, gamma=gamma)

                        dir_mech_sk = os.path.join(dir_sk,'mech')
                        path_yaml_sk = os.path.join(dir_mech_sk,'chem.yaml')

                        if os.path.exists(path_yaml_sk):
                            mech_name = f'{GPS_name}_K{K}_b{beta}_a{alpha}'
                            #simplify names for default settings
                            mech_name = mech_name.replace("_K1.0_b0.5_","_")
                            ns = find_ns(dir_sk)
                            if(with_duplicates or ns != ns_last):
                                GPS_mechs[mech_name] = {'dir': dir_sk, 'base_name':
                                                        GPS_name, 'ns': ns }
                            ns_last = ns
    return GPS_mechs

def get_tune_mechs(parent):
    tune_mechs = {}
    list_tune = []
    for tune_name in parent.project['tune'].keys():
        if parent.project['tune'][tune_name]['checked']:
            list_tune.append(tune_name)

    if bool(list_tune) == False:
        return tune_mechs

    for tune_name in list_tune:
        tune = parent.project['tune'][tune_name]
        mech_name_orig = tune['mech_name']
        mech_name_tune = mech_name_orig + '_tuned'
        databases = tune['databases']
        reactions = tune['reactions']
        if mech_name_orig in parent.project['mech']:
            dir_mech = parent.project['mech'][mech_name_orig]['desk']
            base_name = mech_name_tune
        else:
            assert(mech_name_orig[0:3] == "GPS")
            gps_mechs = get_GPS_mechs(parent)
            dir_mech = gps_mechs[mech_name_orig]['dir']
            base_name = gps_mechs[mech_name_orig]['base_name']+'_tuned'

        tune_dir = os.path.join(dir_mech,'tuning',tune_name)
        path_yaml = os.path.join(tune_dir,'mech','chem.yaml')
        if os.path.exists(path_yaml):
            ns = find_ns(tune_dir)
            tune_mechs[mech_name_tune] = {'dir': tune_dir,
                                          'base_name': base_name,
                                          'ns': ns}

    return tune_mechs


def para2dir_PFA(dir_public, train_name, crit, d=4):
    return os.path.join(dir_public, 'PFA', train_name, num2str(crit,d))



def cond2dir(dir_desk, fuel, oxid, phi, atm, T0, reactor, d):

    comp = add_bracket(fuel) + ' + ' + add_bracket(oxid)
    phi_str = 'phi' + str(phi)#num2str(phi, d=3)
    atm_str = str(atm)+'atm'#num2str(atm, d) + 'atm'
    T0_str = str(T0)+'K'#num2str(T0, d) + 'K'
    return os.path.join(dir_desk,'raw', comp, reactor, phi_str+'_'+atm_str+'_'+T0_str)




def test_cond2dir():
    parent = 'data/CH4/detailed'
    fuel_dict = {'CH4':0.1}
    phi = 1.0
    atm = 1
    T0 = 1000
    print(cond2dir(parent, fuel_dict, phi, atm, T0))

""" ---------------------------------- """


def avg_mole_per_sec(raw, start_point=0, end_point='eq', constV=False):

    #print(type(end_point))

    T = raw['temperature']
    x = raw['axis0']
    rr = raw['net_reaction_rate']
    V = raw['volume']
    n_rxn = rr.shape[1] - 1

    i_start = start_point
    if type(end_point) is int:
        i_end = end_point
        if i_end == i_start:
            mole_per_sec = rr[i_start, :] * float(V[i_start])
            return np.transpose(mole_per_sec)
    else:
        if end_point == 'ign':
            T_end = T[0] + 400
        elif end_point == 'eq':
            T_end = T[-1] - 50
        i_end = np.argmin(abs(T - T_end))

    avg_rr = np.ndarray([n_rxn+1,1])
    for id_rxn in range(1, n_rxn + 1):
        if constV:
            mole_per_sec = rr[i_start:i_end,id_rxn] * V[0]
        else:
            mole_per_sec = np.multiply(rr[i_start:i_end, id_rxn], V[i_start:i_end])
        int_rr = np.trapz(np.transpose(mole_per_sec), np.transpose(x[i_start:i_end]))
        avg_rr[id_rxn] = float(int_rr) / (x[i_end] - x[i_start])

    return avg_rr

