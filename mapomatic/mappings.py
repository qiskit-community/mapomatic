# This code is part of Mapomatic.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# The exact_mappings routine is more or less a direct port of the VF2Layout
# pass code from Qiskit with minor modifications to simplify and return a
# different format.  The Qiskit code is under the following license:

# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Circuit manipulation tools"""
import random
import numpy as np

from retworkx import PyGraph, PyDiGraph, vf2_mapping
from qiskit.converters import circuit_to_dag
from qiskit.transpiler.coupling import CouplingMap


def exact_mappings(circ, cmap, strict_direction=False, call_limit=10000):
    """Find the exact mappings for a circuit onto a given topology (coupling map)

    Parameters:
        circ (QuantumCircuit): Input quantum circuit
        cmap (list): Coupling map
        strict_direction (bool): Use directed coupling
        call_limit (int): Max number of calls to VF2 mapper

    Returns:
        list: Found mappings.
    """
    dag = circuit_to_dag(circ)
    qubits = dag.qubits
    qubit_indices = {qubit: index for index, qubit in enumerate(qubits)}

    interactions = []
    for node in dag.op_nodes(include_directives=False):
        len_args = len(node.qargs)
        if len_args == 2:
            interactions.append((qubit_indices[node.qargs[0]], qubit_indices[node.qargs[1]]))
    cmap = CouplingMap(cmap)
    if strict_direction:
        cm_graph = cmap.graph
        im_graph = PyDiGraph(multigraph=False)
    else:
        cm_graph = cmap.graph.to_undirected()
        im_graph = PyGraph(multigraph=False)

    cm_nodes = list(cm_graph.node_indexes())
    seed = -1
    if seed != -1:
        random.Random(seed).shuffle(cm_nodes)
        shuffled_cm_graph = type(cm_graph)()
        shuffled_cm_graph.add_nodes_from(cm_nodes)
        new_edges = [(cm_nodes[edge[0]], cm_nodes[edge[1]]) for edge in cm_graph.edge_list()]
        shuffled_cm_graph.add_edges_from_no_data(new_edges)
        cm_nodes = [k for k, v in sorted(enumerate(cm_nodes), key=lambda item: item[1])]
        cm_graph = shuffled_cm_graph

    im_graph.add_nodes_from(range(len(qubits)))
    im_graph.add_edges_from_no_data(interactions)
    # To avoid trying to over optimize the result by default limit the number
    # of trials based on the size of the graphs. For circuits with simple layouts
    # like an all 1q circuit we don't want to sit forever trying every possible
    # mapping in the search space
    # im_graph_edge_count = len(im_graph.edge_list())
    # cm_graph_edge_count = len(cm_graph.edge_list())
    # max_trials = max(im_graph_edge_count, cm_graph_edge_count) + 15

    mappings = vf2_mapping(
        cm_graph,
        im_graph,
        subgraph=True,
        id_order=False,
        induced=False,
        call_limit=call_limit,
    )
    layouts = []
    for mapping in mappings:
        # Here we sort in the order that we would use
        # for intial layout
        temp_list = [None]*circ.num_qubits
        for cm_i, im_i in mapping.items():
            key = qubits[im_i]
            val = cm_nodes[cm_i]
            temp_list[circ.find_bit(key).index] = val
        layouts.append(temp_list)
    return layouts


def unique_subsets(mappings):
    """Unique subset of qubits in mappings.
    
    Parameters:
        mappings (list): Collection of possible mappings
    
    Returns:
        list: Unique sets of qubits
    """
    sets = []
    for mapping in mappings:
        temp = set(mapping)
        if not temp in sets:
            sets.append(temp)
    return sets


def best_mapping(circ, backends, successors=False, call_limit=10000):
    """Find the best selection of qubits and system to run
    the chosen circuit one.

    Parameters:
        circ (QuantumCircuit): Quantum circuit
        backends (IBMQBackend or list): A single or list of backends.
        successors (bool): Return list best mappings per backend passed.
        call_limit (int): Maximum number of calls to VF2 mapper.

    Returns:
        tuple: (best_layout, best_backend, best_error)
        list: List of tuples for best match for each backend
    """
    if not isinstance(backends, list):
        backends = [backends]

    best_error = np.inf
    best_layout = None
    best_backend = None
    mappings = {}
    best_out = []

    circ_qubits = circ.num_qubits
    for backend in backends:
        config = backend.configuration()
        num_qubits = config.num_qubits
        backend_name = backend.name()

        if not config.simulator and circ_qubits <= num_qubits:
            seg = config.processor_type.get('segment', '')
            key = str(num_qubits)+seg
            if key not in mappings:
                mappings[key] = exact_mappings(circ, config.coupling_map,
                                               call_limit=call_limit)
            props = backend.properties()
            system_best_layout = None
            system_best_error = np.inf
            if any(mappings[key]):
                for mapping in mappings[key]:
                    error = 0
                    fid = 1
                    for item in circ._data:
                        if item[0].name == 'cx':
                            q0 = circ.find_bit(item[1][0]).index
                            q1 = circ.find_bit(item[1][1]).index
                            fid *= (1-props.gate_error('cx', [mapping[q0],
                                                              mapping[q1]]))
                        if item[0].name == 'measure':
                            q0 = circ.find_bit(item[1][0]).index
                            fid *= 1-props.readout_error(mapping[q0])
                    error = 1-fid
                    if error < system_best_error:
                        system_best_layout = mapping
                        system_best_error = error
                    if error < best_error:
                        best_error = error
                        best_layout = mapping
                        best_backend = backend_name

                best_out.append((system_best_layout, backend_name, system_best_error))
    if best_layout:
        if not successors:
            return best_layout, best_backend, best_error
        best_out.sort(key=lambda x: x[2])
        return best_out
    return []
