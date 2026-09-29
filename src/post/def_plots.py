
import os
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

from src.core.def_tools import cond2dir
from src.ct.def_ct_tools import load_raw

def auto_ign_plots(parent, db_name, test_mechs):
    database = parent.project['database'][db_name]
    phi_list = database['phi']
    T0_list = database['T0']
    atm_list = database['atm']
    fuel_list = database['fuel']
    oxid_list = database['oxid']
    reactor = database['reactor']

    plot_db = {}
    comp_keys = set()
    for mech_name in test_mechs:
        dir_desk=test_mechs[mech_name]['dir']
        plot_db[mech_name] = { }
        for fuel_name in fuel_list:
            fuel = parent.project['fuel'][fuel_name]
            for oxid_name in oxid_list:
                oxid = parent.project['oxid'][oxid_name]
                comp_key = fuel_name+oxid_name
                comp_keys.add(comp_key)
                plot_db[mech_name][comp_key] = {'ign_db': [],
                                               'temps': []}
                                                                   
                for phi in phi_list:
                    for atm in atm_list:
                        for T0 in T0_list:
                            dir_raw = cond2dir(dir_desk, fuel_name, oxid_name, phi, atm, T0, reactor, parent.n_digit)
                            raw = load_raw(os.path.join(dir_raw,'raw.npz'))
                            time = raw['axis0']
                            T = raw['temperature']
                            ign_temp = T[0]+400
                            ign_time = time[np.argwhere( 
                                np.isclose(0, (T - ign_temp),atol=1.0e-4)
                                )].item()
                            plot_db[mech_name][comp_key]['ign_db'].append([T0,
                                                                          phi,
                                                                          atm,
                                                                          ign_time])
                            plot_db[mech_name][comp_key]['temps'].append(T)
                ign_db = np.array(plot_db[mech_name][comp_key]['ign_db'])
                plot_db[mech_name][comp_key]['ign_db'] = ign_db

    for phi in phi_list:
        for atm in atm_list:
            for comp in comp_keys:
                fig, axis = plt.subplots(1,1, layout='constrained')
                for mech_name in test_mechs:
                    ign_db = plot_db[mech_name][comp_key]['ign_db']
                    data = ign_db[np.isclose(ign_db[:,1],phi) &
                                  np.isclose(ign_db[:,2],atm),:]
                    ns = test_mechs[mech_name]['ns']
                    ls = test_mechs[mech_name].get('ls', '-')
                    axis.semilogy(1000.0/data[:,0], data[:,3], label=f"{mech_name} ({ns} sp)", ls=ls)
                axis.legend()
                axis.set_title(f"comp={comp}, phi={phi}, p={atm} atm")
                axis.set_xlabel('1000 / T [K^-1]')
                axis.set_ylabel('Ignition Delay [s]')
                plot_filename = os.path.join(parent.project['dir_public'],'plots',f'idt_{comp}_{phi}_{atm}.png')
                plt.savefig(plot_filename)
                parent.plotfilenames.append(plot_filename)
                plt.close(fig)


    #Error Matrix Plots
    plt.rcParams.update({'font.size': 16}) 
    comparison_mechs = [ m for m in test_mechs if m != "detailed" ]
    cmap = 'PiYG'
    cb_lim = 1.0
    n_rows = len(comparison_mechs)
    n_cols = len(atm_list)
    relative_error_sum  = {mech_name: 0 for mech_name in comparison_mechs}
    num_idts_total = 0
    for comp in comp_keys:
        contours = []
        fig, axes = plt.subplots(n_rows,n_cols,sharex='col',sharey='row',
                                 figsize=(6*n_cols,3*n_rows), layout='constrained')
        for j, atm in enumerate(atm_list):
            ign_db = plot_db['detailed'][comp]['ign_db']
            num_idts_total += len(ign_db[:,3])
            detailed_data = ign_db[np.isclose(ign_db[:,2],atm),:]
            T_mat = detailed_data[:,0].reshape(len(phi_list),len(T0_list))
            phi_mat = detailed_data[:,1].reshape(len(phi_list),len(T0_list))
            idt_mat = detailed_data[:,3].reshape(len(phi_list),len(T0_list))
            for i,mech_name in enumerate(comparison_mechs):
                comp_db = plot_db[mech_name][comp]['ign_db']
                comp_data = comp_db[np.isclose(comp_db[:,2],atm),:]
                comp_idt_mat = comp_data[:,3].reshape(len(phi_list),len(T0_list))
                idt_err = (idt_mat - comp_idt_mat)/(idt_mat)
                relative_error_sum[mech_name] += np.sum(np.abs(idt_err))
                ax = axes[i,j]
                ax.set_title(f"{mech_name}: {atm} atm")
                c = ax.contourf(T_mat, phi_mat, idt_err, cmap=cmap)
                contours.append(c)
        axes[-1,0].set_ylabel('Equivalence Ratio [-]')
        axes[-1,0].set_xlabel('Temperature [K]')
        norm = mpl.colors.Normalize(vmin=-1.0, vmax=1.0) #Could use maximum error
        for c in contours:
            c.set_norm(norm)
        cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm,cmap=cmap), ax=axes,
                          extend='both')
        cb.set_label(r'Relative Error $\mathrm{\frac{\tau_{full}-\tau_{red}}{\tau_{full}}}$')
        plot_filename = os.path.join(parent.project['dir_public'],'plots',f'idt_error_matrix_{comp}.png')
        plt.savefig(plot_filename)
        #parent.plotfilenames.append(plot_filename)
        plt.close(fig)

    error_data = {}
    for mech_name in comparison_mechs:
        e = relative_error_sum[mech_name]/num_idts_total
        dir_desk = test_mechs[mech_name]['dir']
        ns_txt = os.path.join(dir_desk,'mech','ns.txt')
        with open(ns_txt,'r') as f:
            ns = int(f.read())
        base_name = test_mechs[mech_name]['base_name']
        if(base_name not in error_data):
            error_data[base_name] = {'x': [ns], 'y': [e]}
        else:
            error_data[base_name]['x'].append(ns)
            error_data[base_name]['y'].append(e)

    fig, axis = plt.subplots(1,1,layout='constrained')
    for base_name in error_data:
        idxs = np.argsort(error_data[base_name]['x'])
        x = np.array(error_data[base_name]['x'])[idxs]
        y = np.array(error_data[base_name]['y'])[idxs]
        if(len(x)==1):
            axis.plot(x,y,marker='o',label=base_name)
        else:
            axis.plot(x,y,label=base_name)
    axis.set_xlabel('Number of species')
    axis.set_ylabel(f'Mean absolute relative error: {db_name}')
    axis.legend()

    plot_filename = os.path.join(parent.project['dir_public'],'plots',f'{db_name}_error_trends.png')
    plt.savefig(plot_filename)
    parent.plotfilenames.append(plot_filename)
    plt.close()

    return error_data



