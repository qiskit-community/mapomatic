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

import pytest
from qiskit import transpile, QuantumCircuit
from qiskit.test.mock import FakeMontreal

import mapomatic as mm


def test_test_find_all_subgraphs():
    """Test that all unique subgraphs can be found"""
    qc = QuantumCircuit(4)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.cx(0, 3)
    qc.measure_all()

    backend = FakeMontreal()
    mappings = mm.mappings.exact_mappings(qc, backend.configuration().coupling_map)

    assert len(mappings) == 7

    ans_list = [[1, 2, 4, 0],
                [7, 4, 10, 6],
                [8, 5, 11, 9],
                [12, 10, 13, 15],
                [14, 11, 13, 16],
                [18, 15, 21, 17],
                [19, 16, 22, 20],
                [25, 22, 24, 26]]

    for mapping in mappings:
        assert mapping in ans_list
