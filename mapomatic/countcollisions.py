#!/usr/bin/env python
"""
Functions for counting frequency collisions
"""

import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
import numpy as np
import yaml
import matplotlib.pyplot as plt
import coupling_tools as ct
import networkx as nx
from matplotlib.lines import Line2D

#import multi_qubit_exp.mappings as mp

def extract_freq_data(exp_params):
    num_qubits = 0

    # find out how many qubits there are
    for key in exp_params['logical_channels']:
        try:
            num_qubits = max(num_qubits, int(key.split('Q')[1]))
        except:
            continue
    num_qubits += 1 # qubit numbering starts at zero

    data_freq = []
    for ii in range(num_qubits):
        qubit = 'Q'+str(ii)
        qfreq = np.nan
        anharm = np.nan
        if qubit in exp_params['logical_channels']:
            if str(exp_params['logical_channels'][qubit]['freq'])[0] == '$': # it's a variable in exp_params
                if (qubit+'freq') in exp_params['variables'].keys():
                    qfreq = exp_params['variables'][qubit+'freq']
                elif (qubit+'_Freq') in exp_params['variables'].keys():
                    qfreq = exp_params['variables'][qubit+'_Freq']
            else: # it's hard coded into the logical channel
                qfreq = exp_params['logical_channels'][qubit]['freq']
            if 'Xp12' in exp_params['logical_channels'][qubit]['pulses']: # anharmonicity was measured
                #print(exp_params['logical_channels'][qubit]['pulses']['Xp12']['params']['freq_offset'])
                if str(exp_params['logical_channels'][qubit]['pulses']['Xp12']['params']['freq_offset'])[0] == '$': # it's a variable in exp_params
                    if (qubit+'anharm') in exp_params['variables'].keys():
                        anharm = exp_params['variables'][qubit+'anharm']
                    elif (qubit+'_Anharm') in exp_params['variables'].keys():
                        anharm = exp_params['variables'][qubit+'_Anharm']
                else:
                    anharm = exp_params['logical_channels'][qubit]['pulses']['Xp12']['params']['freq_offset']
            else: # placeholder values
                anharm = np.nan #-300e6
        else: # placeholder values
            qfreq = np.nan #5e9
            anharm = np.nan #-300e6
        data_freq.append([str(float(qfreq)/1e9), str(float(anharm)/1e9)]) # f01's and anharm's in GHz
    return np.asfarray(data_freq)


def qanhsfromfs(qfs, device):
#Arguments.
    #qfs:       1-column numpy matrix. Frequencies (GHz) of all qubits starting with Q0.
    #           Empty entries may be filled with np.nan
    #device:    'Falcon 28Q HeavyHex', 'Falcon 28Q HeavyHex AltNums', 'Falcon v3 27Q' or 'Hummingbird 58Q HeavyHex'. Others TBD.
#Returns
    #qfrqs:     np matrix. Column 0 holds qubit frequencies (GHz) in correct order for this multiQ array type
    #           Column 1 holds anharmonicities of each qubit (GHz).

    qadjc = qubit_adjacency(device)
    numQBs = len(qadjc)
    qfrqs = np.zeros([numQBs,2])
    qfrqs[:,0] = qfs

    thedevices = load_standard_devices()
    anhpredictparams = thedevices[device]['anhvsf']
    for n in np.arange(numQBs):
        qfrqs[n,1] = anhpredictparams[n]['anhfromfoffs'] + anhpredictparams[n]['anhfromfcoef']*qfrqs[n,0]
    return qfrqs


def qanhsfromfs_othercorrel(qfs, device, correl):
#Arguments.
    #qfs:       1-column numpy matrix. Frequencies (GHz) of all qubits starting with Q0.
    #           Empty entries may be filled with np.nan
    #device:    'Falcon 28Q HeavyHex', 'Falcon 28Q HeavyHex AltNums', etc. Defines the lattice.
    #correl:    'Falcon 28Q HeavyHex', 'Falcon 28Q HeavyHex AltNums', etc. Defines the correlation.
#Returns
    #qfrqs:     np matrix. Column 0 holds qubit frequencies (GHz) in correct order for this multiQ array type
    #           Column 1 holds anharmonicities of each qubit (GHz).

    qadjc = qubit_adjacency(device)
    numQBs = len(qadjc)
    qfrqs = np.zeros([numQBs,2])
    qfrqs[:,0] = qfs

    thedevices = load_standard_devices()
    anhpredictparams = thedevices[correl]['anhvsf']
    #possibility 1: same number of qubits and presume same correlations as other known lattice
    if len(anhpredictparams) == numQBs:
        for n in np.arange(numQBs):
            qfrqs[n,1] = anhpredictparams[n]['anhfromfoffs'] + anhpredictparams[n]['anhfromfcoef']*qfrqs[n,0]
    #possibility 2: lattice is different than other known lattice but want to use representative correlation from that lattice.
    #Use the correlation for the FIRST qubit.
    else:
        for n in np.arange(numQBs):
            qfrqs[n,1] = anhpredictparams[0]['anhfromfoffs'] + anhpredictparams[0]['anhfromfcoef']*qfrqs[n,0]
    return qfrqs


def names_standard_devices(Printit):
#Find list of names of standard devices
#If desired, print names and numQBs of all standard devices. Print main attribute names.
#Returns
    #stddevnames:  list of all names in standard_devices.yaml

    thedevices = load_standard_devices()
    if Printit == 1:
        print('\nIn standard_devices.yaml are:')
        for dev in thedevices.keys():
            print('\t'+dev+'. Num QBs = '+str(thedevices[dev]['numQ']))
        #print('\n')
        print('\nMain attributes of each device: '+str(list(thedevices[dev].keys())))
    return list(thedevices.keys())


def load_standard_devices():
#Load all standard devices and all info into a dictionary
#Returns
    #stddevs: dictionary of all devices in standard_devices.yaml.
    #         attributes should include numQ, anhvsf, fvsR, connections, coords, schematicsize
    with open("standard_devices.yaml", 'r') as stream:
        try:
            stddevs = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return stddevs


def qfrqsfromRs(qRs, device):
#Arguments.
    #qRs:       1-column numpy matrix. Junction resistances (kOhm) of all qubits starting with Q0.
    #           Empty entries may be filled with np.nan
    #device:    'Falcon 28Q HeavyHex', 'Falcon 28Q HeavyHex AltNums', 'Falcon v3 27Q' or 'Hummingbird 58Q HeavyHex'. Others TBD.
#Returns
    #qfrqs:     np matrix. Column 0 holds qubit frequencies (GHz) in correct order for this multiQ array type
    #           Column 1 holds anharmonicities of each qubit (GHz).

    qadjc = qubit_adjacency(device)
    numQBs = len(qadjc)
    qfrqs = np.zeros([numQBs,2])

    thedevices = load_standard_devices()
    fpredictparams = thedevices[device]['fvsR']
    anhpredictparams = thedevices[device]['anhvsf']
    for n in np.arange(numQBs):
        qfrqs[n,0] = fpredictparams[n]['ffromRoffs'] + fpredictparams[n]['ffromRcoef']*(qRs[n]**fpredictparams[n]['ffromRexp'])
        qfrqs[n,1] = anhpredictparams[n]['anhfromfoffs'] + anhpredictparams[n]['anhfromfcoef']*qfrqs[n,0]
    return qfrqs


def qfrqsfromRs_othercorrel(qRs, device, correl):
#Arguments.
    #qRs:       1-column numpy matrix. Junction resistances (kOhm) of all qubits starting with Q0.
    #           Empty entries may be filled with np.nan
    #device:    'Falcon 28Q HeavyHex', 'Falcon 28Q HeavyHex AltNums', etc. Use layout from this device
    #correl:    'Falcon 28Q HeavyHex', 'Falcon 28Q HeavyHex AltNums', etc. Use correlation defined for this device.
