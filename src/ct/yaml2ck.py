
import os
import cantera as ct 
import cantera.yaml2ck as ctyaml2ck

def yaml2ck(folder, soln=None, overwrite=True):

    ok = True

    path_yaml = os.path.join(folder,'chem.yaml')
    if(not soln):
        soln = ct.Solution(path_yaml)

    mech_file = os.path.join(folder,'chem.inp')
    thermo_file = os.path.join(folder,'therm.dat')
    transport_file = None
    if(soln.transport_model != 'none'):
        tranport_file =  os.path.join(folder,'tran.dat')


    try:
        ctyaml2ck.convert(soln, mechanism_path=mech_file, thermo_path=thermo_file,
                           transport_path=transport_file, overwrite=overwrite)
    except Exception as e:
        print("Converting cantera solution to chemkin format failed:")
        print(e)
        ok = False

    return ok

