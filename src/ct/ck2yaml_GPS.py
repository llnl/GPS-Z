
import os
import cantera.ck2yaml

def ck2yaml(folder):

    ok = True

    input_file = os.path.join(folder,'chem.inp')
    thermo_file = os.path.join(folder,'therm.dat')
    transport_file = None

    try:
        open(os.path.join(folder,'tran.dat'))
        transport_file  = os.path.join(folder,'tran.dat')
    except IOError:
        pass

    out_name = os.path.join(folder,"chem.yaml")

    cantera.ck2yaml.convert(input_file, thermo_file=thermo_file,
                            transport_file=transport_file,
                            out_name=out_name, permissive=True)

    return ok