#Returns
    #qfrqs:     np matrix. Column 0 holds qubit frequencies (GHz) in correct order for this multiQ array type
    #           Column 1 holds anharmonicities of each qubit (GHz).

    qadjc = qubit_adjacency(device)
    numQBs = len(qadjc)
    qfrqs = np.zeros([numQBs,2])

    thedevices = load_standard_devices()
    fpredictparams = thedevices[correl]['fvsR']
    anhpredictparams = thedevices[correl]['anhvsf']
    #possibility 1: same number of qubits and presume same correlations as other known lattice
    if len(fpredictparams) == numQBs:
        for n in np.arange(numQBs):
            qfrqs[n,0] = fpredictparams[n]['ffromRoffs'] + fpredictparams[n]['ffromRcoef']*(qRs[n]**fpredictparams[n]['ffromRexp'])
            qfrqs[n,1] = anhpredictparams[n]['anhfromfoffs'] + anhpredictparams[n]['anhfromfcoef']*qfrqs[n,0]
    #possibility 2: lattice is different than other known lattice but want to use representative correlation from that lattice.
    #Use the correlation for the FIRST qubit.
    else:
        for n in np.arange(numQBs):
            qfrqs[n,0] = fpredictparams[0]['ffromRoffs'] + fpredictparams[0]['ffromRcoef']*(qRs[n]**fpredictparams[0]['ffromRexp'])
            qfrqs[n,1] = anhpredictparams[0]['anhfromfoffs'] + anhpredictparams[0]['anhfromfcoef']*qfrqs[n,0]
    return qfrqs        


def collision_bounds(anharm, boundaries={}, absminmax = {}):
    """
    Argument: anharm in GHz
    Optional argument: boundaries. If specified, use these and anharmonicity to define bounds.
                       If none specified, use default boundaries specified in terms of anharm.
                       String inputs 'gate_err_1%' and 'gate_err_0.5%' will output the best-estimate values for those thresholds.
    Optional argument: absminmax. Specify as two-value list or array of allowable min & max freqs (GHz).
                       If none specified, use default limits for typical transmon 4.8-5.4 GHz.
    
    Returns: bounds, a dict specifying bounds in GHz on degeneracy of
    qubit pairs for each of seven collision types. For slow gate type, bound is
    upper bound of absolute difference between QB freqs. For spectator type, it is
    bound on degeneracy between control 02 and target 01 + spectator 01.
    """

    if boundaries == {}:
        boundaries['NearNbr_01_01'] = [0,0.017]
        boundaries['NearNbr_01_022'] = [-0.004,0.004]
        boundaries['NearNbr_01_12'] = [-0.03,0.03]
        boundaries['SlowGateBelowNegAnhOv2'] = boundaries['NearNbr_01_022'][0]
        boundaries['SlowGateAboveAnh'] = boundaries['NearNbr_01_12'][1]
        boundaries['TviaC_01_01'] = boundaries['NearNbr_01_01']
        boundaries['TviaC_01_12'] = [-0.025,0.025]
        boundaries['Spectator'] = boundaries['NearNbr_01_01']
    elif boundaries == 'gate_err_1%':
        boundaries = dict([('NearNbr_01_01', [0,0.017]), ('NearNbr_01_022', [-0.004,0.004]), ('NearNbr_01_12', [-0.03,0.03]), ('TviaC_01_12', [-0.025,0.025])])
        boundaries['SlowGateBelowNegAnhOv2'] = boundaries['NearNbr_01_022'][0]
        boundaries['SlowGateAboveAnh'] = boundaries['NearNbr_01_12'][1]
        boundaries['TviaC_01_01'] = boundaries['NearNbr_01_01']
        boundaries['Spectator'] = boundaries['NearNbr_01_01']
    elif boundaries == 'gate_err_0.5%':
        boundaries = dict([('NearNbr_01_01', [0,0.04]), ('NearNbr_01_022', [-0.01,0.02]), ('NearNbr_01_12', [-0.04,0.04])])
        boundaries['SlowGateBelowNegAnhOv2'] = boundaries['NearNbr_01_022'][0]
        boundaries['SlowGateAboveAnh'] = boundaries['NearNbr_01_12'][1]
        boundaries['TviaC_01_01'] = boundaries['NearNbr_01_01']
        boundaries['Spectator'] = boundaries['NearNbr_01_01']
        boundaries['TviaC_01_12'] = boundaries['NearNbr_01_12']
    
    bounds = {}
    bounds['NearNbr_01_01'] = np.array(boundaries['NearNbr_01_01'])
    bounds['NearNbr_01_022'] = np.array(boundaries['NearNbr_01_022']) + abs(anharm)/2
    bounds['NearNbr_01_12'] = np.array(boundaries['NearNbr_01_12']) + abs(anharm)
    bounds['SlowGate'] = np.array([-abs(anharm)/2 + boundaries['SlowGateBelowNegAnhOv2'], abs(anharm) + boundaries['SlowGateAboveAnh']])
    bounds['TviaC_01_01'] = np.array(boundaries['TviaC_01_01'])
    bounds['TviaC_01_12'] = np.array(boundaries['TviaC_01_12']) + abs(anharm)
    bounds['Spectator'] = np.array(boundaries['Spectator'])

    if absminmax == {}:
        bounds['AbsMinMax'] = np.array([4.8,5.4]) #default min acceptable QB freq = 4.8GHz, max = 5.4 GHz
    else:
        bounds['AbsMinMax'] = np.array(absminmax)

    return bounds


def qubit_adjacency(qubit_dev, devicedef = []):
    
#qubit_dev: name of device or path and filename of 'device.yaml' file
#devicedef: dictionary defining device, typically loaded using cc.load_standard_devices(). Should include 
#           fields 'numQ' and 'fpatterns'. should correspond to definition of 'device'

    if devicedef != []:
        connects = devicedef['connections']
        numQBs = devicedef['numQ']
        canreturn = 1
    elif 'device.yaml' in qubit_dev:
        connects = ct.get_coupling_map(qubit_dev)
        numQBs = max(np.ravel(np.array(connects))) + 1 # qubit numbering starts at zero
        canreturn = 1
    else:
        thedevices = load_standard_devices()
        thedevnames = names_standard_devices(0)
        if qubit_dev in thedevnames:
            connects = thedevices[qubit_dev]['connections']
            numQBs = thedevices[qubit_dev]['numQ']
            canreturn = 1
        else:
            print('Please input a standard device name or "PATH/device.yaml".')
            canreturn = 0
    if canreturn == 1:
        return ct.pairwise_coupling_to_adjacency(connects,numQBs)
    else:
        return []


def get_collision_7typemap(qfrqs, device, anharm, bounds, gates=[], custbound=None, type8plus = 'n', devdef = []):
    """
    
    
    Arguments.
        qfrqs:     np matrix. Column 0 holds qubit frequencies (GHz) in correct order for this multiQ array type
                   Column 1 (if included) holds anharmonicities of each qubit (GHz).
        device:    'NTPP7', '17Q SurfCode SkewSym', '16Q square' or other string
        anharm:    anharmonicity (GHz). Either enter value here or in column 1 of anharms (latter has precedence). Else count will be wrong!
        bounds:    a dict output by collision_bounds() specifying bounds in GHz for each of 7 collis types.
                   Will be ignored if qfrqs includes a column 1 of anharms.
        gates:     list of pairwise connections between qubits [A,B]. first in each pair is the control.
                   Should include ALL nearest-neighbor pairs in the lattice. If omitted, function will assume
                   highest-freq of each pair is control.
        custbound: Input for custom collision bounds, to be used by collision_bounds() to generate custom bounds for each
                   qubit's anharmonicity. Use string inputs 'gate_err_1%' and 'gate_err_0.5%' for default values for those thresholds
        type8plus: If 'y' then collisions are computed using get_collision_13typemap()
        devdef:    dictionary defining device, typically loaded using cc.load_standard_devices(). Should include 
                   fields 'numQ', 'fpatterns' and 'connections'. should correspond to definition of 'device'
    Returns
       collision_map: where there are n qubits, this is a nxnx7 matrix of binary values.
                      The mxnxk element indicates type k collision between qubit m and n
                      If type8plus = 'y' then this will be a nxnx13 matrix
    """

    if custbound is None:
        custbound = {}
    if (anharm != []) and (bounds == []):
        bounds = collision_bounds(anharm, boundaries=custbound)
    adj_matrix = qubit_adjacency(device, devicedef=devdef)
    adj_squared = np.dot(adj_matrix, adj_matrix)
    num_qubits = int(np.sqrt(np.size(adj_matrix)))
    
    if gates == []: #find the gates in default manner
        if qfrqs.size == num_qubits:
            gates = choose_control_higher(ct.adjacency_to_pairwise_coupling(adj_matrix), qfrqs)
        else:
            gates = choose_control_higher(ct.adjacency_to_pairwise_coupling(adj_matrix), qfrqs[:,0])

    collision_map = np.zeros((num_qubits,num_qubits,7),dtype=int)
    #collision_map = np.zeros((num_qubits,num_qubits)) - np.ones((num_qubits,num_qubits))
    
    #if anharms are not populated into qfrqs, populate with uniform anharm
    if qfrqs.size == num_qubits:
        qfrqsanhs = np.zeros([num_qubits,2])
        qfrqsanhs[:,0] = np.transpose(qfrqs)
        if anharm == []:
            qfrqsanhs[:,1] = np.nan
        else:
            qfrqsanhs[:,1] = anharm
    else:
        qfrqsanhs = qfrqs.copy()

