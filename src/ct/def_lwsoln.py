
import os
import pickle
from functools import cache

import cantera as ct

class lwspecies(object):
    def __init__(self, composition):
        self.composition = composition

class lwreaction(object):
    def __init__(self, heavy_reaction):
        self.products = heavy_reaction.products 
        self.reactants = heavy_reaction.reactants
        self.equation = heavy_reaction.equation

class lwsoln(object):
    def __init__(self, heavy_soln):
        self.n_elements = heavy_soln.n_elements
        self.element_names = heavy_soln.element_names

        self.species_names = heavy_soln.species_names
        self.species_dict = {}
        self.n_species = heavy_soln.n_species
        for i in range(heavy_soln.n_species):
            n = heavy_soln.species(i).name
            c = heavy_soln.species(i).composition
            self.species_dict[n] = lwspecies(c)

        self.reaction_equations_list = heavy_soln.reaction_equations()
        self.reaction_mw = [0]*heavy_soln.n_reactions
        self.reaction_dict = {}
        for i in range(heavy_soln.n_reactions):
            self.reaction_dict[i] = lwreaction(heavy_soln.reaction(i))
            for sp_name in heavy_soln.reaction(i).reactants:
                sp_mw = heavy_soln.species(sp_name).molecular_weight
                sp_amount = heavy_soln.reaction(i).reactants[sp_name]
                self.reaction_mw[i] += sp_amount*sp_mw

        self.n_reactions = heavy_soln.n_reactions

    def species(self, key):
        return self.species_dict[key]

    def reaction(self, key):
        return self.reaction_dict[key]

    def reaction_equations(self):
        return self.reaction_equations_list

#We wrap this function with cache
#so that we only cache successful
#loads.  
@cache
def get_lwsoln_inner(yaml_path):
    pfilename = yaml_path+'.p'
    lws = None
    try:
        with open(pfilename,'rb') as pfile:
            lws = pickle.load(pfile)
    except:
        try:
            soln = ct.Solution(yaml_path)
            lws = lwsoln(soln)
            with open(pfilename,'wb') as pfile:
                pickle.dump(lws, pfile)
            del soln
        except:
            raise
    return lws

#This function is not cached so if we
#write the yaml file later we don't
#get None return on every call
def get_lwsoln(yaml_path):
    try:
        return get_lwsoln_inner(yaml_path)
    except:
        return None


