#make frequency collision script




#first load countcollision module
import countcollisions as cc
import coupling_tools as cpl
import numpy as np


#define functions to detect collisions

#######################here we define the functions to detect frequency collisions



def extract_freq_data(backend):
    # find out how many qubits there are
    num_qubits = backend.configuration().num_qubits

    # get frequencies and anharmonicities
    data_freq = []
    for ii in range(num_qubits):
        qfreq = backend.properties().qubit_property(ii)['frequency'][0]
        anharm  = backend.properties().qubit_property(ii)['anharmonicity'][0]
        data_freq.append([str(float(qfreq)/1e9), str(float(anharm)/1e9)]) # f01's and anharm's in GHz
    return np.asfarray(data_freq)


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

def qubit_adjacency(backend):
    
#qubit_dev: name of device or path and filename of 'device.yaml' file
#devicedef: dictionary defining device, typically loaded using cc.load_standard_devices(). Should include 
#           fields 'numQ' and 'fpatterns'. should correspond to definition of 'device'

    connects = backend.configuration().coupling_map

    numQBs = backend.configuration().num_qubits

    return cpl.pairwise_coupling_to_adjacency(connects,numQBs)

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


def get_collision_7typemap(qfrqs, backend, anharm, bounds, gates=[], custbound=None, type8plus = 'n'):
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
    adj_matrix = qubit_adjacency(backend)
    adj_squared = np.dot(adj_matrix, adj_matrix)
    num_qubits = int(np.sqrt(np.size(adj_matrix)))
    

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


#get collision dict


def cr_to_str(cr):
    return f'{cr[0]}_{cr[1]}'






        
        
def collision_dict(backend):
    """
   
    """
    coupling_map = backend.configuration().coupling_map
    
    freq_data = extract_freq_data(backend)
    
    f01s = np.array(freq_data[:,0], copy=True)
    
    
    # Get all qubit pairs
    all_pairs = []
    for pair in backend.configuration().coupling_map:
        if pair and pair[::-1] not in all_pairs:
            all_pairs.append(pair)
            
    # Order pairs so that control is first and target is second element of list
    ordered_pairs = []
    for pair in all_pairs:
        cx_gate_duration = backend.defaults().instruction_schedule_map.get('cx', pair).duration
        cx_gate_reversed_duration = backend.defaults().instruction_schedule_map.get('cx', pair[::-1]).duration
        if cx_gate_duration < cx_gate_reversed_duration:
            ordered_pairs.append(pair)
        else:
            ordered_pairs.append(pair[::-1])
    
    
    
    collision_dict = list_collisions(get_collision_7typemap(freq_data, backend, [], [], gates=ordered_pairs))
    return(collision_dict)





        

def best_FC_mapping(scores,collision_dict,percentage,weight=1):
    """
    Arguments:
    scores: is return of mm.evaluate_layouts; contains mappings with scores
    collision_dict: return of get_collision_7typemap; contains information about qubits affected by FC's
    percentage: percentage that subset of mm mappings that are taken
    weight: dictionary of same "shape" as collision dict; gives weight of each FC
    
    function will give back mapping with least FC-participation within a range of percentage (of fidelity) away from the max mm-fidelity mapping
    """
    all_mappings=[]
    scorelist=[]
    import copy
    weights0=copy.deepcopy(collision_dict)
    for key in weights0:
        for i in range(len(weights0[key])):
            weights0[key][i]=1
    if weight ==1:
        weight=weights0
     
    for i in range(len(scores)):
        all_mappings.append(scores[i][0])
        scorelist.append(scores[i][1])
    fidelity=1-np.array(scorelist)
    viable_mappings=[]
    i=0
    while fidelity[i]>fidelity[0]-percentage and i<len(all_mappings):
        viable_mappings.append(all_mappings[i])
        i+=1
   #now get collision count for each mapping
    collision_count=[]
    for mapping in viable_mappings:
        aux_count=0
        for key in collision_dict:
            list_qubitpairs=collision_dict[key]
            for qubitpair in list_qubitpairs:
                if set(qubitpair).intersection(set(mapping))!=set():
                    aux_count+=1*weight[key][list_qubitpairs.index(qubitpair)]
        collision_count.append(aux_count)
                    
                    
    #now we have the full collision count
    
    return(viable_mappings[np.argmin(collision_count)])


def FC_score(mapping,collision_dict,weight=1):
    """
    function computes the FC score cost function
    will be useful to detect if introduction of weights/ FC method is useful
    """
    import copy
    weights0=copy.deepcopy(collision_dict)
    for key in weights0:
        for i in range(len(weights0[key])):
            weights0[key][i]=1
    if weight ==1:
        weight=weights0
    collision_score=0
    for key in collision_dict:
        list_qubitpairs=collision_dict[key]
        for qubitpair in list_qubitpairs:
            if set(qubitpair).intersection(set(mapping))!=set():
                collision_score+=1*weight[key][list_qubitpairs.index(qubitpair)]
    return(collision_score)
    
    
    
    