#    #no column 1, i.e. anharmonicities NOT specified for each qubit
#    if qfrqs.size == num_qubits:
#        for q1idx in np.arange(num_qubits):
#            for q2idx in np.arange(num_qubits):
#                if adj_matrix[q1idx,q2idx] and q1idx < q2idx:
#                    detuning = abs(qfrqs[q1idx] - qfrqs[q2idx])
#                    if [q1idx,q2idx] in gates:
#                        detuningCtoT = qfrqs[q1idx] - qfrqs[q2idx]
#                    elif [q2idx, q1idx] in gates:
#                        detuningCtoT = qfrqs[q2idx] - qfrqs[q1idx]
#                    #collision type 1
#                    if (detuning >= bounds['NearNbr_01_01'][0]) and (detuning <= bounds['NearNbr_01_01'][1]):
#                        collision_map[q1idx,q2idx,0] = 1
#                        #print('type1')
#                    #collision type 2
#                    elif (detuning >= bounds['NearNbr_01_022'][0]) and (detuning <= bounds['NearNbr_01_022'][1]):
#                        collision_map[q1idx,q2idx,1] = 1
#                        #print('type2')
#                    #collision type 3
#                    elif (detuning >= bounds['NearNbr_01_12'][0]) and (detuning <= bounds['NearNbr_01_12'][1]):
#                        collision_map[q1idx,q2idx,2] = 1
#                        #print('type3')
#                    #collision type 4
#                    elif (detuningCtoT > bounds['SlowGate'][1]) | (detuningCtoT < bounds['SlowGate'][0]):
#                        collision_map[q1idx,q2idx,3] = 1
#                        #print('type4')
#                    #collision type 7
#                    for q3idx in np.delete(np.arange(num_qubits),[q1idx,q2idx]):
#                        if [q1idx,q2idx] in gates and (adj_matrix[q1idx,q3idx]):
#                            twophotondetun = abs(2*qfrqs[q1idx] + anharm - qfrqs[q2idx] - qfrqs[q3idx])
#                            if (twophotondetun >= bounds['Spectator'][0]) and (twophotondetun <= bounds['Spectator'][1]):
#                                collision_map[q1idx,q2idx,6] = 1
#                                #print('type7. Q'+str(q1idx)+'Q'+str(q2idx)+'Q'+str(q3idx))
#                        elif [q2idx,q1idx] in gates and (adj_matrix[q2idx,q3idx]):
#                            twophotondetun = abs(2*qfrqs[q2idx]+anharm - qfrqs[q1idx] - qfrqs[q3idx])
#                            if (twophotondetun >= bounds['Spectator'][0]) and (twophotondetun <= bounds['Spectator'][1]):
#                                collision_map[q1idx,q2idx,6] = 1
#                                #print('type7. Q'+str(q1idx)+'Q'+str(q2idx)+'Q'+str(q3idx))
#                        else:
#                            []
#                            #print('notype7. Q'+str(q1idx)+'Q'+str(q2idx)+'Q'+str(q3idx))
#                elif adj_squared[q1idx,q2idx] and q1idx < q2idx:
#                    detuning = abs(qfrqs[q1idx] - qfrqs[q2idx])
#                    for q3idx in np.delete(np.arange(num_qubits),[q1idx,q2idx]):
#                        if adj_matrix[q1idx,q3idx] and adj_matrix[q2idx,q3idx]:
#                            #print('Q'+str(q1idx)+'Q'+str(q2idx)+' ControlQ'+str(q3idx))
#                            if ([q3idx,q1idx] in gates) or ([q3idx,q2idx] in gates):
#                                #collision type 5
#                                if (detuning >= bounds['TviaC_01_01'][0]) and (detuning <= bounds['TviaC_01_01'][1]):
#                                    collision_map[q1idx,q2idx,4] = 1
#                                    #print('type5. Q'+str(q1idx)+'Q'+str(q2idx)+' ControlQ'+str(q3idx))
#                                #collision type 6
#                                elif (detuning >= bounds['TviaC_01_12'][0]) and (detuning <= bounds['TviaC_01_12'][1]):
#                                    collision_map[q1idx,q2idx,5] = 1
#                                    #print('type6. Q'+str(q1idx)+'Q'+str(q2idx))
#                else:
#                    collision_map[q1idx,q2idx,0] = 0
#    #anharmonicities specified in col 1 for each qubit in col 0
#    else:
    for q1idx in np.arange(num_qubits):
        if qfrqs.size == num_qubits:
            bounds1 = bounds.copy()
        else:
            bounds1 = collision_bounds(qfrqsanhs[q1idx,1], boundaries=custbound)
        for q2idx in np.arange(num_qubits):
            if qfrqs.size == num_qubits:
                bounds2 = bounds.copy()
            else:
                bounds2 = collision_bounds(qfrqsanhs[q2idx,1], boundaries=custbound)
            detuning1 = qfrqsanhs[q1idx,0] - qfrqsanhs[q2idx,0]
            detuning2 = qfrqsanhs[q2idx,0] - qfrqsanhs[q1idx,0]
            if adj_matrix[q1idx,q2idx] and q1idx < q2idx:
                #collision type 1
                if (detuning1 >= bounds1['NearNbr_01_01'][0]) and (detuning1 <= bounds1['NearNbr_01_01'][1]):
                    collision_map[q1idx,q2idx,0] = 1
                elif (detuning2 >= bounds2['NearNbr_01_01'][0]) and (detuning2 <= bounds2['NearNbr_01_01'][1]):
                    collision_map[q1idx,q2idx,0] = 1
                #collision type 2
                elif (detuning1 >= bounds1['NearNbr_01_022'][0]) and (detuning1 <= bounds1['NearNbr_01_022'][1]):
                    collision_map[q1idx,q2idx,1] = 1
                elif (detuning2 >= bounds2['NearNbr_01_022'][0]) and (detuning2 <= bounds2['NearNbr_01_022'][1]):
                    collision_map[q1idx,q2idx,1] = 1
                #collision type 3
                elif (detuning1 >= bounds1['NearNbr_01_12'][0]) and (detuning1 <= bounds1['NearNbr_01_12'][1]):
                    collision_map[q1idx,q2idx,2] = 1
                elif (detuning2 >= bounds2['NearNbr_01_12'][0]) and (detuning2 <= bounds2['NearNbr_01_12'][1]):
                    collision_map[q1idx,q2idx,2] = 1
                #collision type 4
                elif ([q1idx,q2idx] in gates) and ((detuning1 > bounds1['SlowGate'][1]) | (detuning1 < bounds1['SlowGate'][0])):
                    collision_map[q1idx,q2idx,3] = 1
                elif ([q2idx,q1idx] in gates) and ((detuning2 > bounds2['SlowGate'][1]) | (detuning2 < bounds2['SlowGate'][0])):
                    collision_map[q1idx,q2idx,3] = 1
                else:
                    []
                #collision type 7
                for q3idx in np.delete(np.arange(num_qubits),[q1idx,q2idx]):
                    if [q1idx,q2idx] in gates and (adj_matrix[q1idx,q3idx]):
                        twophotondetun = abs(2*qfrqsanhs[q1idx,0] + qfrqsanhs[q1idx,1] - qfrqsanhs[q2idx,0] - qfrqsanhs[q3idx,0])
                        if (twophotondetun >= bounds1['Spectator'][0]) and (twophotondetun <= bounds1['Spectator'][1]):
                            collision_map[q1idx,q2idx,6] = 1
                    elif [q2idx,q1idx] in gates and (adj_matrix[q2idx,q3idx]):
                        twophotondetun = abs(2*qfrqsanhs[q2idx,0] + qfrqsanhs[q2idx,1] - qfrqsanhs[q1idx,0] - qfrqsanhs[q3idx,0])
                        if (twophotondetun >= bounds2['Spectator'][0]) and (twophotondetun <= bounds2['Spectator'][1]):
                            collision_map[q1idx,q2idx,6] = 1
                    else:
                        []
            elif adj_squared[q1idx,q2idx] and q1idx < q2idx: #types 5 and 6. Q1 and/or Q2 are targets, Q3 is control
                for q3idx in np.delete(np.arange(num_qubits),[q1idx,q2idx]):
                    if adj_matrix[q1idx,q3idx] and adj_matrix[q2idx,q3idx]:
                        if ([q3idx,q1idx] in gates) or ([q3idx,q2idx] in gates):
                            #collision type 5
                            if (detuning1 >= bounds1['TviaC_01_01'][0]) and (detuning1 <= bounds1['TviaC_01_01'][1]):
                                collision_map[q1idx,q2idx,4] = 1
                            elif (detuning2 >= bounds2['TviaC_01_01'][0]) and (detuning2 <= bounds2['TviaC_01_01'][1]):
                                collision_map[q1idx,q2idx,4] = 1
                            #collision type 6
                            elif (detuning1 >= bounds1['TviaC_01_12'][0]) and (detuning1 <= bounds1['TviaC_01_12'][1]):
                                collision_map[q1idx,q2idx,5] = 1
                            elif (detuning2 >= bounds2['TviaC_01_12'][0]) and (detuning2 <= bounds2['TviaC_01_12'][1]):
                                collision_map[q1idx,q2idx,5] = 1
            else:
                collision_map[q1idx,q2idx,0] = 0
    return collision_map


