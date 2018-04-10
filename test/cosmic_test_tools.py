"""
Includes tools used for the COSMIC testing/evaluation process
"""
from nose.plugins.attrib import attr

def unit(*args, **kwargs):
    return attr(testtype="unit")(*args, **kwargs)

def functional(*args, **kwargs):
    return attr(testtype="functional")(*args, **kwargs)
