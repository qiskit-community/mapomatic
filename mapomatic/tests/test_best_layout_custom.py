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
import numpy as np
from qiskit import transpile, QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.test.mock import FakeBelem, FakeQuito, FakeLima

import mapomatic as mm


def test_best_mapping_ghz_state_full_device_multiple_qregs():
    """Test best mappings with multiple registers"""
    qr_a = QuantumRegister(2)
    qr_b = QuantumRegister(3)
    qc = QuantumCircuit(qr_a, qr_b)
    qc.h(qr_a[0])
    qc.cx(qr_a[0], qr_a[1])
    qc.cx(qr_a[0], qr_b[0])
    qc.cx(qr_a[0], qr_b[1])
    qc.cx(qr_a[0], qr_b[2])
    qc.measure_all()
    trans_qc = transpile(qc, FakeLima(), seed_transpiler=102442)
    backends = [FakeBelem(), FakeQuito(), FakeLima()]
    res = mm.best_overall_layout(trans_qc, backends, successors=True,
                                 cost_function=cost_func)
    expected_res = [
        ([2, 1, 0, 3, 4], 'fake_belem', 0.4150109526706456),
        ([0, 1, 2, 3, 4], 'fake_lima', 0.46177764990686654),
        ([2, 1, 0, 3, 4], 'fake_quito', 0.6335024069223241)
    ]
    for index, expected in enumerate(expected_res):
        assert res[index][0] == expected[0]
        assert res[index][1] == expected[1]
        assert np.allclose(res[index][2], expected[2])


def test_best_mapping_ghz_state_deflate_multiple_registers():
    """Test best mappings with multiple registers with deflate"""
    qr_a = QuantumRegister(2)
    qr_b = QuantumRegister(2)
    cr_a = ClassicalRegister(2)
    cr_b = ClassicalRegister(2)
    qc = QuantumCircuit(qr_a, qr_b, cr_a, cr_b)
    qc.h(qr_a[0])
    qc.cx(qr_a[0], qr_a[1])
    qc.cx(qr_a[0], qr_b[0])
    qc.cx(qr_a[0], qr_b[1])
    qc.measure(qr_a, cr_b)
    qc.measure(qr_b, cr_a)
    trans_qc = transpile(qc, FakeLima(), seed_transpiler=102442)
    small_circ = mm.deflate_circuit(trans_qc)
    backends = [FakeBelem(), FakeQuito(), FakeLima()]
    res = mm.best_overall_layout(small_circ, backends, successors=True,
                                 cost_function=cost_func)
    expected_res = [
        ([3, 1, 0, 2], 'fake_lima', 0.16555704545051042),
        ([3, 1, 0, 2], 'fake_belem', 0.21497431066677175),
        ([3, 1, 2, 0], 'fake_quito', 0.35663459001880293)
    ]
    for index, expected in enumerate(expected_res):
        assert res[index][0] == expected[0]
        assert res[index][1] == expected[1]
        assert np.allclose(res[index][2], expected[2])


def cost_func(circ, layouts, backend):
    """
    A custom cost function that includes T1 and T2 computed during idle periods

    Parameters:
        circ (QuantumCircuit): circuit of interest
        layouts (list of lists): List of specified layouts
        backend (IBMQBackend): An IBM Quantum backend instance

    Returns:
        list: Tuples of layout and cost
    """
    out = []
    props = backend.properties()
    dt = backend.configuration().dt
    num_qubits = backend.configuration().num_qubits
    t1s = [props.qubit_property(qq, 'T1')[0] for qq in range(num_qubits)]
    t2s = [props.qubit_property(qq, 'T2')[0] for qq in range(num_qubits)]
    for layout in layouts:
        sch_circ = transpile(circ, backend, initial_layout=layout,
                             optimization_level=0, scheduling_method='alap')
        error = 0
        fid = 1
        touched = set()
        for item in sch_circ._data:
            if item[0].name == 'cx':
                q0 = sch_circ.find_bit(item[1][0]).index
                q1 = sch_circ.find_bit(item[1][1]).index
                fid *= (1-props.gate_error('cx', [q0, q1]))
                touched.add(q0)
                touched.add(q1)

            elif item[0].name in ['sx', 'x']:
                q0 = sch_circ.find_bit(item[1][0]).index
                fid *= 1-props.gate_error(item[0].name, q0)
                touched.add(q0)

            elif item[0].name == 'measure':
                q0 = sch_circ.find_bit(item[1][0]).index
                fid *= 1-props.readout_error(q0)
                touched.add(q0)

            elif item[0].name == 'delay':
                q0 = sch_circ.find_bit(item[1][0]).index
                # Ignore delays that occur before gates
                # This assumes you are in ground state and errors
                # do not occur.
                if q0 in touched:
                    time = item[0].duration * dt
                    fid *= 1-idle_error(time, t1s[q0], t2s[q0])

        error = 1-fid
        out.append((layout, error))
        return out


def idle_error(time, t1, t2):
    """Compute the approx. idle error from T1 and T2
    Parameters:
        time (float): Delay time in sec
        t1 (float): T1 time in sec
        t2 (float): T2 time in sec
    Returns:
        float: Idle error
    """
    t2 = min(t1, t2)
    rate1 = 1/t1
    rate2 = 1/t2
    p_reset = 1-np.exp(-time*rate1)
    p_z = (1-p_reset)*(1-np.exp(-time*(rate2-rate1)))/2
    return p_z + p_reset
