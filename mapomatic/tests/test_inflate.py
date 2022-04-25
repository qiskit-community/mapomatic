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
"""Tests for inflating circuits"""

from qiskit import QuantumCircuit, transpile
from qiskit.test.mock import FakeMontreal

import mapomatic as mm

BACKEND = FakeMontreal()


def test_inflate1():
    """I can properly inflate a circuit"""
    qc = QuantumCircuit(5)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.cx(0, 3)
    qc.cx(0, 4)
    qc.measure_all()
    trans_qc = transpile(qc, BACKEND, optimization_level=3)
    small_qc = mm.deflate_circuit(trans_qc)
    layouts = mm.matching_layouts(small_qc, BACKEND)
    scores = mm.evaluate_layouts(small_qc, layouts, BACKEND)
    best_layout = scores[0][0]

    qc1 = mm.inflate_circuit(small_qc, best_layout, 27)
    qc2 = transpile(small_qc, BACKEND, initial_layout=best_layout)

    data2 = qc2.data.copy()
    for item in qc1.data:
        name1 = item[0].name
        qubits1 = [qc1.find_bit(jj).index for jj in item[1]]
        found = False
        for idx2, item2 in enumerate(data2):
            name2 = item2[0].name
            qubits2 = [qc2.find_bit(jj).index for jj in item2[1]]
            if name2 == name1 and qubits2 == qubits1:
                found = True
                data2.pop(idx2)
                break
        assert found