def list_collisions(collision_map):

#Arguments
    #collision_map: where there are n qubits, this is a nxnx7 matrix of binary values.
    #               The mxnxk element indicates type k collision between qubit m and n.
    #               This is output by get_collision_7typemap()
    results={}
    for n in np.arange(7):
        collisionlist = ''; tmp=[]
        for nn in np.arange(collision_map.shape[1]):
            for nnn in np.arange(collision_map.shape[1]):
                if collision_map[nn,nnn,n]:
                    if collisionlist != '':
                        collisionlist = collisionlist+', '
                    #collisionlist = collisionlist+'Q'+str(nn+1)+'/Q'+str(nnn+1)
                    collisionlist = collisionlist+'Q'+str(nn)+'/Q'+str(nnn)
                    tmp.append([nn, nnn])
        print('Type '+str(n+1)+':  '+str(np.sum(collision_map[:,:,n]))+' collisions.\t'+collisionlist)
        results.update({n+1: tmp})
    print('Total: '+str(np.sum(collision_map))+' collisions.')
    return results

def list_stats(freq_data):
    if len(freq_data.shape) == 2:
        maskvals = ~np.isnan(freq_data[:,0]) #omit missing QBs
        freqsnonans = freq_data[maskvals,0]
    else: #in case input is only freqs no aharms
        maskvals = ~np.isnan(freq_data)
        freqsnonans = freq_data[maskvals]
    print('f01 statistics:')
    print('Num QBs: '+str(sum(maskvals)))
    print('Mean frequency (GHz): '+f'{np.mean(freqsnonans):.4f}')
    print('Median frequency (GHz): '+f'{np.median(freqsnonans):.4f}')
    print('Max frequency (GHz): '+f'{np.max(freqsnonans):.4f}')
    print('Min frequency (GHz): '+f'{np.min(freqsnonans):.4f}')
    print('Std frequency (GHz): '+f'{np.std(freqsnonans):.4f}')


def showlattice(qubit_dev, color = '#d2d4d2', node_size=1000, schemsize='None'):
    """
    visual representation of the qubit lattice
    **kwrd arguments:
            qubit_dev:    'NTPP7', '17Q SurfCode SkewSym', '16Q square' or other string, or else path to device.yaml
            color - change color of the nodes, a list can also be input for different colors
            node_size - size of the nodes, defaults to 1000, max 2500
            schemsize - size of figure [x,y]
    """

    if 'device.yaml' in qubit_dev: #load info from yaml file!!
        connects = ct.get_coupling_map(qubit_dev)
        nodecoords = ct.get_node_coords(qubit_dev)
        canreturn = 1
        schemsize=[10,10]
        numQBs = max(np.ravel(np.array(connects))) + 1
    else: #load info from standard device list
        thedevices = load_standard_devices()
        thedevnames = names_standard_devices(0)
        if qubit_dev in thedevnames:
            connects = thedevices[qubit_dev]['connections']
            nodecoords = thedevices[qubit_dev]['coords']
            if (not schemsize) | (schemsize == 'None'):
                schemsize = thedevices[qubit_dev]['schematicsize']
            numQBs = thedevices[qubit_dev]['numQ']
            canreturn = 1
        else:
            print('Please input a standard device name or "PATH/device.yaml".')
            canreturn = 0
    if canreturn == 1:
        #G = nx.DiGraph()  # directed graph for storing node information
        G = nx.Graph()  # graph for storing node information
        for n in np.arange(numQBs):
            G.add_node(n)
        for thislink in connects:
            G.add_edge(thislink[0],thislink[1])
        if (not schemsize) | (schemsize == 'None'):
            schemsize = [10,10]
        fig = plt.figure(figsize=schemsize)  # figure we are plotting on
        labels = {}  # labels for the nodes. Q + qubit number
        for q in range(numQBs):
            labels[q] = 'Q' + str(q)
        if (not nodecoords) | (nodecoords == 'None'): #python figures out (badly) where to place the nodes in the figure
            nx.draw(G, node_size = min(node_size, 2500), fig=fig, node_color = color,labels = labels, width=1)
        else: #use predefined node positions
            nx.draw(G, pos = nodecoords, node_size = min(node_size, 2500), fig=fig, node_color = color,labels = labels, width=1)


def showlatticecollis(connects, nodecoords, schemsize, numQBs, gates, collisionlist, freqs, color = '#d2d4d2', node_size=2000):
    """
    visual representation of the qubit lattice
    collisions color coded
    
    arguments:
            connects - list of pairwise connections between qubits
            nodecoords - positions for graphing qubits
            schemsize - size of figure [x,y]
            numQBs - number of qubits
            gates - list of pairwise connections between qubits [A,B]. first in each pair is the control
            collisionlist - dictionary of collisions expressed as lists of pairs [A,B] (unordered)  for types 1-4
                            or [A,B,C] (where A = control, B = target, C = spectator) for types 5-7. Keys of dict are 'type1', 'type2' etc
                            Field 'QBsAboveMax' lists all QBs having f > allowable max, 'QBsBelowMin' lists all QBs having f < allowable min, or nan
            freqs - ndarray of frequencies starting with Q0. Empty elements fill with np.nan.
            color - change color of the nodes, a list can also be input for different colors
            node_size - size of the nodes, defaults to 1000, max 2500
    """

    colorhilo = '#faf74d'
    G = nx.DiGraph()  # directed graph for storing node information
    for n in np.arange(numQBs):
        G.add_node(n)
    for thislink in gates:
        G.add_edge(thislink[0],thislink[1])
    if (not schemsize) | (schemsize == 'None'):
        schemsize = [10,10]
    fig = plt.figure(figsize=schemsize)  # figure we are plotting on
    labels = {}  # labels for the nodes. Q + qubit number
    for q in range(numQBs):
        labels[q] = 'Q' + str(q) + '\n' + '{:4.4f}'.format(freqs[q]) #include the freq in the label on the plot
    if (not nodecoords) | (nodecoords == 'None'):
        nx.draw(G, node_size = min(node_size, 2500), fig=fig, node_color = color,labels = labels, width=1)
    else:
        nx.draw(G, pos = nodecoords, node_size = min(node_size, 2500), fig=fig, node_color = color,labels = labels, width=2)
    Ghilo = nx.Graph()  #graph for node information, to draw only the qubits that exceed the absolute high/low bounds!
    for n in collisionlist['QBsAboveMax']:
        Ghilo.add_node(n)
    for n in collisionlist['QBsBelowMin']:
        Ghilo.add_node(n)
    nx.draw(Ghilo, pos = nodecoords, node_size = min(node_size-300, 2200), fig=fig, node_color = colorhilo, labels = labels, width=0)

    colors = ['red', 'blue', 'green', 'purple', 'yellow', 'magenta', 'cyan']  # colors of the error types
    offsets = [-0.2, -0.2, -0.2, -0.2, 0.1, 0.3, 0.5]  # positions of the error relative to center, max 0.5

    if (not nodecoords) | (nodecoords == 'None'):
        print('\nNode positions not defined. Cannot draw collision locations!')
    else:
        for i, coltype in enumerate(['type1', 'type2', 'type3', 'type4']): #draw a single line for each of these types
            for thispair in collisionlist[coltype]:
                x = [nodecoords[thispair[0]][0], nodecoords[thispair[1]][0]]
                y = [nodecoords[thispair[0]][1], nodecoords[thispair[1]][1]]
                if x[0] != x[1]:
                    y = [elt + offsets[i]*node_size/3100 for elt in y]
                elif y[0] != y[1]:
                    x = [elt + offsets[i]*node_size/3100 for elt in x]
                plt.plot(x, y, color = colors[i], zorder=0, lw = 6)
        for i, coltype in enumerate(['type5', 'type6', 'type7']): #for these types, draw a line control-target and control-spect
            for thistrip in collisionlist[coltype]:
                x = [nodecoords[thistrip[0]][0], nodecoords[thistrip[1]][0]]
                y = [nodecoords[thistrip[0]][1], nodecoords[thistrip[1]][1]]
                if x[0] != x[1]:
                    y = [elt + offsets[i+4]*node_size/3100 for elt in y]
                elif y[0] != y[1]:
                    x = [elt + offsets[i+4]*node_size/3100 for elt in x]
                plt.plot(x, y, color = colors[i+4], zorder=0, lw = 6)
                x = [nodecoords[thistrip[0]][0], nodecoords[thistrip[2]][0]]
                y = [nodecoords[thistrip[0]][1], nodecoords[thistrip[2]][1]]
                if x[0] != x[1]:
                    y = [elt + offsets[i+4]*node_size/3100 for elt in y]
                elif y[0] != y[1]:
                    x = [elt + offsets[i+4]*node_size/3100 for elt in x]
                plt.plot(x, y, color = colors[i+4], zorder=0, lw = 6)

    proxies = [Line2D([0, 1], [0, 1], color=clr, lw=5) for clr in colors]  # creates the legend
    proxies.append(Line2D([0, 1], [0, 1], color=colorhilo, lw=30))
    labels = ["%s"%(t) for t in [1,2,3,4,5,6,7]]  # labels for each of the error types
    labels.append('QB f01\nout of\nrange')
    plt.legend( proxies, labels,loc='best', bbox_to_anchor=(0.5, 1.05),  # prints legend
              fancybox=True, shadow=True, ncol=9, title = 'Error Type')


