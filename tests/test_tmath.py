import pytest
from typecrate.tmath import MathParser


def test_addition():
    parser = MathParser()
    assert parser.parse("2+3") == 5
    assert parser.parse("2+3+4") == 9


def test_subtraction():
    parser = MathParser()
    assert parser.parse("5-2") == 3
    assert parser.parse("10-3-2") == 5


def test_multiplication():
    parser = MathParser()
    assert parser.parse("2*3") == 6


def test_division():
    parser = MathParser()
    assert parser.parse("6/2") == 3


def test_modulo():
    parser = MathParser()
    assert parser.parse("10%3") == 1


def test_parentheses():
    parser = MathParser()
    assert parser.parse("(2+3)*4") == 20


def test_unary():
    parser = MathParser()
    assert parser.parse("-2+3") == 1
    assert parser.parse("+2+3") == 5


def test_functions():
    parser = MathParser()
    assert parser.parse("sqrt(4)") == 2
    assert parser.parse("sin(0)") == 0


def test_variables():
    parser = MathParser()
    variables = {'x': 5, 'y': 2}
    assert parser.parse("x+y", variables) == 7


def test_errors():
    parser = MathParser()
    with pytest.raises(ValueError):
        parser.parse("6/0")
    with pytest.raises(ValueError):
        parser.parse("unknown_func(4)")
    with pytest.raises(ValueError):
        parser.parse("z+4", {'x': 1})
    with pytest.raises(ValueError):
        parser.parse("(2+3")


def test_complex_arithmetic_1():
    parser = MathParser()
    assert parser.parse("2*3 + 5/5 - 3") == 4


def test_complex_arithmetic_2():
    parser = MathParser()
    assert parser.parse("(2+3) * (4+1)") == 25


def test_complex_arithmetic_3():
    parser = MathParser()
    assert parser.parse("2 * (3 + (4 * 5))") == 46


def test_complex_arithmetic_4():
    parser = MathParser()
    assert parser.parse("10 % 3 + 1") == 2


def test_complex_arithmetic_5():
    parser = MathParser()
    assert parser.parse("(2*3) + sqrt(16)") == 10


def test_complex_arithmetic_with_functions_1():
    parser = MathParser()
    assert parser.parse("sqrt(49) + sin(0) + cos(0)") == 8  # sqrt(49) = 7, sin(0) = 0, cos(0) = 1


def test_complex_arithmetic_with_functions_2():
    parser = MathParser()
    assert parser.parse("tan(0) + 3*exp(0)") == 3  # tan(0) = 0, exp(0) = 1


def test_complex_arithmetic_with_variables():
    parser = MathParser()
    variables = {'x': 2, 'y': 3, 'z': 4}
    assert parser.parse("(x+y)*z", variables) == 20  # (2 + 3) * 4 = 20


def test_nested_functions():
    parser = MathParser()
    assert parser.parse("sqrt(sin(0) + cos(0))") == 1  # sqrt(0 + 1) = 1