#define ver 2 of the FC_score
#this version tries to take into account more the actual connectivity, does not just take intersections

def FC_score_ver2(mapping,collision_dict,weight=1):
    """
    function computes the FC score cost function in version 2
    will be useful to detect if introduction of weights/ FC method is useful
    """
    import copy
    weights0=copy.deepcopy(collision_dict)
    for key in weights0:
        for i in range(len(weights0[key])):
            weights0[key][i]=1
    if weight ==1:
        weight=weights0
    
    
   
    score=0   #we will add up the errors here
    for key in collision_dict:
        for collision in collision_dict[key]:
            test=True
            for qubit in collision:
                if qubit not in mapping:
                    test=False
            if test:
                score+=weight[key][collision_dict[key].index(collision)]
    return(score)
    
    
    
    
    
    
    
    
 
    
#define function for thermal mapping

def thermal_mapping(mappings_array,cost_array,N,T=1):
    """
    Arguments:
    mappings_array: array containing different mappings
    cost_array: same shape as mappings_array, contains cost for each of the mappings
    N:total amount of mappings (approximate, upper limit)
    T: "Temperature", optional
    
    returns mappings_final: array containing each mapping the corresponding time, len(mappings_final)<=N and hopefully len(mappings_final) \approx N

    """
    if len(mappings_array)!=len(cost_array):
        raise ValueError("arrys must be same length")
        
    #define partition function
    Z=0
    for cost_i in cost_array:
        Z+=np.exp(-cost_i/T)
        
    #next get array containing number of each mapping
    n=[]
    for i in range(len(mappings_array)):
        n.append(int(N/Z*(np.exp(-cost_array[i]/T))))
    mappings_final=[]
    for i in range(len(mappings_array)):
        number=n[i]
        for j in range(number):
            mappings_final.append(mappings_array[i])
            j+=1
        i+=1
    return(mappings_final)




#define also function to give only the "thermal integers" by which each mapping is weighed

def thermal_integers(cost_array,N,T=1):
    """
    Arguments:
    mappings_array: array containing different mappings
    cost_array: same shape as mappings_array, contains cost for each of the mappings
    N:total amount of mappings (approximate, upper limit)
    T: "Temperature", optional
    
    returns integers n_i which are N*rho_i=N/Z *exp(-cost/T)

    """
   # if len(mappings_array)!=len(cost_array):
    #    raise ValueError("arrys must be same length")
        
    #define partition function
    Z=0
    for cost_i in cost_array:
        Z+=np.exp(-cost_i/T)
        
    #next get array containing number of each mapping
    n=[]
    for i in range(len(cost_array)):
        n.append(int(N/Z*(np.exp(-cost_array[i]/T))))
    
    return(n)

def FC_score_filter(mapping, collision_dict,weight=1, threshhold=4):
    """
    function returns  False if a specific mapping has an FC score above the threshhold and returns True if it is below
    
    Arguments:
    mapping: array of used qubits for mapping [q_0,q_1,....,q-n]
    collision_dict: return of collision dict function
    weight: possible weight array
    threshhold: threshhold of when to cut out mappings
    
    a priori values if weight=1 yields that eacg collision is weighted the same
    
    threshhold=4 cuts mapping out once it experiences more than 4 collisions, if we put a non-trivial weight array into we have to adjust the threshhold
    """
    
    #if we count just the number of collisions, we have to adjust the threshold
    score=FC_score(mapping,collision_dict,weight)
    if score <= threshhold:
        return(True)
    else:
        return(False)
    
    
    
    
#finally try to use a "full characterization score" based on the randomized benchmarking ansatz by Fraunhofer/Andreas


import mapomatic as mm
def full_char_score(circ,mapping,backend,crosstalk_dicts):
    fid0=1-mm.layouts.default_cost(circ,[mapping],backend)[0][1]
    #now add factors based on crosstalk dicts
    dict1=crosstalk_dicts[0]
    dict2=crosstalk_dicts[1]
    for q0 in mapping:
        for q1 in mapping:
            if str([q0, q1]) in dict1.keys():
                for q2 in mapping:
                    if str([q2]) in dict1[str([q0, q1])]:
                        fid0*=1-dict1[str([q0, q1])][str([q2])][0]
                                      
    for q0 in mapping:
        for q1 in mapping:
            if str([q0, q1]) in dict2.keys():
                for q2 in mapping:
                    if str([q2]) in dict2[str([q0, q1])]:
                        fid0*=1-dict2[str([q0, q1])][str([q2])][0]
                                      
    return(1-fid0)
    
    