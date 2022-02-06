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


def test_test_find_all_subsets():
    """Test that all unique subset can be found"""
    qc = QuantumCircuit(4)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.cx(0, 3)
    qc.measure_all()

    backend = FakeMontreal()
    mappings = mm.matching_layouts(qc, backend.configuration().coupling_map)
    unique_sets = mm.layouts.unique_subsets(mappings)

    assert len(unique_sets) == 8

    ans_list = [set([1, 2, 4, 0]),
                set([7, 4, 10, 6]),
                set([8, 5, 11, 9]),
                set([12, 10, 13, 15]),
                set([14, 11, 13, 16]),
                set([18, 15, 21, 17]),
                set([19, 16, 22, 20]),
                set([25, 22, 24, 26])]

    for st in unique_sets:
        assert st in ans_list
