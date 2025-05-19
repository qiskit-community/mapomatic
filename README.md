# Mapomatic: Automatic mapping of compiled circuits to low-noise sub-graphs

[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI version](https://badge.fury.io/py/mapomatic.svg)](https://badge.fury.io/py/mapomatic)
[![pypi](https://img.shields.io/pypi/dm/mapomatic.svg)](https://pypi.org/project/mapomatic/)
![workflow](https://github.com/Qiskit-Partners/mapomatic/actions/workflows/python-package-conda.yml/badge.svg)

![mapomatic-fig](https://user-images.githubusercontent.com/1249193/221616579-56e574a7-5c1d-4479-8c92-16b0e350749a.png)

## Overview

One of the main painpoints in executing circuits on IBM Quantum hardware is finding the best qubit mapping.  For a given circuit, one typically tries to pick the best `initial_layout` for a given target system, and then SWAP maps using that set of qubits as the starting point.  However there are a couple of issues with that execution model.  First, an `initial_layout` selected, for example with respect to the noise characteristics of the system, need not be optimal for the SWAP mapping.  In practice this leads to either low-noise layouts with extra SWAP gates inserted in the circuit, or optimally SWAP mapped circuits on (possibly) lousy qubits.  Second, there is no way to know if the system you targeted in the compilation is actually the best one to execute the compiled circuit on.  With 20+ quantum systems, it is hard to determine which device is actually ideal for a given problem.

`mapomatic` tries to tackle these issues in a different way. `mapomatic` is a post-compilation routine that finds the best low noise sub-graph on which to run a circuit given one or more quantum systems as target devices.  Once compiled, a circuit has been rewritten so that its two-qubit gate structure matches that of a given sub-graph on the target system.  `mapomatic` then searches for matching sub-graphs using the VF2 mapper in [Qiskit](https://github.com/Qiskit/qiskit-terra) ([retworkx](https://github.com/Qiskit/retworkx) actually), and uses a heuristic to rank them based on error rates determined by the current calibration data. That is to say that given a single target system, `mapomatic` will return the best set of qubits on which to execute the compiled circuit.  Or, given a list of systems, it will find the best system and set of qubits on which to run your circuit.  Given the current size of quantum hardware, and the excellent performance of the VF2 mapper, this whole process is actually very fast.

### Qiskit Transpiler

The same algorithm used in mapomatic is integrated into the Qiskit transpiler
by default as the `VF2PostLayout` pass (https://qiskit.org/documentation/stubs/qiskit.transpiler.passes.VF2PostLayout.html)
which gets run by default in optimization levels 1, 2, and 3. Using mapomatic
as a standalone tool has two primary advantages, the first is to enable
running over multiple backends, and the second is to experiment with alternative
heuristic scoring (`VF2PostLayout` supports custom heuristic scoring, but it
is more difficult to integrate that into `transpile()`).

## Installation
`mapomatic` can be installed via `pip`: `pip install mapomatic` or installed from source.

## Usage

To begin we first import what we need

```python
import numpy as np
from qiskit import *
from qiskit_ibm_runtime import QiskitRuntimeService
import mapomatic as mm
```

Second we will load our IBM account and select a backend:

```python
service = QiskitRuntimeService()
backend = service.backend('ibm_fez')
```

We then go through the usual step of making a circuit and calling `transpile` on the given `backend`:

```python
qc = QuantumCircuit(5)
qc.h(0)
qc.cx(0,1)
qc.cx(0,2)
qc.cx(0,3)
qc.cx(0,4)
qc.measure_all()
```

Here we use `optimization_level=3` as it is the best overall.  It is also not noise-aware though, and thus can select lousy qubits on which to do a good SWAP mapping

```python
trans_qc = transpile(qc, backend, optimization_level=3)
```

Now, a call to `transpile` inflates the circuit to the number of qubits in the target system.  For small problems like the example here, this prevents us from finding the smaller sub-graphs.  Thus we need to deflate the circuit down to just the number of active qubits:

```python
small_qc = mm.deflate_circuit(trans_qc)
```

We can now find all the matching subgraphs of the target backend onto which the deflated circuit fits:

```python

layouts = mm.matching_layouts(small_qc, backend)
```

returning a list of possible layouts (not showing all of them):

```python
[[4, 3, 2, 1, 16],
 [16, 3, 2, 1, 4],
 [2, 3, 4, 5, 16],
 [16, 3, 4, 5, 2],
 [2, 3, 16, 23, 4],
 [4, 3, 16, 23, 2],
 [22, 23, 16, 3, 24],
 [24, 23, 16, 3, 22],
 [16, 23, 22, 21, 24],
 [24, 23, 22, 21, 16],
 [16, 23, 24, 25, 22],
 [22, 23, 24, 25, 16],
 [8, 7, 6, 5, 17],
 [17, 7, 6, 5, 8],
 [6, 7, 8, 9, 17],
 [17, 7, 8, 9, 6],
 [6, 7, 17, 27, 8],
 [8, 7, 17, 27, 6]]
```

We can then evaluate the "cost" of each layout, by default just the total error rate from gate and readout errors, to find a good candidate:

```python
scores = mm.evaluate_layouts(small_qc, layouts, backend)
```

```python
[([38, 29, 30, 31, 28], 0.05093873841945773),
 ([28, 29, 30, 31, 38], 0.050938738419458174),
 ([37, 25, 24, 23, 26], 0.05343574396227724),
 ([26, 25, 24, 23, 37], 0.05343574396227735),
 ([126, 125, 124, 123, 117], 0.05407007716175927),
 ([117, 125, 124, 123, 126], 0.05407007716175949),
 ([118, 109, 110, 111, 108], 0.05812828076384735),
 ([108, 109, 110, 111, 118], 0.05812828076384757),
 ([108, 107, 106, 105, 97], 0.058541600240600844),
 ([97, 107, 106, 105, 108], 0.05854160024060118),
 ([128, 129, 118, 109, 130], 0.05957264822459807),
 ([130, 129, 118, 109, 128], 0.05957264822459818),
 ([97, 107, 108, 109, 106], 0.05965873164544999),
 ([106, 107, 108, 109, 97], 0.05965873164544999),
 ([79, 73, 74, 75, 72], 0.06009536422582451),
 ([72, 73, 74, 75, 79], 0.06009536422582462),
 ([122, 123, 124, 125, 136], 0.06248799076446121),
 ([23, 21, 17, 18, 15, 12], 0.41564717799937645),
 ([12, 15, 17, 18, 21, 23], 0.43370673744503807),
 ([7, 10, 13, 12, 15, 18], 0.4472384837396254)]
```

The return layouts and costs are sorted from lowest to highest. You can then use the best layout in a new call to `transpile`
which will then do the desired mapping for you:

```python
best_qc = transpile(small_qc, backend, initial_layout=scores[0][0])
```

Alternatively, it is possible to do the same computation over multiple systems, eg all systems in the provider:

```python
backends = service.backends()

mm.best_overall_layout(small_qc, backends)
```

that returns a tuple with the target layout, system name, and the computed cost:

```python
([18, 31, 32, 33, 30], 'ibm_aachen', 0.03314823029292624)
```

Alternatively, we can ask for the best mapping on all systems, yielding a list sorted in order from best to worse:

```python

mm.best_overall_layout(small_qc, backends, successors=True)
```

```python
[([18, 31, 32, 33, 30], 'ibm_aachen', 0.03314823029292624),
 ([98, 111, 110, 109, 112], 'ibm_marrakesh', 0.05082476091063681),
 ([38, 29, 30, 31, 28], 'ibm_fez', 0.05093873841945773),
 ([9, 8, 7, 6, 17], 'ibm_torino', 0.09793328693588799)]
```

Because of the stochastic nature of the SWAP mapping, the optimal sub-graph may change over repeated compilations.


## Custom cost functions

You can define a custom cost function in the following manner:

```python

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
        for item in sch_circ.data:
            if item.operation.name in ['cx', 'cz', 'ecr']:
                q0 = item.qubits[0]._index
                q1 = item.qubits[1]._index
                fid *= (1-props.gate_error(item.operation.name, [q0, q1]))
                touched.add(q0)
                touched.add(q1)

            elif item.operation.name in ['sx', 'x']:
                q0 = item.qubits[0]._index
                fid *= 1-props.gate_error(item.operation.name, q0)
                touched.add(q0)

            elif item.operation.name == 'measure':
                q0 = item.qubits[0]._index
                fid *= 1-props.readout_error(q0)
                touched.add(q0)

            elif item.operation.name == 'delay':
                q0 = item.qubits[0]._index
                # Ignore delays that occur before gates
                # This assumes you are in ground state and errors
                # do not occur.
                if q0 in touched:
                    time = item.operation.duration * dt
                    fid *= 1-idle_error(time, t1s[q0], t2s[q0])

        error = 1-fid
        out.append((layout, error))
    return out


def idle_error(time, t1, t2):
    """Compute the approx. idle error from T1 and T2
    Parameters:
        time (float): Delay time in sec
        t1 (float): T1 time in sec
        t2, (float): T2 time in sec
    Returns:
        float: Idle error
    """
    t2 = min(t1, t2)
    rate1 = 1/t1
    rate2 = 1/t2
    p_reset = 1-np.exp(-time*rate1)
    p_z = (1-p_reset)*(1-np.exp(-time*(rate2-rate1)))/2
    return p_z + p_reset
```

You can then pass this to the layout evaluation steps:

```python

mm.best_overall_layout(small_qc, backends, successors=True, cost_function=cost_func)
```

# Citing

If you use mapomatic in your research, we would be delighted if you cite it in your work using the included [BibTeX file](CITATION.bib).
