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
backend = provider.get_backend('ibm_auckland')
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

returning a list of possible layouts:

```python
[[3, 2, 0, 1, 4, 7],
 [7, 4, 0, 1, 2, 3],
 [1, 4, 6, 7, 10, 12],
 [12, 10, 6, 7, 4, 1],
 [3, 5, 9, 8, 11, 14],
 [14, 11, 9, 8, 5, 3],
 [7, 10, 15, 12, 13, 14],
 [7, 10, 13, 12, 15, 18],
 [14, 13, 15, 12, 10, 7],
 [14, 13, 10, 12, 15, 18],
 [18, 15, 13, 12, 10, 7],
 [18, 15, 10, 12, 13, 14],
 [8, 11, 16, 14, 13, 12],
 [8, 11, 13, 14, 16, 19],
 [12, 13, 16, 14, 11, 8],
 [12, 13, 11, 14, 16, 19],
 [19, 16, 13, 14, 11, 8],
 [19, 16, 11, 14, 13, 12],
 [12, 15, 17, 18, 21, 23],
 [23, 21, 17, 18, 15, 12],
 [14, 16, 20, 19, 22, 25],
 [25, 22, 20, 19, 16, 14],
 [19, 22, 26, 25, 24, 23],
 [23, 24, 26, 25, 22, 19]]
```

We can then evaluate the "cost" of each layout, by default just the total error rate from gate and readout errors, to find a good candidate:

```python
scores = mm.evaluate_layouts(small_qc, layouts, backend)
```

```python

[([3, 5, 9, 8, 11, 14], 0.1409544035570952),
 ([3, 2, 0, 1, 4, 7], 0.159886911767115),
 ([14, 11, 9, 8, 5, 3], 0.16797160130080224),
 ([19, 16, 13, 14, 11, 8], 0.1825119371865237),
 ([8, 11, 13, 14, 16, 19], 0.18331648549982482),
 ([7, 4, 0, 1, 2, 3], 0.19124485963881122),
 ([23, 24, 26, 25, 22, 19], 0.19226855309761348),
 ([25, 22, 20, 19, 16, 14], 0.19228399510047922),
 ([19, 22, 26, 25, 24, 23], 0.2000625493093675),
 ([14, 16, 20, 19, 22, 25], 0.20604403000055715),
 ([8, 11, 16, 14, 13, 12], 0.2580131332633393),
 ([12, 13, 16, 14, 11, 8], 0.27134706745983517),
 ([19, 16, 11, 14, 13, 12], 0.2755049869801992),
 ([12, 13, 11, 14, 16, 19], 0.2879346238104463),
 ([14, 13, 15, 12, 10, 7], 0.3474625243348848),
 ([1, 4, 6, 7, 10, 12], 0.34887580284018227),
 ([18, 15, 10, 12, 13, 14], 0.35020374737523874),
 ([7, 10, 15, 12, 13, 14], 0.35023196005467194),
 ([12, 10, 6, 7, 4, 1], 0.3628988750928549),
 ([18, 15, 13, 12, 10, 7], 0.39637978849009425),
 ([14, 13, 10, 12, 15, 18], 0.4063300698900274),
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
backends = provider.backends()

mm.best_overall_layout(small_qc, backends)
```

that returns a tuple with the target layout, system name, and the computed cost:

```python
([5, 3, 2, 1, 0, 4], 'ibm_hanoi', 0.08603879221106037)
```

Alternatively, we can ask for the best mapping on all systems, yielding a list sorted in order from best to worse:

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

## Custom cost functions

You can define a custom cost function in the following manner

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

```python

[([4, 0, 1, 2, 3], 'ibm_hanoi', 0.1058869747468042),
 ([0, 2, 1, 3, 5], 'ibm_lagos', 0.15241444774632107),
 ([0, 2, 1, 3, 5], 'ibm_perth', 0.16302150717418362),
 ([0, 2, 1, 3, 5], 'ibmq_casablanca', 0.18228556142682584),
 ([4, 0, 1, 2, 3], 'ibmq_mumbai', 0.19314785746073515),
 ([0, 2, 1, 3, 4], 'ibmq_quito', 0.20388545685291504),
 ([4, 0, 1, 2, 3], 'ibmq_montreal', 0.20954722547784943),
 ([0, 2, 1, 3, 4], 'ibmq_belem', 0.22163468736634484),
 ([5, 11, 4, 3, 2], 'ibmq_brooklyn', 0.23161086629870287),
 ([0, 2, 1, 3, 5], 'ibmq_jakarta', 0.23215575814258282),
 ([4, 0, 1, 2, 3], 'ibm_auckland', 0.2448657847182769),
 ([4, 0, 1, 2, 3], 'ibmq_guadalupe', 0.3104200973685135),
 ([0, 2, 1, 3, 4], 'ibmq_lima', 0.31936325970774426),
 ([5, 15, 4, 3, 2], 'ibm_washington', 0.35009793314185045),
 ([4, 0, 1, 2, 3], 'ibmq_toronto', 0.39020468922200047),
 ([4, 0, 1, 2, 3], 'ibm_cairo', 0.4133587550267118)]
 ```
