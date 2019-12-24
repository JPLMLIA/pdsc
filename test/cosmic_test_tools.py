"""
Includes tools used for the COSMIC testing/evaluation process
"""
import numpy as np
from numbers import Number
import pytest
import sqlite3
from contextlib import contextmanager
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

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

class MockDbManager(object):

    def __init__(self):
        self._connections = {}

    @contextmanager
    def __call__(self, filename, *args, **kwargs):
        """
        Implements the mock ``sqlite3.connect`` functionality; use a
        contextmanager so we can keep the connection to the in-memory database
        open until after the tests have completed.
        """

        # Database must have already been initialized
        assert filename in self._connections

        try:
            yield self._connections[filename]
        finally:
            # *Don't* close the connection
            pass

    def new_connection(self, filename):
        conn = sqlite3.connect(
            ':memory:', detect_types=sqlite3.PARSE_DECLTYPES
        )
        self._connections[filename] = conn
        return conn

    def close(self):
        for c in self._connections.values():
            c.close()

@contextmanager
def mock_open(fname, mode):
    assert mode == 'r'
    try:
        io = StringIO(fname)
        yield io
    finally:
        io.close()
