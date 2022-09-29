"""
Tools for converting between coupling maps and
matrices
"""

import yaml
import numpy as np

__author__=''
__date__ = ''

def get_coupling_map(deviceyaml):
    with open(deviceyaml) as dev:
        data = yaml.safe_load(dev)
    return data['connections']

def get_node_coords(deviceyaml):
    with open(deviceyaml) as dev:
        data = yaml.safe_load(dev)
    return data['coords']

def get_gates(deviceyaml):
    with open(deviceyaml) as dev:
        data = yaml.safe_load(dev)
    return data['gates']

def pairwise_coupling_to_adjacency(coupling_map, *argv): # convert from coupling map to adjacency matrix
    num_qubits = max(np.ravel(np.array(coupling_map))) + 1 # qubit numbering starts at zero
    try: #try to look for 2nd argument which should be the number of qubits
        thelen = argv[0]
        if thelen > num_qubits:
            num_qubits = thelen #in case the adjacency matrix has no nonzero elements in its last few rows & cols     
    except:
        num_qubits = num_qubits    
    adj_matrix = np.zeros((num_qubits, num_qubits))
    for pair in coupling_map:
        adj_matrix[pair[0]][pair[1]] = 1
        adj_matrix[pair[1]][pair[0]] = 1
    return adj_matrix

def adjacency_to_pairwise_coupling(adj_matrix): # convert from adjacency matrix to coupling map
    num_qubits = np.shape(adj_matrix)[0]
    coupling_map = []
    for ii in range(num_qubits):
        for jj in range(ii+1, num_qubits): # only need upper half - this keeps the usual ordering
            if adj_matrix[ii][jj]:
                coupling_map.append([ii, jj])
    return coupling_map

def heavy_coupling_to_adjacency(heavy_coupling_map):
    num_qubits = max(heavy_coupling_map) + 1 # qubit numbering starts at zero
    adj_matrix = np.zeros((num_qubits, num_qubits))
    for ii in heavy_coupling_map:
        for jj in heavy_coupling_map[ii]:
            adj_matrix[ii][jj] = 1
    return adj_matrix

def adjacency_to_heavy_coupling(adj_matrix):
    num_qubits = np.shape(adj_matrix)[0]
    heavy_coupling_map = {}
    for ii in range(num_qubits):
        qkey = ii
        qcoupled = []
        for jj in range(num_qubits): # heavy coupling is over-specified
            if adj_matrix[ii][jj]:
                qcoupled.append(jj)
        heavy_coupling_map.update({qkey: qcoupled})
    return heavy_coupling_map

def heavy_to_pairwise_coupling(heavy_coupling_map):
    adj_matrix = heavy_coupling_to_adjacency(heavy_coupling_map)
    return adjacency_to_pairwise_coupling(adj_matrix)

def pairwise_to_heavy_coupling(pairwise_coupling_map):
    adj_matrix = pairwise_coupling_to_adjacency(pairwise_coupling_map)
    return adjacency_to_heavy_coupling(adj_matrix)
