# mapomatic

Automatic mapping of compiled circuits to low-noise sub-graphs

## Overview

One of the main painpoints in executing circuits on IBM Quantum hardware is finding the best qubit mapping.  For a given circuit, one typically tries to pick the best `initial_layout` for a given target system, and then SWAP maps using that set of qubits as the starting point.  However there are a couple of issues with that execution model.  First, an `initial_layout` seletected, for example with respect to the noise characteristics of the system, need not be optimal for the SWAP mapping.  In practice this leads to either low-noise layouts with extra SWAP gates inserted in the circuit, or optimally SWAP mapped circuits on (possibly) lousy qubits.  Second, there is no way to know if the system you targeted in the compilation is actually the best one to execute the compiled circuit on.  With 20+ quantum systems, it is hard to determine wich device is actually ideal for a given problem.

Mapomatic tries to tackle these issues in a different way. Mapomatic is a post-compilation routine that finds the best low noise sub-graph on which to run a circuit given one or more quantum systems as target devices.  Once compiled, a circuit has been rewritten so that its two-qubit gate structure matches that of a given sub-graph on the target system.  Mapomatic then searches for matching sub-graphs using the VF2 mapper in [Qiskit](https://github.com/Qiskit/qiskit-terra) ([retworkx](https://github.com/Qiskit/retworkx) actually), and uses a heuristic to rank them based on error rates determined by the current calibration data. That is to say that given a single target system, mapomatic will return the best set of qubits on which to execute the compiled circuit.  Or, given a list of systems, it will find the best system and set of qubits on which to run your circuit.  Given the current size of quantum hardware, and the excellent performance of the VF2 mapper, this whole process is actually very fast.


## Usage

> **IMPORTANT**: Mapomatic currently works only on circuits with single quantum and classical registers

To begin we first import what we need and load our IBM Quantum account.

```python
from qiskit import *
import mapomatic as mm

IBMQ.load_account()
```

Second we will select a `provider` that has one or more systems of interest in it:

```python

provider = IBMQ.get_provider(group='deployed')
```

We then go through the usual step of making a circuit and calling `transpile` on a given `backend`:

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
trans_qc = transpile(qc, provider.get_backend('ibm_auckland'),optimization_level=3)
```

Now, a call to `transpile` inflates the circuit to the number of qubits in the target system.  For small problems like the example here, this prevents us from finding the smaller sub-graphs.  Thus we need to deflate the circuit down to just the number of active qubits:

```python
small_qc = mm.deflate_circuit(trans_qc)
```

This deflated circuit, along with one or more backends can now be used to find the ideal system and mapping.  Here we will look over all systems in the provider:

```python
backends = provider.backends()

mm.best_mapping(small_qc, backends)
```

that returns a tuple with the target layout, system, and the computed error score:

```
([2, 1, 3, 5, 8], 'ibm_auckland', 0.09518597703355036)
```

Alternatively, we can ask for the best mapping on all systems, yielding a list sorted in order from best to worse:

```python

mm.best_mapping(small_qc, backends, successors=True)
```

```
[([2, 1, 3, 5, 8], 'ibm_auckland', 0.09518597703355036),
 ([7, 10, 4, 1, 0], 'ibm_hanoi', 0.11217956761629977),
 ([5, 6, 3, 1, 2], 'ibm_lagos', 0.1123755285308975),
 ([7, 6, 10, 12, 15], 'ibmq_mumbai', 0.13708593236124922),
 ([3, 2, 5, 8, 9], 'ibmq_montreal', 0.13762962991865924),
 ([2, 1, 3, 5, 8], 'ibm_cairo', 0.1423752001642351),
 ([1, 2, 3, 5, 6], 'ibmq_casablanca', 0.15623594190953083),
 ([4, 3, 5, 6, 7], 'ibmq_brooklyn', 0.16468576058762707),
 ([7, 6, 10, 12, 15], 'ibmq_guadalupe', 0.17186581811649904),
 ([5, 3, 8, 11, 14], 'ibmq_toronto', 0.1735555283027388),
 ([5, 4, 3, 1, 0], 'ibmq_jakarta', 0.1792325518776976),
 ([2, 3, 1, 0, 14], 'ibm_washington', 0.2078576175452339),
 ([1, 0, 2, 3, 4], 'ibmq_bogota', 0.23973220166838316),
 ([1, 2, 3, 5, 6], 'ibm_perth', 0.31268969778002176),
 ([3, 4, 2, 1, 0], 'ibmq_manila', 0.3182338194159915),
 ([1, 0, 2, 3, 4], 'ibmq_santiago', 1.0)]
```

Because of the stochastic nature of the SWAP mapping, the optimal sub-graph may change over repeated compilations.
