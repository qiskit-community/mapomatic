# mapomatic

Automatic mapping of compiled circuits to low-noise sub-graphs

## Overview

One of the main painpoints in executing circuits on IBM Quantum hardware is finding the best qubit mapping.  For a given circuit, one typically tries to pick the best `initial_layout` for a given target system, and then SWAP maps using that set of qubits as the starting point.  However there are a couple of issues with that execution model.  First, an `initial_layout` selected, for example with respect to the noise characteristics of the system, need not be optimal for the SWAP mapping.  In practice this leads to either low-noise layouts with extra SWAP gates inserted in the circuit, or optimally SWAP mapped circuits on (possibly) lousy qubits.  Second, there is no way to know if the system you targeted in the compilation is actually the best one to execute the compiled circuit on.  With 20+ quantum systems, it is hard to determine which device is actually ideal for a given problem.

`mapomatic` tries to tackle these issues in a different way. `mapomatic` is a post-compilation routine that finds the best low noise sub-graph on which to run a circuit given one or more quantum systems as target devices.  Once compiled, a circuit has been rewritten so that its two-qubit gate structure matches that of a given sub-graph on the target system.  `mapomatic` then searches for matching sub-graphs using the VF2 mapper in [Qiskit](https://github.com/Qiskit/qiskit-terra) ([retworkx](https://github.com/Qiskit/retworkx) actually), and uses a heuristic to rank them based on error rates determined by the current calibration data. That is to say that given a single target system, `mapomatic` will return the best set of qubits on which to execute the compiled circuit.  Or, given a list of systems, it will find the best system and set of qubits on which to run your circuit.  Given the current size of quantum hardware, and the excellent performance of the VF2 mapper, this whole process is actually very fast.

## Usage

To begin we first import what we need and load our IBM Quantum account.

```python
import numpy as np
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

mm.best_overall_layout(small_qc, backends)
```

that returns a tuple with the target layout, system, and the computed error score:

```python
([5, 3, 2, 1, 0, 4], 'ibm_hanoi', 0.08603879221106037)
```

You can then use the best layout in a new call to `transpile` which will then do the desired mapping for you.  Alternatively, we can ask for the best mapping on all systems, yielding a list sorted in order from best to worse:

```python

mm.best_overall_layout(small_qc, backends, successors=True)
```

```python
[([5, 3, 2, 1, 0, 4], 'ibm_hanoi', 0.08603879221106037),
 ([36, 51, 50, 49, 48, 55], 'ibm_washington', 0.09150102196508092),
 ([21, 23, 24, 25, 22, 26], 'ibm_auckland', 0.09666750964284976),
 ([5, 8, 11, 14, 16, 13], 'ibmq_montreal', 0.1010191806180305),
 ([21, 23, 24, 25, 22, 26], 'ibm_cairo', 0.10310508869235013),
 ([6, 5, 3, 1, 0, 2], 'ibm_lagos', 0.10806691390621592),
 ([16, 19, 22, 25, 24, 26], 'ibmq_mumbai', 0.11927719515976587),
 ([24, 25, 22, 19, 20, 16], 'ibmq_toronto', 0.13724935147063222),
 ([24, 29, 30, 31, 32, 39], 'ibmq_brooklyn', 0.1537915794715058),
 ([13, 14, 11, 8, 5, 9], 'ibmq_guadalupe', 0.1575476343119544),
 ([4, 5, 3, 1, 0, 2], 'ibmq_casablanca', 0.17901628434617056),
 ([6, 5, 3, 1, 0, 2], 'ibm_perth', 0.18024603271960626),
 ([4, 5, 3, 1, 2, 0], 'ibmq_jakarta', 0.1874412047495625)]
```

Because of the stochastic nature of the SWAP mapping, the optimal sub-graph may change over repeated compilations.

## Getting optimal results

Because the SWAP mappers in Qiskit are stochastic, the number of inserted SWAP gates can vary with each run.  The spread in this number can be quite large, and can impact the performance of your circuit.  It is thus beneficial to `transpile` many instances of a circuit and take the best one.  For example:

```python
trans_qc_list = transpile([qc]*20, provider.get_backend('ibm_auckland'), optimization_level=3)

best_cx_count = [circ.count_ops()['cx'] for circ in trans_qc_list]
best_cx_count
```

```python
[10, 6, 10, 7, 10, 11, 8, 8, 8, 10, 8, 13, 10, 7, 10, 5, 8, 10, 7, 11]
```

We obviously want the one with minimum CNOT gates here:

```python

best_idx = np.where(best_cx_count == np.min(best_cx_count))[0][0]
best_qc = trans_qc_list[best_idx] 
```

We can then use this best mapped circuit to find the ideal qubit candidates via `mapomatic`.

```python
best_small_qc = mm.deflate_circuit(best_qc)
mm.best_overall_layout(best_small_qc, backends, successors=True)
```

```python
[([3, 2, 4, 1, 0], 'ibm_hanoi', 0.07011500213196731),
 ([51, 50, 48, 49, 55], 'ibm_washington', 0.07499096356285917),
 ([14, 11, 5, 8, 9], 'ibmq_montreal', 0.08633597995021536),
 ([3, 5, 11, 8, 9], 'ibm_auckland', 0.0905845988548658),
 ([5, 3, 0, 1, 2], 'ibm_lagos', 0.09341441561338637),
 ([23, 24, 22, 25, 26], 'ibm_cairo', 0.09368920161042149),
 ([19, 22, 24, 25, 26], 'ibmq_mumbai', 0.10338126987554686),
 ([25, 22, 16, 19, 20], 'ibmq_toronto', 0.12110219482337559),
 ([5, 3, 0, 1, 2], 'ibm_perth', 0.1283276775628739),
 ([14, 13, 15, 12, 10], 'ibmq_guadalupe', 0.12860835365491008),
 ([13, 14, 24, 15, 16], 'ibmq_brooklyn', 0.13081072372091407),
 ([5, 3, 0, 1, 2], 'ibmq_jakarta', 0.14268582212594894),
 ([5, 3, 0, 1, 2], 'ibmq_casablanca', 0.15103780612586304),
 ([4, 3, 0, 1, 2], 'ibmq_belem', 0.1574210243350943),
 ([4, 3, 0, 1, 2], 'ibmq_quito', 0.18349713324910477),
 ([4, 3, 0, 1, 2], 'ibmq_lima', 0.1977398974865432)]
```