def psr_ext_plots(parent, db_name, test_mechs):
    database = parent.project['database'][db_name]
    phi_list = database['phi']
    T0_list = database['T0']
    atm_list = database['atm']
    fuel_list = database['fuel']
    oxid_list = database['oxid']
    reactor = database['reactor']

    ext_tau = { mech_name: [] for mech_name in test_mechs }
    for fuel_name in fuel_list:
        fuel = parent.project['fuel'][fuel_name]
        for oxid_name in oxid_list:
            oxid = parent.project['oxid'][oxid_name]
            comp = fuel_name+oxid_name
            for phi in phi_list:
                for atm in atm_list:
                    for T0 in T0_list:
                        fig, axis = plt.subplots(1,1, layout='constrained')
                        for mech_name in test_mechs:
                            dir_desk=test_mechs[mech_name]['dir']
                            dir_raw = cond2dir(dir_desk, fuel_name, oxid_name, phi, atm, T0, reactor, parent.n_digit)
                            raw = load_raw(os.path.join(dir_raw,'raw.npz'))
                            residence_time = raw['axis0']
                            T = raw['temperature']
                            ext_tau[mech_name].append(residence_time[-1])

                            ns = test_mechs[mech_name]['ns']
                            ls = test_mechs[mech_name].get('ls', '-')
                            axis.semilogx(residence_time, T, label=f"{mech_name} ({ns} sp)", ls=ls)
                        axis.legend()
                        axis.set_title(f"{comp}: phi={phi}, p={atm} atm, T0={T0} K")
                        axis.set_xlabel('tau [s]')
                        axis.set_ylabel('Temperature [K]')
                        plot_filename = os.path.join(parent.project['dir_public'],'plots',f'psr_{comp}_{phi}_{atm}_{T0}.png')
                        plt.savefig(plot_filename)
                        parent.plotfilenames.append(plot_filename)
                        plt.close(fig)

    comparison_mechs = [ m for m in test_mechs if m != "detailed" ]
    error_data = {}
    for mech_name in comparison_mechs:
        ext_tau_detailed = np.array(ext_tau['detailed'])
        ext_tau_comparison = np.array(ext_tau[mech_name])
        ext_tau_err = (ext_tau_detailed - ext_tau_comparison)/(ext_tau_detailed)
        e = np.mean(np.sum(np.abs(ext_tau_err)))

        dir_desk = test_mechs[mech_name]['dir']
        ns_txt = os.path.join(dir_desk,'mech','ns.txt')
        with open(ns_txt,'r') as f:
            ns = int(f.read())
        base_name = test_mechs[mech_name]['base_name']
        if(base_name not in error_data):
            error_data[base_name] = {'x': [ns], 'y': [e]}
        else:
            error_data[base_name]['x'].append(ns)
            error_data[base_name]['y'].append(e)

    fig, axis = plt.subplots(1,1,layout='constrained')
    for base_name in error_data:
        idxs = np.argsort(error_data[base_name]['x'])
        x = np.array(error_data[base_name]['x'])[idxs]
        y = np.array(error_data[base_name]['y'])[idxs]
        if(len(x)==1):
            axis.plot(x,y,marker='o',label=base_name)
        else:
            axis.plot(x,y,label=base_name)
    axis.set_xlabel('Number of species')
    axis.set_ylabel(f'Mean absolute relative error: {db_name}')
    axis.legend()

    plot_filename = os.path.join(parent.project['dir_public'],'plots',f'{db_name}_error_trends.png')
    plt.savefig(plot_filename)
    parent.plotfilenames.append(plot_filename)
    plt.close()

    return error_data


