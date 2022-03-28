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

from retworkx import PyGraph, PyDiGraph, vf2_mapping
from qiskit.converters import circuit_to_dag
from qiskit.transpiler.coupling import CouplingMap


def matching_layouts(circ, cmap, strict_direction=False, call_limit=10000):
    """Matching for a circuit onto a given topology (coupling map)

    Parameters:
        circ (QuantumCircuit): Input quantum circuit
        cmap (list or IBMQBackend): Coupling map or backend instance
        strict_direction (bool): Use directed coupling
        call_limit (int): Max number of calls to VF2 mapper

    Returns:
        list: Found mappings.
    """
    if isinstance(cmap, list):
        cmap = CouplingMap(cmap)
    else:
        cmap = CouplingMap(cmap.configuration().coupling_map)

    dag = circuit_to_dag(circ)
    qubits = dag.qubits
    qubit_indices = {qubit: index for index, qubit in enumerate(qubits)}

    interactions = []
    for node in dag.op_nodes(include_directives=False):
        len_args = len(node.qargs)
        if len_args == 2:
            interactions.append((qubit_indices[node.qargs[0]], qubit_indices[node.qargs[1]]))

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
        if temp not in sets:
            sets.append(temp)
    return sets


def evaluate_layouts(circ, layouts, backend, cost_function=None):
    """Evaluate the error rate of the layout on a backend

    Parameters:
        circ (QuantumCircuit): circuit of interest
        layouts (list): Specified layouts
        backend (IBMQBackend): An IBM Quantum backend instance
        cost_function (callable): Custom cost function, default=None

    Returns:
        list: Tuples of layout, backend name, and cost
    """
    if not any(layouts):
        return []
    if not isinstance(layouts[0], list):
        layouts = [layouts]
    if cost_function is None:
        cost_function = default_cost
    out = cost_function(circ, layouts, backend)
    out.sort(key=lambda x: x[1])
    return out


def best_overall_layout(circ, backends, successors=False, call_limit=10000, cost_function=None):
    """Find the best selection of qubits and system to run
    the chosen circuit one.

    Parameters:
        circ (QuantumCircuit): Quantum circuit
        backends (IBMQBackend or list): A single or list of backends.
        successors (bool): Return list best mappings per backend passed.
        call_limit (int): Maximum number of calls to VF2 mapper.
        cost_function (callable): Custom cost function, default=None

    Returns:
        tuple: (best_layout, best_backend, best_error)
        list: List of tuples for best match for each backend
    """
    if not isinstance(backends, list):
        backends = [backends]

    if cost_function is None:
        cost_function = default_cost

    layouts = {}
    best_out = []

    circ_qubits = circ.num_qubits
    for backend in backends:
        config = backend.configuration()
        num_qubits = config.num_qubits
        if not config.simulator and circ_qubits <= num_qubits:
            seg = config.processor_type.get('segment', '')
            key = str(num_qubits)+seg
            if key not in layouts:
                layouts[key] = matching_layouts(circ, config.coupling_map,
                                                call_limit=call_limit)
            layout_and_error = evaluate_layouts(circ, layouts[key], backend,
                                                cost_function=cost_function)
            if any(layout_and_error):
                layout = layout_and_error[0][0]
                error = layout_and_error[0][1]
                best_out.append((layout, backend.name(), error))
    best_out.sort(key=lambda x: x[2])
    if successors:
        return best_out
    return best_out[0]


def default_cost(circ, layouts, backend):
    """The default mapomatic cost function that returns the total
    error rate over all the layouts for the gates in the given circuit

    Parameters:
        circ (QuantumCircuit): circuit of interest
        layouts (list of lists): List of specified layouts
        backend (IBMQBackend): An IBM Quantum backend instance

    Returns:
        list: Tuples of layout and error
    """
    out = []
    # Make a single layout nested
    props = backend.properties()
    for layout in layouts:
        error = 0
        fid = 1
        for item in circ._data:
            if item[0].name == 'cx':
                q0 = circ.find_bit(item[1][0]).index
                q1 = circ.find_bit(item[1][1]).index
                fid *= (1-props.gate_error('cx', [layout[q0],
                                                  layout[q1]]))

            elif item[0].name in ['sx', 'x']:
                q0 = circ.find_bit(item[1][0]).index
                fid *= 1-props.gate_error(item[0].name, layout[q0])

            elif item[0].name == 'measure':
                q0 = circ.find_bit(item[1][0]).index
                fid *= 1-props.readout_error(layout[q0])
        error = 1-fid
        out.append((layout, error))
    return out
