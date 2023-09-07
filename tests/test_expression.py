# Test the build method with a simple expression
import pytest

from typecrate.exceptions import ValueDoesNotExist
from typecrate.expression import ExpressionNode


def test_build_simple_expression():
    root = ExpressionNode.build("parent.child.grand_child")
    assert root.source == "parent"
    assert root.child.source == "child"
    assert root.child.child.source == "grand_child"
    assert root.child.child.child is None


# Test the build method with a single element
def test_build_single_element():
    root = ExpressionNode.build("a")
    assert root.source == "a"
    assert root.child is None


# Test the build method with an empty expression
def test_build_empty_expression():
    root = ExpressionNode.build("")
    assert root is None


# Test the build method with optional chaining
def test_build_with_optional():
    root = ExpressionNode.build("a.b?")
    assert root.source == "a"
    assert root.child.source == "b"
    assert root.child.optional is True


# Test the build method with default value
def test_build_with_default_value():
    root = ExpressionNode.build("a.b", default="N/A")
    assert root.fallback == "N/A"
    assert root.child.fallback == "N/A"


#
# Test a complex case with nested expressions and array index
def test_build_complex_expression():
    root = ExpressionNode.build("a[0].b[1].c?")
    assert root.source == "a"
    assert root.child.source == 0
    assert root.child.child.source == "b"
    assert root.child.child.child.source == 1
    assert root.child.child.child.child.source == "c"
    assert root.child.child.child.child.optional is True


def test_build_complex_array_expression():
    root = ExpressionNode.build("a[0][1].b[1][2][3].c?")
    assert root.source == "a"
    assert root.child.source == 0
    assert root.child.child.source == 1
    assert root.child.child.child.source == 'b'
    assert root.child.child.child.child.source == 1
    assert root.child.child.child.child.child.source == 2
    assert root.child.child.child.child.child.child.source == 3
    assert root.child.child.child.child.child.child.child.source == 'c'
    assert root.child.child.child.child.child.child.child.optional is True

#
# # Test getting value from a dictionary
# def test_get_value_from_dict():
#     root = ExpressionNode.build("a.b.c")
#     test_dict = {'a': {'b': {'c': 42}}}
#     assert root.get_value(test_dict) == 42
#
#
# # Test getting value from a class instance
# def test_get_value_from_class():
#     class TestClass:
#         def __init__(self):
#             self.a = {'b': {'c': 42}}
#
#     root = ExpressionNode.build("a.b.c")
#     test_instance = TestClass()
#     assert root.get_value(test_instance) == 42
#
#
# # Test getting value with optional chaining
# def test_get_value_optional():
#     root = ExpressionNode.build("a.b?.c")
#     test_dict = {'a': {}}
#     assert root.get_value(test_dict) is None
#
#
# # Test getting value with a default value
# def test_get_value_with_default():
#     root = ExpressionNode.build("a.b", default="N/A")
#     test_dict = {}
#     assert root.get_value(test_dict) == "N/A"
#
#
# # Test getting value with an array index
# def test_get_value_with_array_index():
#     root = ExpressionNode.build("a[0].b[1]")
#     test_dict = {'a': [{'b': [0, 42]}]}
#     assert root.get_value(test_dict) == 42
#
#
# # Test getting value with multiple array indices
# def test_get_value_with_multiple_array_indices():
#     root = ExpressionNode.build("a[0][1]")
#     test_dict = {'a': [[0, 42]]}
#     assert root.get_value(test_dict) == 42
#
#
# # Test getting value from an invalid source
# def test_get_value_invalid_source():
#     root = ExpressionNode.build("a.b.c")
#     test_dict = {"a": {"b": 1}}
#     with pytest.raises(ValueDoesNotExist) as e:  # Replace Exception with the specific exception you're raising
#         root.get_value(test_dict)
#         print(e)
#         print(str(e))
#         assert type(e) is ValueDoesNotExist
