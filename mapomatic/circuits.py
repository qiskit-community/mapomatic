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
    active_qubits = set([])
    for item in input_circ.data:
        if item[0].name not in ['barrier']:
            qubits = item[1]
            for qubit in qubits:
                active_qubits.add(qubit._index)

    active_qubits = list(active_qubits)
    num_reduced_qubits = len(active_qubits)
    num_meas_bits = len(input_circ.clbits)

    active_map = {}
    for idx, val in enumerate(active_qubits):
        active_map[val] = idx

    new_qc = QuantumCircuit(num_reduced_qubits, num_meas_bits)
    for item in input_circ.data:
        args = []
        if item[0].name not in ['barrier']:
            ref = getattr(new_qc, item[0].name)
            params = item[0].params
            if any(params):
                args.extend([float(param) for param in params])
            for qubit in item[1]:
                args.append(active_map[qubit._index])
            for meas in item[2]:
                args.append(meas._index)
            ref(*args)

    return new_qc
