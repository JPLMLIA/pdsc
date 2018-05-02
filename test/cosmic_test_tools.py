"""
Includes tools used for the COSMIC testing/evaluation process
"""
import numpy as np
from numbers import Number
import pytest

unit = pytest.mark.unit
functional = pytest.mark.functional

class Approximately(object):

    def __init__(self, x, *args, **kwargs):
        self.x = x
        self.args = args
        self.kwargs = kwargs

    def __eq__(self, other):
        if isinstance(other, (np.ndarray, Number)):
            return np.allclose(self.x, other, *self.args, **self.kwargs)
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, repr(self.x))
