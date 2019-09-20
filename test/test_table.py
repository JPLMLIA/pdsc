"""
Unit Tests for Table Code
"""
import pytest

from cosmic_test_tools import unit

from pdsc.table import parse_simple_label

@unit
def test_parse_simple_label():

    contents = """
    TEST_KEY1 = "TEST_VALUE1"
    TEST_KEY2 = TEST_VALUE2
    """

    value = parse_simple_label(contents, 'TEST_KEY1')
    assert value == 'TEST_VALUE1'

    value = parse_simple_label(contents, 'TEST_KEY2')
    assert value == 'TEST_VALUE2'

    value = parse_simple_label(contents, 'TEST_KEY3')
    assert value is None