def choose_control_higher(connects, freqs):
    """
    for every connection in the lattice, select the higher frequency as control
   
    arguments -
            connects - list of pairwise connections between qubits
            freqs - ndarray of frequencies starting with Q0. Empty elements fill with np.nan.
    returns -
            gates - list of pairwise connections each ordered as [control,target]
    """

    gates = []
    for pair in connects:
        if (len(freqs.shape) > 1):
            thispairfs = [freqs[pair[0],0], freqs[pair[1],0]]
        else:
            thispairfs = [freqs[pair[0]], freqs[pair[1]]]
        if thispairfs[0] > thispairfs[1]: 
            gates.append([pair[0],pair[1]])
        else:
            gates.append([pair[1],pair[0]])
    gates = [[int(num) for num in pair] for pair in gates]
    return gates


def reversegate(gates, thepair, suppressoutput=0):
    """
    swap the order of the given pair in the list of gates
  
    arguments -
            gates - list of pairwise connections each ordered as [control,target]
            thepair - a pair [C,T] in gates to be replaced with [T,C]. If the pair is not found, error.
            suppressoutput - if = 1, do not print error message.
    returns -
            gates - list of pairwise connections each ordered as [control,target]
    """
    newgates = gates.copy()
    if thepair in gates:
        newgates.remove(thepair)
        newgates.append([thepair[1],thepair[0]])
        if suppressoutput != 1:
            print('Gate '+str(thepair)+' reversed direction!')
    elif suppressoutput != 1:
        print('Gate '+str(thepair)+' not found in gates list!')
    return newgates


def collisionmap_to_collisionlist(collision_map, qfrqs, device, anharm=[], bounds=[], gates=[], custbound=None, custminmax = {}):
    """
    Convert nxnx7 collision map to dictionary of 7 types of collisions. For types 5,6,7, identifies the control or spectator.
   
    arguments -
            collision_map - output of get_collision_7typemap. Where there are n qubits,
                            this is a nxnx7 matrix of binary values. The mxnxk element
                            indicates type k collision between qubit m and n.
            qfrqs - np matrix. Column 0 holds qubit frequencies (GHz) in correct order for this
                    multiQ array type. Column 1 (if included) holds anharmonicities of each qubit (GHz).
            device - device name e.g. '16Q square' as key in standard_devices.yaml, or else
                     path to device.yaml file.
            anharm (optional) - anharmonicity (GHz). Will be ignored if qfrqs includes a column 1 of anharms.
            bounds (optional) - a dict output by collision_bounds() specifying bounds in GHz for each of
                                7 collis types, as well as abs min and max bounds. Will be ignored if qfrqs includes a column 1 of anharms.
            gates (optional) - list of pairwise connections between qubits [A,B]. first in each
                               pair is the control. If not given, will be found based on default assumptions.
            custbound (optional) - Input for custom collision bounds, to be used by collision_bounds() to 
                                   generate custom bounds for each qubit's anharmonicity. 
                                   Use string inputs 'gate_err_1%' and 'gate_err_0.5%' for default values for those thresholds
            custminmax (optional) - 2 value list or array of lower and upper acceptable bounds for QB freq (GHz), otherwise use defaults. 
                                    If included. takes precedence over field 'AbsMinMax' in argument 'bounds'
    returns -
            collisionlist - dictionary of collisions expressed as lists of pairs [A,B] (unordered)  for types 1-4
                            or [A,B,C] (where A = control, B = target, C = spectator) for types 5-7. Keys of dict are 'type1', 'type2' etc
                            Field 'QBsAboveMax' lists all QBs having f > allowable max, 'QBsBelowMin' lists all QBs having f < allowable min, or nann
    """

    if custbound is None:
        custbound = {}
    adj_matrix = qubit_adjacency(device)
    num_qubits = int(np.sqrt(np.size(adj_matrix)))
    if (anharm != []) and (bounds == []) and (qfrqs.size == num_qubits): #if global anharm given, not anharm for each QB
        bounds = collision_bounds(anharm, boundaries=custbound, absminmax = custminmax)
        qfrqs1d = np.array(qfrqs)
        qfrqs = np.zeros([num_qubits,2])
        qfrqs[:,0] = qfrqs1d
        qfrqs[:,1] = anharm
    if gates == []: #if gates list not given, determine the set of ordered gate-pairs
        if qfrqs.size == num_qubits:
            gates = choose_control_higher(ct.adjacency_to_pairwise_coupling(adj_matrix), qfrqs)
        else:
            gates = choose_control_higher(ct.adjacency_to_pairwise_coupling(adj_matrix), qfrqs[:,0])

    collisionlist = {'type1': [], 'type2': [], 'type3': [], 'type4': [], 'type5': [], 'type6': [], 'type7': [], 'QBsAboveMax': [], 'QBsBelowMin': []}

    n = 0
    for nn in np.arange(collision_map.shape[1]):
        for nnn in np.arange(collision_map.shape[1]):
            if collision_map[nn,nnn,n]:
                collisionlist['type1'].append([nn,nnn])
    n = 1
    for nn in np.arange(collision_map.shape[1]):
        for nnn in np.arange(collision_map.shape[1]):
            if collision_map[nn,nnn,n]:
                collisionlist['type2'].append([nn,nnn])
    n = 2
    for nn in np.arange(collision_map.shape[1]):
        for nnn in np.arange(collision_map.shape[1]):
            if collision_map[nn,nnn,n]:
                collisionlist['type3'].append([nn,nnn])
    n = 3
    for nn in np.arange(collision_map.shape[1]):
        for nnn in np.arange(collision_map.shape[1]):
            if collision_map[nn,nnn,n]:
                collisionlist['type4'].append([nn,nnn])
    n = 4
    for nn in np.arange(collision_map.shape[1]):
        for nnn in np.arange(collision_map.shape[1]):
            if collision_map[nn,nnn,n]:
                for q3idx in np.delete(np.arange(num_qubits),[nn,nnn]): #find the control that adjoins both QBs
                    if adj_matrix[nn,q3idx] and adj_matrix[nnn,q3idx] and (([q3idx,nn] in gates) or ([q3idx,nnn] in gates)):
                        collisionlist['type5'].append([q3idx, nn,nnn])
    n = 5 #type 6 collision, ensure that collision is reported as [Control,Target,Spectator]
    for nn in np.arange(collision_map.shape[1]):
        for nnn in np.arange(collision_map.shape[1]):
            if collision_map[nn,nnn,n]:
                for q3idx in np.delete(np.arange(num_qubits),[nn,nnn]): #find the control that adjoins both QBs
                    if adj_matrix[nn,q3idx] and adj_matrix[nnn,q3idx]:
                        if ([q3idx,nn] in gates):
                            collisionlist['type6'].append([q3idx, nn,nnn])
                        elif [q3idx,nnn] in gates:
                            collisionlist['type6'].append([q3idx, nnn,nn])
    n = 6 #type 7 collision must re-check the 2-photon degeneracy condition!!
    for nn in np.arange(collision_map.shape[1]):
        for nnn in np.arange(collision_map.shape[1]):
            if collision_map[nn,nnn,n]:
                for q3idx in np.delete(np.arange(num_qubits),[nn,nnn]):
                    if ([nn,nnn] in gates) and adj_matrix[nn,q3idx]:
                        if bounds != []:
                            thisbounds = bounds
                        else:
                            thisbounds = collision_bounds(qfrqs[nn,1], boundaries=custbound, absminmax = custminmax)
                        if (anharm != []) and (qfrqs.size == num_qubits): #if global anharm given, not anharm for each QB
                            twophotondetun = abs(2*qfrqs[nn] + anharm - qfrqs[nnn] - qfrqs[q3idx])
                        else:
                            twophotondetun = abs(2*qfrqs[nn,0] + qfrqs[nn,1] - qfrqs[nnn,0] - qfrqs[q3idx,0])
                        if (twophotondetun >= thisbounds['Spectator'][0]) and (twophotondetun <= thisbounds['Spectator'][1]):
                            collisionlist['type7'].append([nn,nnn,q3idx])
                    elif ([nnn,nn] in gates) and adj_matrix[nnn,q3idx]:
                        if bounds != []:
                            thisbounds = bounds
                        else:
                            thisbounds = collision_bounds(qfrqs[nnn,1], boundaries=custbound, absminmax = custminmax)
                        if (anharm != []) and (qfrqs.size == num_qubits): #if global anharm given, not anharm for each QB
                            twophotondetun = abs(2*qfrqs[nnn] + anharm - qfrqs[nn] - qfrqs[q3idx])
                        else:
                            twophotondetun = abs(2*qfrqs[nnn,0] + qfrqs[nnn,1] - qfrqs[nn,0] - qfrqs[q3idx,0])
                        if (twophotondetun >= thisbounds['Spectator'][0]) and (twophotondetun <= thisbounds['Spectator'][1]):
                            collisionlist['type7'].append([nnn,nn,q3idx])
    if qfrqs.size != num_qubits:
        listfrqs = qfrqs[:,0]
    else:
        listfrqs = qfrqs
    if bounds == []:
        bounds = collision_bounds(-0.34)
    if custminmax != {}:                #if this argument was given it takes precedence
        theminmax = custminmax
    elif ('AbsMinMax' in bounds.keys()) and (bounds['AbsMinMax'] != {}).all():  #otherwise look for abs min and max freqs in argument 'bounds' 
        theminmax = bounds['AbsMinMax']
    else:                               #otherwise use default abs min and max freqs
        bounds = collision_bounds(-0.34)
        theminmax = bounds['AbsMinMax']
    for nn in np.arange(num_qubits):
        if listfrqs[nn] > theminmax[1]:
            collisionlist['QBsAboveMax'].append(nn)
        elif (listfrqs[nn] < theminmax[0] or np.isnan(listfrqs[nn])):
            collisionlist['QBsBelowMin'].append(nn)

    return collisionlist


