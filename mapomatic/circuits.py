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
# pylint: disable=protected-access

"""Circuit manipulation tools"""
import numbers
from qiskit import QuantumCircuit


def deflate_circuit(input_circ):
    """Reduce a transpiled circuit down to only active qubits.

    Parameters:
        input_circ (QuantumCircuit): Input circuit.

    Returns:
        QuantumCircuit: Reduced circuit.

    Notes:
        Requires a circuit with flatten qregs and cregs.
    """
    active_qubits, active_clbits = active_bits(input_circ)

    num_reduced_qubits = len(active_qubits)
    num_reduced_clbits = len(active_clbits)

    active_map = {}
    for idx, val in enumerate(
        sorted(active_qubits, key=lambda x: input_circ.find_bit(x).index)
    ):
        active_map[val] = idx
    for idx, val in enumerate(
        sorted(active_clbits, key=lambda x: input_circ.find_bit(x).index)
    ):
        active_map[val] = idx

    new_qc = QuantumCircuit(num_reduced_qubits, num_reduced_clbits)
    for item in input_circ.data:
        # Find active qubits used by instruction (if any)
        used_active_set = [qubit for qubit in item[1] if qubit in active_qubits]
        # If any active qubits used, add to deflated circuit
        if any(used_active_set):
            ref = getattr(new_qc, item[0].name)
            params = item[0].params
            qargs = [new_qc.qubits[active_map[qubit]] for qubit in used_active_set]
            cargs = [new_qc.clbits[active_map[clbit]] for clbit in item[2]]
            ref(*params, *qargs, *cargs)
    new_qc.global_phase = input_circ.global_phase
    return new_qc


def active_bits(input_circ):
    """Find active bits (quantum and classical) in a transpiled circuit.

    Parameters:
        input_circ (QuantumCircuit): Input circuit.

    Returns:
        tuple: Tuple of sets for active qubits and active classical bits

    Notes:
        Requires a circuit with flatten qregs and cregs.
    """
    active_qubits = set([])
    active_clbits = set([])
    for item in input_circ.data:
        if item[0].name not in ["barrier", "delay"]:
            qubits = item[1]
            for qubit in qubits:
                active_qubits.add(qubit)
            clbits = item[2]
            for clbit in clbits:
                active_clbits.add(clbit)

    return active_qubits, active_clbits


def inflate_circuit(input_circ, layout, backend):
    """Inflate a circuit to execute on a backend.

    Parameters:
        input_circ (QuantumCircuit): Input circuit.
        layout (list): List of best qubits for layout
        backend (int or BackendV1 or BackendV2): An IBM Quantum backend instance
                                                 or integer specifying number of
                                                 qubits

    Returns:
        QuantumCircuit: Inflated circuit.

    Notes:
        Requires a circuit with flatten qregs and cregs.
    """
    if isinstance(backend, numbers.Integral):
        num_qubits = backend
    else:
        num_qubits = backend.configuration().num_qubits
    new_qc = QuantumCircuit(num_qubits, input_circ.num_clbits)
    for item in input_circ.data:
        ref = getattr(new_qc, item[0].name)
        params = item[0].params
        qargs = [layout[input_circ.find_bit(idx).index] for idx in item[1]]
        cargs = item[2]
        ref(*params, *qargs, *cargs)
    new_qc.global_phase = input_circ.global_phase
    return new_qc
