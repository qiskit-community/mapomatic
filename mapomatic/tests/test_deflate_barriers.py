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
"""Test preserving barriers in deflation"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.test.mock import FakeMontreal

import mapomatic as mm

BACKEND = FakeMontreal()


def test_deflate_barriers1():
    """I can properly deflate with final barrier over all qubits"""
    qc = QuantumCircuit(10)
    qc.h(0)
    qc.barrier(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    qc.barrier()

    trans_qc = transpile(qc, BACKEND)
    small_qc = mm.deflate_circuit(trans_qc)

    ans_qc = QuantumCircuit(4)
    ans_qc.rz(np.pi/2, 0)
    ans_qc.sx(0)
    ans_qc.rz(np.pi/2, 0)
    ans_qc.barrier(0)
    ans_qc.cx(0, 1)
    ans_qc.cx(1, 2)
    ans_qc.cx(2, 3)
    ans_qc.barrier()
    # Need to add phase
    ans_qc.global_phase = np.pi/4

    assert small_qc == ans_qc


def test_deflate_barriers2():
    """Test that a barrier itself does not mean active qubits"""
    qc = QuantumCircuit(10)
    qc.barrier()

    trans_qc = transpile(qc, BACKEND)
    small_qc = mm.deflate_circuit(trans_qc)

    ans_qc = QuantumCircuit()
    assert small_qc == ans_qc


def test_deflate_barriers3():
    """Test that measure_all subset returns itself (with a slight creg name change)"""
    qc = QuantumCircuit(10)
    qc.measure_all()

    trans_qc = transpile(qc, BACKEND)
    small_qc = mm.deflate_circuit(trans_qc)

    qr = QuantumRegister(10, 'q')
    qc = ClassicalRegister(10, 'c')
    ans_qc = QuantumCircuit(qr, qc)
    ans_qc.barrier()
    ans_qc.measure(range(10), range(10))

    assert small_qc == ans_qc
