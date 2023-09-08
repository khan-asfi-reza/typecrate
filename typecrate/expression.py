import string
import traceback
from collections.abc import Mapping
from enum import Enum
from typing import Any, Optional

from typecrate.datatype import Empty, NonExistent
from typecrate.exceptions import ValueDoesNotExist, InvalidSourceExpression, InvalidDataType
from typecrate.methods import classproperty
from typecrate.structure import EArray
from typecrate.utils import is_callable, is_iterable


class OpType(Enum):
    # Refers to [0]/[-1]/[1:2]/[*]/[@len-1] indexed child
    ARRAY = "ARRAY"
    # Refers to . seperated child
    OBJ = "OBJ"
    # None
    NULL = "NULL"


class Token:
    LSB = "["
    RSB = "]"
    DOT = "."
    L_PAR = "("
    R_PAR = ")"
    Q_MARK = "?"
    UP_CARET = "^"

    @classproperty
    def seperator_tokens(self):
        return self.LSB, self.RSB, self.DOT

    @classproperty
    def unr_operators(self):
        """
        Unary operator, works on the current node
        """
        return self.Q_MARK, self.UP_CARET


class SourceOpType:
    ARRAY_INDEX_SELECT = "ARRAY_INDEX_SELECT"
    ARRAY_SLICE_SELECT = "ARRAY_SLICE_SELECT"
    ARRAY_FULL_SELECT = "ARRAY_FULL_SELECT"
    ARRAY_MULTI_INDEX_SELECT = "ARRAY_MULTI_INDEX_SELECT"
    CHILD_OBJ_SELECT = "CHILD_OBJ_SELECT"

    @classproperty
    def array_op_type(self):
        """
        Operations that will return a list of object or an array
        Examples:
            x[0] will return one element from x
            x[1,2] will return 2nd and 3rd element from x
            x[*] will return every element from x, just x[*] is redundant though.
            x[*] only makes sense if it has child chaining: IE: x[*].y which will get
            y for every element in x
        Returns(tuple(str)): Tuple of operation
        """
        return (
            self.ARRAY_SLICE_SELECT,
            self.ARRAY_MULTI_INDEX_SELECT,
            self.ARRAY_FULL_SELECT
        )


class SourceNode:
    """
    Source is dynamic structure, to get a certain portion from a dataset like dictionary or object
    Source node is required
    """

    def __init__(self, expression, op_type):
        raw_expression = expression
        self.raw_expression = raw_expression
        if expression.endswith(Token.UP_CARET):
            self.unique_array = True
        else:
            self.unique_array = False
        self.op_type = op_type
        self.source_op_type = SourceOpType.CHILD_OBJ_SELECT
        getter = expression
        if self.op_type == OpType.ARRAY:
            expression = expression.removesuffix(Token.RSB).removeprefix(Token.LSB)
            getter = expression
            if ":" in expression and "," in expression:
                raise InvalidSourceExpression(
                    "`[{}]` Invalid expression,"
                    "Both slice operation(`[start:end:step]`) and index multiple select operation(`[1,2]`) is not "
                    "supported "
                    "".format(expression)
                )
            elif ":" in expression:
                try:
                    getter = list(map(lambda x: None if x == "" else int(x), expression.split(":")))
                    self.source_op_type = SourceOpType.ARRAY_SLICE_SELECT
                    if len(getter) == 2:
                        getter.append(None)
                    if len(getter) > 3:
                        raise InvalidSourceExpression(
                            "Invalid slice operation `[{}]` performed, the slice operation must follow `["
                            "start:end:step]` "
                            "".format(expression)
                        )
                except ValueError:
                    tb = traceback.format_exc()
                    raise InvalidSourceExpression(
                        "Invalid source `[{}]`,"
                        "Slice operator must have integers, original exception was \n{}".format(
                            expression, tb
                        )
                    )
            elif "," in expression:
                try:
                    getter = list(map(int, expression.split(",")))
                    self.source_op_type = SourceOpType.ARRAY_MULTI_INDEX_SELECT
                except ValueError:
                    tb = traceback.format_exc()
                    raise InvalidSourceExpression(
                        "Invalid source `[{}]`,"
                        "Multi index selector must have integers, original exception was \n{}".format(
                            expression, tb
                        )
                    )
            elif expression in string.digits + "*":
                if expression in string.digits and expression != "":
                    self.source_op_type = SourceOpType.ARRAY_INDEX_SELECT
                    getter = int(expression)
                else:
                    self.source_op_type = SourceOpType.ARRAY_FULL_SELECT
        self.getter = getter

    def __repr__(self):
        return self.raw_expression


