from enum import Enum
from typing import Any, List, Union

from typecrate.datatype import Empty
from typecrate.exceptions import (
    InvalidSourceExpression,
    ValueDoesNotExist,
)
from typecrate.methods import classproperty
from typecrate.utils import get_attribute, is_iterable


class Token:
    LSB = "["
    RSB = "]"
    DOT = "."
    L_PAR = "("
    R_PAR = ")"
    Q_MARK = "?"
    UP_CARET = "^"
    PLUS = "+"
    PIPE = "|"
    ASTER = "*"
    COLON = ":"

    @classproperty
    def seperator_tokens(self):
        return {self.LSB, self.RSB, self.DOT}

    @classproperty
    def unr_operators(self):
        """
        Unary operator, works on the current node
        """
        return {self.Q_MARK, self.UP_CARET}

    @classproperty
    def operators(self):
        return {self.PLUS, self.PIPE}


def to_int(string: str) -> Union[int, None]:
    if not string:
        return None
    return int(string)


def extract_attribute(expression: str) -> Union[str, int, List]:
    attr = (
        expression.strip()
        .removesuffix(Token.RSB)
        .removeprefix(Token.LSB)
    )
    if attr.isalpha() or attr == Token.ASTER:
        return attr
    if attr.isdigit():
        return int(attr)
    if Token.COLON in attr:
        try:
            colon_attr = list(map(to_int, attr.split(Token.COLON)))
        except ValueError:
            raise InvalidSourceExpression(
                "Syntax error, slice operators must be integer"
            )
        if len(colon_attr) > 3:
            raise InvalidSourceExpression(
                "Syntax error, Slice operation must follow `[start:end:step]`"
            )
        if len(colon_attr) == 2:
            colon_attr.append(1)
        return colon_attr
    return attr


def format_attribute(attr: str):
    return (
        attr
        .replace("?", "")
        .replace("^", "")
    )


class BaseGetter:
    def get(self, obj: Any):
        """Placeholder method to get the value from an object based on some expression."""
        pass

    def parse(self, *args, **kwargs):
        """Placeholder method to parse the expression."""
        pass


class OperationType(Enum):
    OBJ = "OBJECT"
    ARR = "ARRAY"
    ARR_SELECT = "ARRAY_SELECT"
    ARR_SLICE = "ARRAY_SLICE"


def get_operation_type(attr: Union[str, List, int], in_bracket: bool) -> OperationType:
    if in_bracket:
        if attr == Token.ASTER:
            return OperationType.ARR
        elif type(attr) is list:
            return OperationType.ARR_SLICE
        return OperationType.ARR_SELECT
    return OperationType.OBJ


class BasicE(BaseGetter):
    """
    BasicE class also known as BasicExpression getter.
    """


