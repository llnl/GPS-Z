
import os
import cantera.ck2yaml

def ck2yaml(folder):

    ok = True

    input_file = os.path.join(folder,'chem.inp')
    thermo_file = os.path.join(folder,'therm.dat')
    transport_file  = os.path.join(folder,'trans.dat')

    if(not os.path.exists(transport_file)):
        transport_file = None

    out_name = os.path.join(folder,"chem.yaml")

    try:
        cantera.ck2yaml.convert(input_file, thermo_file=thermo_file,
                                transport_file=transport_file,
                                out_name=out_name, permissive=True)
    except Exception as e:
        print("Converting to chemkin format to cantera yaml failed:")
        print(e)
        ok = False

    return ok

