
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
        self.element_names = heavy_soln.element_names

        self.species_names = heavy_soln.species_names
        self.species_dict = {}
        for i in range(heavy_soln.n_species):
            spec_dict = {}
            n = heavy_soln.species(i).name
            c = heavy_soln.species(i).composition
            self.species_dict[n] = lwspecies(c)

        self.reaction_equations_list = heavy_soln.reaction_equations()
        self.reaction_dict = {}
        for i in range(heavy_soln.n_reactions):
            self.reaction_dict[i] = lwreaction(heavy_soln.reaction(i))

        self.n_reactions = heavy_soln.n_reactions

    def species(self, key):
        return self.species_dict[key]

    def reaction(self, key):
        return self.reaction_dict[key]

    def reaction_equations(self):
        return self.reaction_equations_list

@cache
def get_lwsoln(yaml_path):
    pfilename = yaml_path+'.p'
    if(os.path.exists(pfilename)):
        with open(pfilename,'rb') as pfile:
            lws = pickle.load(pfile)
    else:
        soln = ct.Solution(yaml_path)
        lws = lwsoln(soln)
        with open(pfilename,'wb') as pfile:
            pickle.dump(lws, pfile)
        del soln
    return lws
