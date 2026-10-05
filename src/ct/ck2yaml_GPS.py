
import os
import cantera.ck2yaml

def ck2yaml(folder):

    ok = True

    input_file = os.path.join(folder,'chem.inp')
    thermo_file = os.path.join(folder,'therm.dat')
    # N.B. we don't convert the transport file because it 
    # takes an extremely long time for cantera to parse into
    # soln for large mechanisms
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