class Expression(BaseGetter):
    """
    Expression class converts an expression/string, parses it to a list of arguments.
    These arguments will be used in the `get` method. The `get` method uses these 
    arguments recursively on a given dataset to get the data.
    "item.value.id" -> Will be parsed to [item, value, id]
    Which will perform the action `data.get(item).get(value).get(id)`
    

    Attributes:
        expression (str): The main expression string this node represents.
        default (Any): A default value to use if the expression fails, 
                       a global default value.


    Examples:

        ```python
        # Simple attribute lookup on a dictionary
        root_node = Expression("person.name")
        data = {'person': {'name': 'Alice'}}
        value = root_node.get(data)
        print(value)  # Expected Output: Alice
        ```

        ```python
        # Optional attribute lookup on a dictionary
        root_node = Expression("person.name?")
        data = {'person': {}}
        value = root_node.get(data)
        print(value)  # Expected Output: None
        ```

        ```python
        # Simple attribute lookup on a class instance
        root_node = Expression("company.CEO.name")
        class Person:
            def __init__(self, name):
                self.name = name
        class Company:
            def __init__(self, CEO):
                self.CEO = CEO
        CEO = Person("Alice")
        company_instance = Company(CEO)
        value = root_node.get(company_instance)
        print(value)  # Expected Output: Alice
        ```

        ```python
        # Optional attribute lookup on a class instance
        root_node = Expression("company.CFO.name?")
        class Company:
            def __init__(self, CEO):
                self.CEO = CEO
                self.CFO = None
        CEO = Person("Alice")
        company_instance = Company(CEO)
        value = root_node.get(company_instance)
        print(value)  # Expected Output: None
        ```

        ```python
        # Nested dot-separated with array index
        root_node = Expression("students[0].name")
        data = {'students': [{'name': 'Alice'}, {'name': 'Bob'}]}
        value = root_node.get(data)
        print(value)  # Expected Output: Alice
        ```

        ```python
        # Nested dot-separated with multiple array indices
        root_node = Expression("matrix[0][1]")
        data = {'matrix': [[1, 2], [3, 4]]}
        value = root_node.get(data)
        print(value)  # Expected Output: 2
        ```
    """

    def __init__(self, expression: str, default=Empty):
        self.expression = expression
        self.default = default
        self.expression_list = self.parse(self.expression)
        self.exp_len = len(self.expression_list)

    def get_default(self, default):
        return default if default is not Empty else self.default

    def get_attribute(self, instance: Any, attr: str, default=Empty):
        optional = attr.endswith("?")
        default = self.get_default(default)
        optional = optional or default is not Empty
        try:
            return get_attribute(instance, format_attribute(attr))
        except ValueDoesNotExist as exc:
            if optional:
                return default
            raise exc

    def parse(self, expression):
        start, index, br_margin = 0, 0, 0
        in_brackets = False
        exp_len = len(expression)
        attr_list = []
        while index < exp_len:
            char = expression[index]
            if (
                    char in Token.seperator_tokens
                    or char in Token.unr_operators
                    or index == exp_len - 1
            ):
                # Determining end index, as for the last index, the last character stays missing
                end = index + 1 if index == exp_len - 1 else index
                attribute = extract_attribute(expression[start:end])
                operation = get_operation_type(attribute, in_brackets)
                start = index + 1
                if attribute:
                    attr_list.append(
                        (operation, attribute)
                    )

                if char == Token.LSB:
                    if in_brackets:
                        raise InvalidSourceExpression(
                            "{} Syntax error, "
                            "`[` inside `[]` not allowed.".format(expression)
                        )
                    # Mark that we are inside array brackets
                    in_brackets = True
                    # Increment the bracket margin counter
                    br_margin += 1

                elif char == Token.RSB:
                    if not in_brackets:
                        raise InvalidSourceExpression(
                            "`{}` Syntax error in source expression, "
                            "Array index must be in the following pattern "
                            "`item[n]`".format(expression)
                        )
                    in_brackets = False
                    # Decrement the bracket margin counter
                    br_margin -= 1

                else:
                    if index < exp_len - 2:
                        if expression[index + 1] == "[":
                            raise InvalidSourceExpression(
                                "`{}` Syntax error in source expression, "
                                "Cannot contain array index after `.` operator"
                                "".format(expression)
                            )

            index += 1

        # If the bracket margin is still greater than zero, it means we have unmatched brackets
        if br_margin > 0:
            raise InvalidSourceExpression("{} Syntax error: Unmatched '['.".format(expression))

        return attr_list

    def handle_obj_attr(self, instance, attr, default, index, raw):
        instance = self.get_attribute(instance, attr, default)
        instance = self.get(instance, default, index + 1, raw)
        return instance

    def handle_array_attr(
            self,
            instance: Any,
            attr: Union[str, int, List],
            operation: OperationType,
            default: Any,
            index: int,
            root: Any
    ):
        ret = []
        if not is_iterable(instance):
            raise ValueError(
                "Value is not iterable for source `{}`".format(
                    self.expression
                )
            )
        if type(attr) is list:
            start, end, step = attr
            start = start or 0
            end = end or len(instance)
            step = step or 1
            instance = instance[start:end:step]
        for each in instance:
            val = self.get(each, default, index + 1, root)
            if type(val) is not list:
                ret.append(
                    val
                )
            else:
                ret += val
        if operation == OperationType.ARR_SELECT:
            ret = ret[attr]
        return ret

    def get(self, instance: Any, default=Empty, index=0, root=Empty):
        expression_list = self.expression_list
        exp_len = self.exp_len

        root = instance if root is Empty else root

        default_value = default if default is not Empty else self.default

        while index < exp_len and instance:
            operation, attr = expression_list[index]

            if operation == OperationType.OBJ:
                try:
                    instance = get_attribute(instance, format_attribute(attr))
                except ValueDoesNotExist as exc:
                    if attr.endswith("?") or default_value is not Empty:
                        return default_value
                    raise exc

                index += 1

            else:
                if not is_iterable(instance):
                    raise ValueError(
                        "Value is not iterable for source `{}`".format(self.expression)
                    )

                if operation == OperationType.ARR_SLICE:
                    start, end, step = attr
                    start = start or 0
                    end = end or len(instance)
                    step = step or 1
                    instance = instance[start:end:step]

                if operation == OperationType.ARR_SELECT:
                    instance = [instance[attr]]

                instance = [
                    self.get(each, default, index + 1, root) for each in instance
                ]

                instance = instance[attr] if operation == OperationType.ARR_SELECT else instance

                break

        return instance

