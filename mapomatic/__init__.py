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

"""MapMan
"""

try:
    from .version import version as __version__
except ImportError:
    __version__ = '0.0.0'

from .circuits import deflate_circuit
from .layouts import (best_overall_layout, matching_layouts, evaluate_layouts)


def about():
    """The Mapomatic version info function.
    """
    print('='*80)
    print('# Mapomatic version {}'.format(__version__))
    print('# (C) Copyright IBM 2022.')
    print('# Paul Nation and Matthew Treinish')
    print('='*80)