def premix_plots(parent, db_name, test_mechs):
    database = parent.project['database'][db_name]
    phi_list = database['phi']
    T0_list = database['T0']
    atm_list = database['atm']
    fuel_list = database['fuel']
    oxid_list = database['oxid']
    reactor = database['reactor']

    plot_db = {mech_name: {} for mech_name in test_mechs}
    comp_keys=set()
    for mech_name in test_mechs:
        for fuel_name in fuel_list:
            fuel = parent.project['fuel'][fuel_name]
            for oxid_name in oxid_list:
                oxid = parent.project['oxid'][oxid_name]
                comp = fuel_name+oxid_name
                comp_keys.add(comp)

                plot_db[mech_name][comp] = {'flame_speed_db': []}
                for phi in phi_list:
                    for atm in atm_list:
                        for T0 in T0_list:
                        #fig, axis = plt.subplots(1,1, layout='constrained')
                            dir_desk=test_mechs[mech_name]['dir']
                            dir_raw = cond2dir(dir_desk, fuel_name, oxid_name, phi, atm, T0, reactor, parent.n_digit)
                            raw = load_raw(os.path.join(dir_raw,'raw.npz'))
                            flame_speed = raw['flame_speed'][0]
                            plot_db[mech_name][comp]['flame_speed_db'].append([T0,
                                                                          phi,
                                                                          atm,
                                                                          flame_speed])
                tmp_db = np.array(plot_db[mech_name][comp]['flame_speed_db'])
                plot_db[mech_name][comp]['flame_speed_db'] = tmp_db

    for T0 in T0_list:
        for atm in atm_list:
            for comp in comp_keys:
                fig, axis = plt.subplots(1,1, layout='constrained')
                for mech_name in test_mechs:
                    fs_db = plot_db[mech_name][comp]['flame_speed_db']
                    data = fs_db[np.isclose(fs_db[:,0],T0) &
                                 np.isclose(fs_db[:,2],atm),:]
                    ns = test_mechs[mech_name]['ns']
                    ls = test_mechs[mech_name].get('ls', '-')
                    axis.plot(data[:,1], data[:,3],  label=f"{mech_name} ({ns} sp)",ls=ls)
                base_fontsize = 20
                min_fontsize = 12
                num_series = len(test_mechs)
                calculated_size = max(min_fontsize,
                                      base_fontsize - (num_series * 0.7))
                axis.legend(loc=(1.1, 0.1),fontsize=calculated_size)
                axis.set_title(f"comp={comp}, T0={T0} K, p={atm} atm")
                axis.set_xlabel('phi')
                axis.set_ylabel('Flame Speed [m/s]')
                plot_filename = os.path.join(parent.project['dir_public'],'plots',f'premix_{comp}_{T0}_{atm}.png')
                plt.savefig(plot_filename)
                parent.plotfilenames.append(plot_filename)
                plt.close(fig)

    comparison_mechs = [ m for m in test_mechs if m != "detailed" ]
    error_data = {}
    for mech_name in comparison_mechs:
        fs_detailed = []
        fs_comparison = []
        for comp in comp_keys:
            fs_detailed.append(plot_db['detailed'][comp]['flame_speed_db'][:,3])
            fs_comparison.append(plot_db[mech_name][comp]['flame_speed_db'][:,3])
        fs_detailed = np.array(fs_detailed)
        fs_comparison = np.array(fs_comparison)
        fs_err = (fs_detailed - fs_comparison)/(fs_detailed)
        e = np.mean(np.sum(np.abs(fs_err)))

        dir_desk = test_mechs[mech_name]['dir']
        ns_txt = os.path.join(dir_desk,'mech','ns.txt')
        with open(ns_txt,'r') as f:
            ns = int(f.read())
        base_name = test_mechs[mech_name]['base_name']
        if(base_name not in error_data):
            error_data[base_name] = {'x': [ns], 'y': [e]}
        else:
            error_data[base_name]['x'].append(ns)
            error_data[base_name]['y'].append(e)

    fig, axis = plt.subplots(1,1,layout='constrained')
    for base_name in error_data:
        idxs = np.argsort(error_data[base_name]['x'])
        x = np.array(error_data[base_name]['x'])[idxs]
        y = np.array(error_data[base_name]['y'])[idxs]
        if(len(x)==1):
            axis.plot(x,y,marker='o',label=base_name)
        else:
            axis.plot(x,y,label=base_name)
    axis.set_xlabel('Number of species')
    axis.set_ylabel(f'Mean absolute relative error: {db_name}')
    axis.legend()

    plot_filename = os.path.join(parent.project['dir_public'],'plots',f'{db_name}_error_trends.png')
    plt.savefig(plot_filename)
    parent.plotfilenames.append(plot_filename)
    plt.close()

    return error_data

def cumulative_error_plot(parent, error_data):
    fig, axis = plt.subplots(1,1,layout='constrained')
    for base_name in error_data:
        idxs = np.argsort(error_data[base_name]['x'])
        x = np.array(error_data[base_name]['x'])[idxs]
        y = np.array(error_data[base_name]['y'])[idxs]
        if(len(x)==1):
            axis.plot(x,y,marker='o',label=base_name)
        else:
            axis.plot(x,y,label=base_name)
    axis.set_xlabel('Number of species')
    axis.set_ylabel('Sum mean absolute relative errors\nover all test dbs')
    axis.legend()

    plot_filename = os.path.join(parent.project['dir_public'],'plots',f'total_error_trends.png')
    plt.savefig(plot_filename)
    parent.plotfilenames.append(plot_filename)
    plt.close()

