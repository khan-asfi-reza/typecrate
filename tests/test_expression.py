import pytest

from typecrate.exceptions import ValueDoesNotExist
from typecrate.expression import ExpressionNode, E


def test_build_simple_expression():
    root = ExpressionNode.build("parent.child.grand_child")
    assert root.source.getter == "parent"
    assert root.child.source.getter == "child"
    assert root.child.child.source.getter == "grand_child"
    assert root.child.child.child is None


# Test the build method with a single element
def test_build_single_element():
    root = ExpressionNode.build("a")
    assert root.source.getter == "a"
    assert root.child is None


# Test the build method with an empty expression
def test_build_empty_expression():
    root = ExpressionNode.build("")
    assert root is None


# Test the build method with optional chaining
def test_build_with_optional():
    root = ExpressionNode.build("a.b?")
    assert root.source.getter == "a"
    assert root.child.source.getter == "b"
    assert root.child.optional is True


# Test the build method with default value
def test_build_with_default_value():
    root = ExpressionNode.build("a.b", default="N/A")
    assert root.default == "N/A"
    assert root.child.default == "N/A"


# Test a complex case with nested expressions and array index
def test_build_complex_expression():
    root = ExpressionNode.build("a[0].b[1].c?")
    assert root.source.getter == "a"
    assert root.child.source.getter == 0
    assert root.child.child.source.getter == "b"
    assert root.child.child.child.source.getter == 1
    assert root.child.child.child.child.source.getter == "c"
    assert root.child.child.child.child.optional is True


# Test a complex case with nested expressions and array index
def test_build_complex_array_optional_expression():
    root = ExpressionNode.build("a[0]?[1].b[1]?.c?")
    assert root.source.getter == "a"
    assert root.child.source.getter == 0
    assert root.child.optional is True
    assert root.child.child.source.getter == 1
    assert root.child.child.child.source.getter == "b"
    assert root.child.child.child.child.source.getter == 1
    assert root.child.child.child.child.child.source.getter == "c"
    assert root.child.child.child.child.child.optional is True


def test_build_complex_array_expression():
    root = ExpressionNode.build("a[0][1].b[1][2][3].c?")
    assert root.source.getter == "a"
    assert root.child.source.getter == 0
    assert root.child.child.source.getter == 1
    assert root.child.child.child.source.getter == 'b'
    assert root.child.child.child.child.source.getter == 1
    assert root.child.child.child.child.child.source.getter == 2
    assert root.child.child.child.child.child.child.source.getter == 3
    assert root.child.child.child.child.child.child.child.source.getter == 'c'
    assert root.child.child.child.child.child.child.child.optional is True


# Test getting value from a dictionary
def test_get_from_dict():
    root = ExpressionNode.build("a.b.c")
    test_dict = {'a': {'b': {'c': 42}}}
    assert root.get(test_dict) == 42


# Test getting value from a class instance
def test_get_from_class():
    class TestClass:
        def __init__(self):
            self.a = {'b': {'c': 42}}

    root = ExpressionNode.build("a.b.c")
    test_instance = TestClass()
    assert root.get(test_instance) == 42


# Test getting value with optional chaining
def test_get_optional():
    root = ExpressionNode.build("a.b?.c")
    test_dict = {'a': {}}
    assert root.get(test_dict) is None


# Test getting value with a default value
def test_get_with_default():
    root = ExpressionNode.build("a.b", default="N/A")
    test_dict = {}
    assert root.get(test_dict) == "N/A"


# Test getting value with an array index
def test_get_with_array_index():
    root = ExpressionNode.build("a[0].b[1]")
    test_dict = {'a': [{'b': [0, 42]}]}
    assert root.get(test_dict) == 42


# Test getting value with multiple array indices
def test_get_with_multiple_array_indices():
    root = ExpressionNode.build("a[0][1]")
    test_dict = {'a': [[0, 42]]}
    assert root.get(test_dict) == 42


# Test getting value from an invalid source
def test_get_invalid_source():
    root = ExpressionNode.build("a.b.c")
    test_dict = {"a": {"b": 1}}
    with pytest.raises(ValueDoesNotExist):
        root.get(test_dict)


# Test getting value from an invalid source
def test_get_data_from_array():
    root = ExpressionNode.build("a.b.c")
    test_dict = {"a": {"b": {"c": [1, 2, 3, 4]}}}
    assert root.get(test_dict) == [1, 2, 3, 4]


def test_get_data_from_array_index():
    root = ExpressionNode.build("a.b.c[0]")
    test_dict = {"a": {"b": {"c": [1, 2, 3, 4]}}}
    assert root.get(test_dict) == 1


def test_get_data_from_array_slice():
    root = ExpressionNode.build("a.b.c[0:2:1]")
    test_dict = {"a": {"b": {"c": [1, 2, 3, 4]}}}
    assert root.get(test_dict) == [1, 2]


def test_get_data_from_array_slice_with_2_step():
    root = ExpressionNode.build("a.b.c[0:5:2]")
    test_dict = {"a": {"b": {"c": [1, 2, 3, 4]}}}
    assert root.get(test_dict) == [1, 3]


def test_get_data_from_array_slice_with_just_step():
    root = ExpressionNode.build("a.b.c[::2]")
    test_dict = {"a": {"b": {"c": [1, 2, 3, 4]}}}
    assert root.get(test_dict) == [1, 3]


def test_get_data_from_array_slice_with_start_end():
    root = ExpressionNode.build("a.b.c[0:3]")
    test_dict = {"a": {"b": {"c": [1, 2, 3, 4]}}}
    assert root.get(test_dict) == [1, 2, 3]


def test_get_data_from_array_index_optional():
    root = ExpressionNode.build("a.b.c[0]?")
    test_dict = {"a": {"b": {"c": []}}}
    assert root.get(test_dict) is None


def test_simple_key_fetching():
    e = E("name.first")
    assert e.get({"name": {"first": "John", "last": "Doe"}}) == "John"


def test_with_default_value():
    e = E("name.middle", default="N/A")
    assert e.get({"name": {"first": "John", "last": "Doe"}}) == "N/A"


def test_chainable_expressions():
    e1 = E("name.first")
    e2 = E("name.last")
    e1 + e2
    assert e1.get({"name": {"first": "John", "last": "Doe"}}) == "JohnDoe"


def test_using_operators():
    e1 = E("name.first")
    e2 = E("first_name", default="Jane")
    e1 | e2
    assert e1.get({"first_name": "Alice"}) == "Alice"


def test_using_array_slicing():
    e = E("numbers[1:4]")
    assert e.get({"numbers": [0, 1, 2, 3, 4]}) == [1, 2, 3]


def test_advanced_optional_chaining():
    e = E("name.middle?")
    assert e.get({"name": {"first": "John", "last": "Doe"}}) is None

    e = E("a.b?.c | a.b[1:2:3].c", default="N/A")
    assert e.get({"a": {"b": [{"c": "value"}]}}) == "N/A"


def test_using_array_wildcards():
    e = E("a[*].b")
    assert e.get({"a": [{"b": 1}, {"b": 2}, {"b": 3}]}) == [1, 2, 3]


def test_unique_operator():
    e = E("a.b[*]^")
    assert e.get({"a": {"b": [1, 1, 2, 3, 3]}}) == [1, 2, 3]