def list_collisions_fromlist(collisionlist): 
    """
   
    Arguments
            collisionlist - dictionary of collisions expressed as lists of pairs [A,B] (unordered)  for types 1-4
                            or [A,B,C] (where A = control, B = target, C = spectator) for types 5-7. Keys of dict are 'type1', 'type2' etc
                            Field 'QBsAboveMax' lists all QBs having f > allowable max, 'QBsBelowMin' lists all QBs having f < allowable min, or nan
                            Outputted by collisionmap_to_collisionlist()
    """
    thistot = 0
    for n in np.arange(7):
        thiskey = 'type'+str(n+1)
        thisnum = len(collisionlist[thiskey])
        if n in [4,5,6] and thisnum > 0:
            suffix = '. Format [Contr,Target,Spec].'
        else:
            suffix = '.'
        print('Type '+str(n+1)+':  '+str(thisnum)+' collisions.\t'+str(collisionlist[thiskey])+suffix)
        thistot += thisnum
    print('Total: '+str(thistot)+' collisions.')


def reversegates_fixcollis(qfrqs, device, anharm, bounds, gates, custbounds=None):
    """
   
   
    Arguments.
    qfrqs:     np matrix. Column 0 holds qubit frequencies (GHz) in correct order for this multiQ array type
               Column 1 (if included) holds anharmonicities of each qubit (GHz).
    device:    'NTPP7', '17Q SurfCode SkewSym', '16Q square' or other string
    anharm:    anharmonicity (GHz). Will be ignored if qfrqs includes a column 1 of anharms.
    bounds:    a dict output by collision_bounds() specifying bounds in GHz for each of 7 collis types.
               Will be ignored if qfrqs includes a column 1 of anharms.
    gates:     list of pairwise connections between qubits [A,B]. first in each pair is the control.
               Should include ALL nearest-neighbor pairs in the lattice. 
    custbounds (optional): Input for custom collision bounds, to be used by collision_bounds() to 
                           generate custom bounds for each qubit's anharmonicity.
                           Use string inputs 'gate_err_1%' and 'gate_err_0.5%' for default values for those thresholds.
               
    Returns
    newgates:  list of gates for qubits in the device. any gate in input 'gates' that can be
               reversed in order to reduce the number of collisions, is reversed. 
               If none can be, then newgates = gates.
    """

    if custbounds is None:
        custbounds = {}
    newgates = gates.copy()
   
    #reduce type 5 collisions if possible
    collmap = get_collision_7typemap(qfrqs, device, anharm, bounds, newgates, custbound=custbounds)
    colllist0 = collisionmap_to_collisionlist(collmap, qfrqs, device, anharm=anharm, bounds=bounds, gates=newgates, custbound=custbounds)
    for thiscol in colllist0['type5']:
        
        #count number of collisions as-is
        collmap = get_collision_7typemap(qfrqs, device, anharm, bounds, newgates, custbound=custbounds)
        collnums = np.zeros(7)
        for n in np.arange(7):
            collnums[n] = np.sum(collmap[:,:,n])
            
        #control, target, spectator
        thisC = thiscol[0]
        thisT = thiscol[1]
        thisS = thiscol[2]
        
        #try three possibilities of flipping the gate direction
        gatesflip0 = reversegate(newgates, [thisC,thisT], suppressoutput=1) #reverse first gate
        if [thisC,thisS] in newgates:
            gatesflip1 = reversegate(newgates, [thisC,thisS], suppressoutput=1) #reverse 2nd gate
        elif [thisS,thisC] in newgates:
            gatesflip1 = reversegate(newgates, [thisS,thisC], suppressoutput=1) #reverse 2nd gate           
        gatesflipboth = reversegate(gatesflip1, [thisC,thisT], suppressoutput=1) #reverse both gates
        
        #Calculate collisions for three alternate directions. 
        collmapflip0 = get_collision_7typemap(qfrqs, device, anharm, bounds, gatesflip0, custbound=custbounds)
        collflip0nums = np.zeros(7)
        for n in np.arange(7):
            collflip0nums[n] = np.sum(collmapflip0[:,:,n])
        collmapflip1 = get_collision_7typemap(qfrqs, device, anharm, bounds, gatesflip1, custbound=custbounds)
        collflip1nums = np.zeros(7)
        for n in np.arange(7):
            collflip1nums[n] = np.sum(collmapflip1[:,:,n])
        collmapflipboth = get_collision_7typemap(qfrqs, device, anharm, bounds, gatesflipboth, custbound=custbounds)
        collflipbothnums = np.zeros(7)
        for n in np.arange(7):
            collflipbothnums[n] = np.sum(collmapflipboth[:,:,n])
            
        #must have no greater number of types 1,2,3,4,6,7 than previous        
        #choose arrangement with fewest number of type 5
        #List of four gate arrangements, corresponding list of four type-5 collision numbers
        gatesopts = []
        gatesopts.append(newgates)
        gatesopts.append(gatesflip0)
        gatesopts.append(gatesflip1)
        gatesopts.append(gatesflipboth)
        collnumstype5 = [collnums[4], collflip0nums[4], collflip1nums[4], collflipbothnums[4]]
        #Consider only gate arrangements that have no greater number of types 1,2,3,4,6,7 than previous
        #Among these, select the gate arrangement corresponding to the lowest number of type 5 collisions
        if (min(np.greater_equal(collnums,collflip0nums)) == 1) & (min(np.greater_equal(collnums,collflip1nums)) == 1) & (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype5
        elif (min(np.greater_equal(collnums,collflip0nums)) == 1) & (min(np.greater_equal(collnums,collflip1nums)) == 1):
            collnumstype5[3] = np.nan
        elif (min(np.greater_equal(collnums,collflip0nums)) == 1) & (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype5[2] = np.nan
        elif (min(np.greater_equal(collnums,collflip1nums)) == 1) & (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype5[1] = np.nan
        elif (min(np.greater_equal(collnums,collflip0nums)) == 1):
            collnumstype5[3] = collnumstype5[2] = np.nan
        elif (min(np.greater_equal(collnums,collflip1nums)) == 1):
            collnumstype5[3] = collnumstype5[1] = np.nan
        elif (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype5[2] = collnumstype5[1] = np.nan
        else:
            collnumstype5[3] = collnumstype5[2] = collnumstype5[1] = np.nan
        newgates = gatesopts[np.argsort(collnumstype5)[0]].copy() #select the gate arrangement corresponding to the lowest number of type 5 collisions
        
    #reduce type 6 collisions if possible
    collmap = get_collision_7typemap(qfrqs, device, anharm, bounds, newgates, custbound=custbounds)
    colllist0 = collisionmap_to_collisionlist(collmap, qfrqs, device, anharm=anharm, bounds=bounds, gates=newgates, custbound=custbounds)
    for thiscol in colllist0['type6']:
        
        #count number of collisions as-is
        collmap = get_collision_7typemap(qfrqs, device, anharm, bounds, newgates, custbound=custbounds)
        collnums = np.zeros(7)
        for n in np.arange(7):
            collnums[n] = np.sum(collmap[:,:,n])
            
        #control, target, spectator
        thisC = thiscol[0]
        thisT = thiscol[1]
        thisS = thiscol[2]
        
        #try three possibilities of flipping the gate direction
        gatesflip0 = reversegate(newgates, [thisC,thisT], suppressoutput=1) #reverse first gate
        if [thisC,thisS] in newgates:
            gatesflip1 = reversegate(newgates, [thisC,thisS], suppressoutput=1) #reverse 2nd gate
        elif [thisS,thisC] in newgates:
            gatesflip1 = reversegate(newgates, [thisS,thisC], suppressoutput=1) #reverse 2nd gate           
        gatesflipboth = reversegate(gatesflip1, [thisC,thisT], suppressoutput=1) #reverse both gates
        
        #Calculate collisions for three alternate directions. 
        collmapflip0 = get_collision_7typemap(qfrqs, device, anharm, bounds, gatesflip0, custbound=custbounds)
        collflip0nums = np.zeros(7)
        for n in np.arange(7):
            collflip0nums[n] = np.sum(collmapflip0[:,:,n])
        collmapflip1 = get_collision_7typemap(qfrqs, device, anharm, bounds, gatesflip1, custbound=custbounds)
        collflip1nums = np.zeros(7)
        for n in np.arange(7):
            collflip1nums[n] = np.sum(collmapflip1[:,:,n])
        collmapflipboth = get_collision_7typemap(qfrqs, device, anharm, bounds, gatesflipboth, custbound=custbounds)
        collflipbothnums = np.zeros(7)
        for n in np.arange(7):
            collflipbothnums[n] = np.sum(collmapflipboth[:,:,n])
        
        #must have no greater number of types 1,2,3,4,5,7 than previous        
        #choose arrangement with fewest number of type 6
        #List of four gate arrangements, corresponding list of four type-6 collision numbers
        gatesopts = []
        gatesopts.append(newgates)
        gatesopts.append(gatesflip0)
        gatesopts.append(gatesflip1)
        gatesopts.append(gatesflipboth)
        collnumstype6 = [collnums[5], collflip0nums[5], collflip1nums[5], collflipbothnums[5]]
        #Consider only gate arrangements that have no greater number of types 1,2,3,4,5,7 than previous
        #Among these, select the gate arrangement corresponding to the lowest number of type 6 collisions
        if (min(np.greater_equal(collnums,collflip0nums)) == 1) & (min(np.greater_equal(collnums,collflip1nums)) == 1) & (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype6
        elif (min(np.greater_equal(collnums,collflip0nums)) == 1) & (min(np.greater_equal(collnums,collflip1nums)) == 1):
            collnumstype6[3] = np.nan
        elif (min(np.greater_equal(collnums,collflip0nums)) == 1) & (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype6[2] = np.nan
        elif (min(np.greater_equal(collnums,collflip1nums)) == 1) & (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype6[1] = np.nan
        elif (min(np.greater_equal(collnums,collflip0nums)) == 1):
            collnumstype6[3] = collnumstype6[2] = np.nan
        elif (min(np.greater_equal(collnums,collflip1nums)) == 1):
            collnumstype6[3] = collnumstype6[1] = np.nan
        elif (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype6[2] = collnumstype6[1] = np.nan
        else:
            collnumstype6[3] = collnumstype6[2] = collnumstype6[1] = np.nan
        newgates = gatesopts[np.argsort(collnumstype6)[0]].copy() #select the gate arrangement corresponding to the lowest number of type 6 collisions

    #reduce type 7 collisions if possible
    collmap = get_collision_7typemap(qfrqs, device, anharm, bounds, newgates, custbound=custbounds)
    colllist0 = collisionmap_to_collisionlist(collmap, qfrqs, device, anharm=anharm, bounds=bounds, gates=newgates, custbound=custbounds)
    for thiscol in colllist0['type7']:
        
        #count number of collisions as-is
        collmap = get_collision_7typemap(qfrqs, device, anharm, bounds, newgates, custbound=custbounds)
        collnums = np.zeros(7)
        for n in np.arange(7):
            collnums[n] = np.sum(collmap[:,:,n])
            
        #control, target, spectator
        thisC = thiscol[0]
        thisT = thiscol[1]
        thisS = thiscol[2]
        
        #try three possibilities of flipping the gate direction
        gatesflip0 = reversegate(newgates, [thisC,thisT], suppressoutput=1) #reverse first gate
        if [thisC,thisS] in newgates:
            gatesflip1 = reversegate(newgates, [thisC,thisS], suppressoutput=1) #reverse 2nd gate
        elif [thisS,thisC] in newgates:
            gatesflip1 = reversegate(newgates, [thisS,thisC], suppressoutput=1) #reverse 2nd gate           
        gatesflipboth = reversegate(gatesflip1, [thisC,thisT], suppressoutput=1) #reverse both gates
        
        #Calculate collisions for three alternate directions. 
        collmapflip0 = get_collision_7typemap(qfrqs, device, anharm, bounds, gatesflip0, custbound=custbounds)
        collflip0nums = np.zeros(7)
        for n in np.arange(7):
            collflip0nums[n] = np.sum(collmapflip0[:,:,n])
        collmapflip1 = get_collision_7typemap(qfrqs, device, anharm, bounds, gatesflip1, custbound=custbounds)
        collflip1nums = np.zeros(7)
        for n in np.arange(7):
            collflip1nums[n] = np.sum(collmapflip1[:,:,n])
        collmapflipboth = get_collision_7typemap(qfrqs, device, anharm, bounds, gatesflipboth, custbound=custbounds)
        collflipbothnums = np.zeros(7)
        for n in np.arange(7):
            collflipbothnums[n] = np.sum(collmapflipboth[:,:,n])
            
        #must have no greater number of types 1,2,3,4,5,6 than previous        
        #choose arrangement with fewest number of type 6
        #List of four gate arrangements, corresponding list of four type-7 collision numbers
        gatesopts = []
        gatesopts.append(newgates)
        gatesopts.append(gatesflip0)
        gatesopts.append(gatesflip1)
        gatesopts.append(gatesflipboth)
        collnumstype7 = [collnums[6], collflip0nums[6], collflip1nums[6], collflipbothnums[6]]
        #Consider only gate arrangements that have no greater number of types 1,2,3,4,5,7 than previous
        #Among these, select the gate arrangement corresponding to the lowest number of type 7 collisions
        if (min(np.greater_equal(collnums,collflip0nums)) == 1) & (min(np.greater_equal(collnums,collflip1nums)) == 1) & (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype7
        elif (min(np.greater_equal(collnums,collflip0nums)) == 1) & (min(np.greater_equal(collnums,collflip1nums)) == 1):
            collnumstype7[3] = np.nan
        elif (min(np.greater_equal(collnums,collflip0nums)) == 1) & (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype7[2] = np.nan
        elif (min(np.greater_equal(collnums,collflip1nums)) == 1) & (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype7[1] = np.nan
        elif (min(np.greater_equal(collnums,collflip0nums)) == 1):
            collnumstype7[3] = collnumstype7[2] = np.nan
        elif (min(np.greater_equal(collnums,collflip1nums)) == 1):
            collnumstype7[3] = collnumstype7[1] = np.nan
        elif (min(np.greater_equal(collnums,collflipbothnums)) == 1):
            collnumstype7[2] = collnumstype7[1] = np.nan
        else:
            collnumstype7[3] = collnumstype7[2] = collnumstype7[1] = np.nan
        newgates = gatesopts[np.argsort(collnumstype7)[0]].copy() #select the gate arrangement corresponding to the lowest number of type 7 collisions
        
        #convert all gate numbers to int (currently some are being left as a numpy type, which breaks yaml writeout)
    newgates = [[int(num) for num in gate] for gate in newgates]
    return newgates 


def list_QBsHiLo(collisionlist, bounds):
    """
    
    Arguments
            collisionlist - dictionary of collisions expressed as lists of pairs [A,B] (unordered)  for types 1-4
                            or [A,B,C] (where A = control, B = target, C = spectator) for types 5-7. Keys of dict are 'type1', 'type2' etc
                            Field 'QBsAboveMax' lists all QBs having f > allowable max, 'QBsBelowMin' lists all QBs having f < allowable min, or nan
                            Outputted by collisionmap_to_collisionlist()
            bounds        - a dict output by collision_bounds() specifying bounds in GHz for each of
                            7 collis types, as well as 'AbsMinMax' which should have been used to find 'QBsAboveMax' and 'QBsBelowMin' in collisionlist
    """
    print('\nQubits exceeding absolute frequency bounds:')
    print('  Qubits having f01 below '+str(bounds['AbsMinMax'][0])+' GHz, or blank: '+str(collisionlist['QBsBelowMin']))
    print('  Qubits having f01 above '+str(bounds['AbsMinMax'][1])+' GHz: '+str(collisionlist['QBsAboveMax']))


def get_collision_extendedmap(qfrqs, device, anharm, bounds, gates=[], custbound=None):
    """
    
    Arguments.
        qfrqs:     np matrix. Column 0 holds qubit frequencies (GHz) in correct order for this multiQ array type
                   Column 1 (if included) holds anharmonicities of each qubit (GHz).
        device:    'NTPP7', '17Q SurfCode SkewSym', '16Q square' or other string
        anharm:    anharmonicity (GHz). Either enter value here or in column 1 of anharms (latter has precedence). Else count will be wrong!
        bounds:    a dict output by collision_bounds() specifying bounds in GHz for each of 7 collis types.
                   Will be ignored if qfrqs includes a column 1 of anharms.
        gates:     list of pairwise connections between qubits [A,B]. first in each pair is the control.
                   Should include ALL nearest-neighbor pairs in the lattice. If omitted, function will assume
                   highest-freq of each pair is control.
        custbound: Input for custom collision bounds, to be used by collision_bounds() to generate custom bounds for each qubit's
                   anharmonicity. Use string inputs 'gate_err_1%' and 'gate_err_0.5%' for default values for those thresholds.

    Returns
       collision_map: where there are n qubits, this is a nxnx13 matrix of binary values.
                      The mxnxk element indicates type k collision between qubit m and n
    """
    if custbound is None:
        custbound = {}
    []

def collisionlist_extendedtype(qfrqs, device, gates=[], custbound=None, custminmax = {}):
    """
    Finds dictionary of 13 types of collisions. For types involving 3 qubits, identifies the control or spectator.
   
    arguments -
            qfrqs - np matrix. Column 0 holds qubit frequencies (GHz) in correct order for this
                    multiQ array type. Column 1 holds anharmonicities of each qubit (GHz).
            device - device name e.g. '16Q square' as key in standard_devices.yaml, or else
                     path to device.yaml file.
            gates (optional) - list of pairwise connections between qubits [A,B]. first in each
                               pair is the control. If not given, will be found based on default assumptions.
            custbound (optional) - Input for custom collision bounds, to be used by collision_bounds() to generate custom bounds for each qubit's
                                   anharmonicity. Use string inputs 'gate_err_1%' and 'gate_err_0.5%' for default values for those thresholds.
            custminmax (optional) - 2 value list or array of lower and upper acceptable bounds for QB freq (GHz), otherwise use defaults. 
                                    If included. takes precedence over field 'AbsMinMax' in argument 'bounds'
    returns -
            collisionlist - dictionary of collisions expressed as lists of pairs [A,B] (unordered)  for 2-qubit types, 
                            or [A,B,C] (where A = control, B = target, C = spectator) for 3-qubit types. Keys of dict are 'type1', 'type2' etc
                            Field 'QBsAboveMax' lists all QBs having f > allowable max, 'QBsBelowMin' lists all QBs having f < allowable min, or nan
    """
#MAKE SURE THAT IF ALL ANHARMS ARE IDENTICAL IT CALCS SINGLE BOUNDS TO SAVE TIME!!!
    if custbound is None:
        custbound = {}
    []
    
    
def collisionlist_to_extendedmap(collisionlist):
    """
    Converts dictionary of 13 types of collisions to a 3 dimensional binary matrix indicating collisions.
   
   
    arguments -
            collisionlist - dictionary of collisions expressed as lists of pairs [A,B] (unordered)  for 2-qubit types, 
                            or [A,B,C] (where A = control, B = target, C = spectator) for 3-qubit types. Keys of dict are 'type1', 'type2' etc
                            Field 'QBsAboveMax' lists all QBs having f > allowable max, 'QBsBelowMin' lists all QBs having f < allowable min, or nan
    returns -
       collision_map: where there are n qubits, this is a nxnx13 matrix of binary values.
                      The mxnxk element indicates type k collision between qubit m and n
    """
    []

    
def showlattice_freqs(qubit_dev, freqs, color = '#d2d4d2', node_size=1000, Qlabel=True, schemsize='None'):
    """
    visual representation of the qubit lattice with freqs
    
    arguments:
            qubit_dev - 'NTPP7', '17Q SurfCode SkewSym', '16Q square' or other string, or else path to device.yaml
            freqs - ndarray of frequencies starting with Q0. Empty elements fill with np.nan 
            color - change color of the nodes, a list can also be input for different colors
            node_size - size of the nodes, defaults to 1000, max 2500
            text - if True, runs list_collisions() to add the text description of the collisions
            schemsize - size of figure [x,y]
    """

    if 'device.yaml' in qubit_dev: #load info from yaml file!!
        connects = ct.get_coupling_map(qubit_dev)
        nodecoords = ct.get_node_coords(qubit_dev)
        canreturn = 1
        schemsize=[10,10]
        numQBs = max(np.ravel(np.array(connects))) + 1
    else: #load info from standard device list
        thedevices = load_standard_devices()
        thedevnames = names_standard_devices(0)
        if qubit_dev in thedevnames:
            connects = thedevices[qubit_dev]['connections']
            nodecoords = thedevices[qubit_dev]['coords']
            if (not schemsize) | (schemsize == 'None'):
                schemsize = thedevices[qubit_dev]['schematicsize']
            numQBs = thedevices[qubit_dev]['numQ']
            canreturn = 1
        else:
            print('Please input a standard device name or "PATH/device.yaml".')
            canreturn = 0
    if canreturn == 1:
        G = nx.Graph()  # graph for storing node information
        for n in np.arange(numQBs):
            G.add_node(n)
        for thislink in connects:
            G.add_edge(thislink[0],thislink[1])
        if (not schemsize) | (schemsize == 'None'):
            schemsize = [10,10]
        fig = plt.figure(figsize=schemsize)  # figure we are plotting on 
        labels = {}  # labels for the nodes. Q + qubit number
        for q in range(numQBs):
            if Qlabel==True:
                labels[q] = 'Q' + str(q) + '\n' + '{:4.4f}'.format(freqs[q]) #include the freq in the label on the plot
            else:
                #labels[q] = '{:4.4f}'.format(freqs[q]) #include freq but no QB label on the plot
                #INTEGER LABELING: 
                labels[q] = str(int(freqs[q]))
        if (not nodecoords) | (nodecoords == 'None'): #python figures out (badly) where to place the nodes in the figure
            nx.draw(G, node_size = min(node_size, 2500), fig=fig, node_color = color,labels = labels, width=1)
        else: #use predefined node positions (add argument font_size=30 for larger text)
            nx.draw(G, pos = nodecoords, node_size = min(node_size, 2500), fig=fig, node_color = color,labels = labels, width=6, font_size=30)



