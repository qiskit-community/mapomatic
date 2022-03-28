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
"""Test best mappings"""

from qiskit import QuantumCircuit
from qiskit.test.mock import FakeMontreal

import mapomatic as mm


def test_matching_layout_backend_pass():
    """Test that I can pass a backend to matching layouts"""
    qc = QuantumCircuit(4)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.cx(0, 3)
    qc.measure_all()

    backend = FakeMontreal()
    mappings1 = mm.matching_layouts(qc, backend)
    mappings2 = mm.matching_layouts(qc, backend.configuration().coupling_map)
    assert mappings1 == mappings2
