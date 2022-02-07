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
"""Test layouts in transpile"""

from qiskit import transpile
from qiskit.test.mock import FakeMontreal
from qiskit.circuit.library import QuantumVolume

import mapomatic as mm


def test_layouts_transpile():
    """Solution layouts preserve circuit ops"""
    backend = FakeMontreal()
    qv_circ = QuantumVolume(5, seed=12345)
    trans_qc = transpile(qv_circ, backend, optimization_level=3)
    small_qc = mm.deflate_circuit(trans_qc)
    ans_ops = small_qc.count_ops()

    layouts = mm.matching_layouts(small_qc, backend.configuration().coupling_map)
    for layout in layouts:
        temp_circ = transpile(small_qc, backend, initial_layout=layout)
        temp_ops = temp_circ.count_ops()
        assert temp_ops == ans_ops