def clean_expression(expression: str) -> str:
    return expression.strip().replace(
        " ", ""
    ).removesuffix(
        Token.UP_CARET
    ).removesuffix(
        Token.Q_MARK
    ).removesuffix(
        Token.UP_CARET
    ).removesuffix(
        Token.RSB
    ).removeprefix(
        Token.LSB
    )


class ExpressionNode:
    """
    A class to model an expression node.

    This class represents a node in an expression tree, useful for
    evaluating complex expressions. Each node may contain a source attribute,
    an expression, an optional flag, child nodes, and other metadata.

    Attributes:
        expression (str): The main expression string this node represents.
        full_expression (str): The full expression string that includes
            all parent nodes.
        default (Any): A default value to use if the expression fails.
        source (SourceNode, Optional): The source attribute, derived from
            the expression.
        optional (bool): A flag to denote if the node is optional. Defaults
            to False.
        child (ExpressionNode, Optional): A child node, if exists.
            Defaults to None.
        op_type(OpType): OpType refers to whether the child is an object selector or an array selector

    Examples:

        ```python
        # Simple attribute lookup on a dictionary
        root_node = ExpressionNode.build("person.name")
        data = {'person': {'name': 'Alice'}}
        value = root_node.get_value(data)
        print(value)  # Expected Output: Alice
        ```

        ```python
        # Optional attribute lookup on a dictionary
        root_node = ExpressionNode.build("person.name?")
        data = {'person': {}}
        value = root_node.get_value(data)
        print(value)  # Expected Output: None
        ```

        ```python
        # Simple attribute lookup on a class instance
        root_node = ExpressionNode.build("company.CEO.name")
        class Person:
            def __init__(self, name):
                self.name = name
        class Company:
            def __init__(self, CEO):
                self.CEO = CEO
        CEO = Person("Alice")
        company_instance = Company(CEO)
        value = root_node.get_value(company_instance)
        print(value)  # Expected Output: Alice
        ```

        ```python
        # Optional attribute lookup on a class instance
        root_node = ExpressionNode.build("company.CFO.name?")
        class Company:
            def __init__(self, CEO):
                self.CEO = CEO
                self.CFO = None
        CEO = Person("Alice")
        company_instance = Company(CEO)
        value = root_node.get_value(company_instance)
        print(value)  # Expected Output: None
        ```

        ```python
        # Nested dot-separated with array index
        root_node = ExpressionNode.build("students[0].name")
        data = {'students': [{'name': 'Alice'}, {'name': 'Bob'}]}
        value = root_node.get_value(data)
        print(value)  # Expected Output: Alice
        ```

        ```python
        # Nested dot-separated with multiple array indices
        root_node = ExpressionNode.build("matrix[0][1]")
        data = {'matrix': [[1, 2], [3, 4]]}
        value = root_node.get_value(data)
        print(value)  # Expected Output: 2
        ```
    """

    def __init__(
            self,
            expression: Optional[str],
            full_expression: str,
            op_type: OpType,
            default=NonExistent,
            parent: "ExpressionNode" = None
    ):
        """
        Initializes an ExpressionNode object.

        Args:
            expression (str): The main expression this node represents.
            full_expression (str): The full expression that includes
                all parent nodes. Useful to provide meaningful error message
            default (Any, Optional): A default value for the expression.
                Defaults to None. `default` is used to get the value when exception is raised



        """
        # Initialize the main and full expression attributes
        if expression is not None:
            expression = clean_expression(expression)
            if not expression:
                raise InvalidSourceExpression("Empty `""` String Source is not valid")

        self.expression = expression
        self.full_expression = full_expression
        self.parent = parent
        # Initialize optional, source, and array_index attributes
        self.optional = False
        self.source = None
        self.op_type = op_type
        self._default = default
        # Set the default value
        # Check if the node is optional and remove the optional suffix from the expression
        if self.expression:
            self.optional = True if default is not NonExistent else expression.endswith("?")
            # Split the expression to extract array indices and the source attribute
            self.source = SourceNode(expression, self.op_type)
            # Initialize child to None; will be set later if required
            self.child = None
        else:
            self._default = None

    @property
    def default(self):
        if self.optional:
            return None if (self._default is NonExistent or self._default is Empty) else self._default
        return self._default

    def __validate(
            self,
            instance,
    ):
        """
        Validates a value based on certain conditions.

        Args:
            instance (Any): The value to validate.

        Returns:
            Any: The validated value.

        Raises:
            ValueDoesNotExist: If the value does not exist and optional flag is False.
            ValueError: If the value is not iterable but an array index is set.
        """
        if instance is NonExistent:
            raise ValueDoesNotExist(
                "Value doesn't exist for source `{}` at key `{}`".format(
                    self.full_expression, self.source
                )
            )
        self.validate(instance)
        return instance

    def get_node_value(self, instance: Any):
        """
        Retrieves the node's value based on its attributes and the given instance.

        Args:
            instance (Any): The instance to get the value from.

        Returns:
            Any: The retrieved value.
        """
        # Retrieve value based on whether the instance is a Mapping or a custom object
        value = self.default
        if self.source.source_op_type == SourceOpType.ARRAY_INDEX_SELECT:
            if is_iterable(instance):
                try:
                    value = instance[self.source.getter]
                except IndexError:
                    value = self.default

        elif self.source.source_op_type == SourceOpType.CHILD_OBJ_SELECT:
            if isinstance(instance, Mapping):
                # For dictionary-like objects
                value = instance.get(self.source.getter, self.default)
            else:
                # For custom objects
                try:
                    value = getattr(instance, self.source.getter)
                    if is_callable(value):
                        value = value()
                except AttributeError:
                    value = self.default
        else:
            raise InvalidSourceExpression(
                "The expression `{}` failed to parse and get value for given data".format(
                    self.full_expression
                )
            )

        # Validate the retrieved value
        self.__validate(value)
        return value

    def validate(self, value):
        """
        Validator to extend in subclasses, doesn't return anything
        Args:
            value:

        Returns:

        """

    def get(self, instance: Any = None, root_instance: Any = None):
        """
        Retrieves the node's value recursively, traversing any child nodes.

        Args:
            root_instance: The root object/data that is given to get the value using the built expression
            instance (Any): The instance is the modified value from the root instance, it is later returned.

        Returns:
            Any: The final retrieved value.
        """
        # Retrieve the value for the current node

        if not root_instance:
            root_instance = instance
        if not self.source:
            return self.default
        if self.source.source_op_type not in SourceOpType.array_op_type:
            instance = self.get_node_value(instance)
            if self.child and instance is not None:
                return self.child.get(instance, root_instance)
            return instance
        else:
            r_val = EArray(self.source.unique_array)
            getter = self.source.getter
            getter_parent_str = '[]' if not self.parent and self.parent.source else str(self.parent.source.getter)
            if self.source.source_op_type == SourceOpType.ARRAY_SLICE_SELECT:
                start = 0 if getter[0] is None else getter[0]
                end = len(instance) if getter[1] is None else getter[1]
                step = 1 if getter[2] is None else getter[2]
                try:
                    instance = instance[start:end:step]
                except Exception:
                    tb = traceback.format_exc()
                    raise InvalidDataType(
                        "Unable to slice the dataset for `{}` with slice `{}`, original exception was {}".format(
                            self.full_expression,
                            getter_parent_str,
                            tb
                        ))
            if self.child:
                if not is_iterable(instance):
                    raise InvalidDataType(
                        "Invalid iterable `{}` at key `{}`".format(
                            self.full_expression,
                            getter_parent_str
                        )
                    )

                for each_instance in instance:
                    child_val = self.child.get(each_instance, root_instance)
                    if type(child_val) is not list:
                        r_val.insert(child_val)
                    else:
                        r_val += child_val
            else:
                return instance

    @classmethod
    def build(cls, expression: str, default=NonExistent) -> Optional["ExpressionNode"]:
        """
        Constructs a linked list of ExpressionNode objects based on a given expression string.

        This method recursively parses the input expression string and creates a tree of
        ExpressionNode objects, each representing a segment of the expression, starting
        from the root node.

        Args:
            expression (str): The expression string to parse. This is a dot-separated string
                              that can also contain array indices, e.g., "a.b[0].c".
            default: The default value to set in each ExpressionNode object.
                     This value is used when an attribute or index does not exist during
                     the evaluation of the expression.

        Returns:
            ExpressionNode: The root node of the ExpressionNode tree, or None if the
                            expression is empty.

        Example:

            To construct an expression tree for the string "a.b.c":

            >>> root_node = ExpressionNode.build("a.b.c")


            To construct an expression tree for the string "a.b[0].c":

            >>> root_node = ExpressionNode.build("a.b[0].c")

        Notes:
            The method handles optional attributes and nested attributes, and can be used
            to later evaluate these expressions against various types of data structures.
        """
        # Initialize variables to keep track of the root and current node
        root = None
        current = None
        start = 0
        index = 0
        in_brackets = False
        br_margin = 0
        exp_len = len(expression)
        while index < exp_len:
            if (
                    expression[index] in Token.seperator_tokens or
                    expression[index] in Token.unr_operators or
                    index == exp_len - 1
            ):
                end = index + 1 if index == exp_len - 1 else index
                op_type = OpType.ARRAY if in_brackets else OpType.OBJ
                sub_expression = clean_expression(expression[start:end])
                start = index + 1
                if sub_expression:
                    node = cls(sub_expression, expression, op_type, default=default, parent=current)
                    if not root:
                        root = node
                    if current:
                        current.child = node
                    current = node
                if expression[index] == Token.LSB:
                    if in_brackets:
                        raise InvalidSourceExpression(
                            "`{}` Syntax error in source expression, Array index must be in the following pattern "
                            "`item[n]`".format(expression)
                        )
                    in_brackets = True
                    br_margin += 1

                elif expression[index] == Token.RSB:
                    if not in_brackets:
                        raise InvalidSourceExpression(
                            "`{}` Syntax error in source expression, Array index must be in the following pattern "
                            "`item[n]`".format(expression)
                        )
                    in_brackets = False
                    br_margin -= 1

                elif expression[index] == Token.Q_MARK:
                    # For optional chaining for array operation
                    if current:
                        current.optional = True

                elif expression[index] == Token.UP_CARET:
                    # For unique array
                    if current and current.source:
                        if current.op_type != OpType.ARRAY:
                            raise InvalidSourceExpression(
                                "`{}` `^` Unique operation is only possible with iterable element".format(
                                    expression
                                )
                            )
                        current.source.unique_array = True

                else:
                    if index < exp_len - 2:
                        if expression[index + 1] == "[":
                            raise InvalidSourceExpression(
                                "`{}` Syntax error in source expression, Cannot contain array index after `.` operator"
                                "".format(expression)
                            )

            index += 1

        if br_margin > 0:
            raise InvalidSourceExpression(
                "`{}` Syntax error in source expression, contains uneven array index operator `[` , `]`"
            )

        return root


if __name__ == "__main__":
    # data = {
    #     'sections': [
    #         {
    #             'layout_content': {
    #                 'medias': [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    #             }
    #         },
    #         {
    #             'layout_content': {
    #                 'medias': [{"id": 4, "name": "Conan"}, {"id": 5, "name": "David"}]
    #             }
    #         }
    #     ]
    # }
    #
    # datav2 = {
    #     'sections': [
    #         {
    #             'medias': [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    #         },
    #         {
    #             'medias': [{"id": 4, "name": "Conan"}, {"id": 5, "name": "David"}]
    #         }
    #     ]
    # }
    #
    # a = {
    #     "x": [
    #         [1, 2, 3],
    #         [4, 5, 6]
    #     ]
    # }
    # b = "x[0][*]"
    #
    #
    # class E:
    #     def __init__(self, *args, **kwargs):
    #         pass
    #
    #
    # b = E("sections.something", default=[], cast=list, flat=True, conditions=[])
    # d = [
    #
    # ]
    #
    # __t = {
    #     ""
    # }

    root = ExpressionNode.build("a.b.c[0:2:1]")
    test_dict = {"a": {"b": {"c": [1, 2, 3, 4]}}}
    print(root.get(test_dict))
