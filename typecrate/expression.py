import string
import traceback
from collections.abc import Mapping
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from typecrate.datatype import Empty, NonExistent
from typecrate.exceptions import ValueDoesNotExist, InvalidSourceExpression
from typecrate.utils import is_callable, is_iterable


class OpType(Enum):
    # Refers to [0]/[-1]/[1:2]/[*]/[@len-1] indexed child
    ARRAY = "ARRAY"
    # Refers to . seperated child
    OBJ = "OBJ"
    # None
    NULL = "NULL"


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
        fallback (Any): A default value to use if the expression fails.
        parameters (Tuple, List): Positional arguments to be passed
            when calling callable attributes.
        keywords (Dict): Keyword arguments to be passed when calling
            callable attributes.
        source (str, Optional): The source attribute, derived from
            the expression.
        optional (bool): A flag to denote if the node is optional. Defaults
            to False.
        child (ExpressionNode, Optional): A child node, if exists.
            Defaults to None.
        op_type(OpType):
            
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
            expression: str,
            full_expression: str,
            op_type: OpType,
            fallback=None,
            parameters: Optional[Union[Tuple, List]] = None,
            keywords: Optional[Dict] = None,
    ):
        """
        Initializes an ExpressionNode object.

        Args:
            expression (str): The main expression this node represents.
            full_expression (str): The full expression that includes
                all parent nodes. Useful to provide meaningful error message
            fallback (Any, Optional): A fallback value for the expression.
                Defaults to None. `fallback` is used to get the value when exception is raised
            parameters (Union[Tuple, List], Optional): Positional arguments
                to be passed when evaluating callable attributes. Defaults to None.
            keywords (Dict, Optional): Keyword arguments to be passed when
                evaluating callable attributes. Defaults to None.

        """
        # Initialize the main and full expression attributes
        self.expression = expression
        self.full_expression = full_expression

        # Set default values for parameters and keywords if not provided
        self.parameters = tuple(parameters) if parameters else ()
        self.keywords = keywords if keywords else {}

        # Initialize optional, source, and array_index attributes
        self.optional = False
        self.source = None
        self.op_type = op_type

        # Check if the node is optional and remove the optional suffix from the expression
        if self.expression:
            self.optional = expression.endswith("?")
            expression = expression.removesuffix("?")
            # Split the expression to extract array indices and the source attribute
            self.source = self.set_source(expression)
            # Initialize child to None; will be set later if required
            self.child = None

        # Set the fallback value
        self.fallback = fallback

    def set_source(self, source: str):
        if self.op_type == OpType.OBJ:
            return source
        elif self.op_type == OpType.ARRAY:
            source = source.removesuffix("]").removeprefix("[")

            if ":" in source and "," in source:
                raise InvalidSourceExpression(
                    "`[{}]` Invalid expression,"
                    "Both slice operation(`[start:end:step]`) and index multiple select operation(`[1,2]`) is not "
                    "supported "
                    "".format(source)
                )
            if ":" in source:
                try:
                    source = list(map(int, source.split(":")))
                    if len(source) > 3:
                        raise InvalidSourceExpression(
                            "Invalid slice operation `{}` performed, the slice operation must follow `[start:end:step]`"
                            "format"
                        )
                    return source
                except ValueError:
                    tb = traceback.format_exc()
                    raise InvalidSourceExpression(
                        "Invalid source `[{}]`,"
                        "Slice operator must have integers, original exception was \n{}".format(source, tb)
                    )
            if "," in source:
                try:
                    source = list(map(int, source.split(",")))
                    return source
                except ValueError:
                    tb = traceback.format_exc()
                    raise InvalidSourceExpression(
                        "Invalid source `[{}]`,"
                        "Multi index selector must have integers, original exception was \n{}".format(source, tb)
                    )
            if source in string.digits + "*":
                if source in string.digits:
                    return int(source)
                return source
        return None

    def get_value_from_array(self, instance: Any):
        """
        Retrieves the value from an array using the node's array_index attribute.

        Args:
            instance (Any): The instance containing the array.

        Returns:
            Any: The retrieved value.

        Raises:
            ValueDoesNotExist: If the value does not exist and optional flag is False.
        """
        # Initialize val to Empty or NonExistent based on whether the node is optional
        val = instance

        # Loop through the array indices specified in array_index
        loop_level = 0
        for index in self.array_index:
            try:
                # Retrieve the value at the current index
                if index == "*":
                    loop_level += 1
                else:
                    if loop_level > 0:
                        for loop in range(0, loop_level + 1):
                            instance = 1
            except IndexError:
                if val is NonExistent:
                    # Raise exception if the value doesn't exist and optional is False
                    raise ValueDoesNotExist(
                        "Value doesn't exist for source `{}` -> `{}{}` at index `{}`".format(
                            self.full_expression,
                            self.source,
                            str(
                                list(
                                    map(
                                        lambda idx: "[{}]".format(idx), self.array_index
                                    )
                                )
                            ),
                            self.array_index,
                        )
                    )
        return val

    def validate_value(
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
        if isinstance(instance, Mapping):
            # For dictionary-like objects
            default = Empty if self.optional else NonExistent
            value = instance.get(self.source, default)
        else:
            # For custom objects
            try:
                value = getattr(instance, self.source)
                if is_callable(value):
                    value = value(*self.parameters, **self.keywords)
            except AttributeError:
                value = Empty if self.optional else NonExistent

        # Validate the retrieved value
        value = self.validate_value(value)

        # Retrieve value from array if array_index is set
        return value

    def get_value(self, instance: Any):
        """
        Retrieves the node's value recursively, traversing any child nodes.

        Args:
            instance (Any): The instance to get the value from.

        Returns:
            Any: The final retrieved value.
        """
        # Retrieve the value for the current node
        if not self.source:
            return self.fallback
        try:
            instance = self.get_node_value(instance)
        except ValueDoesNotExist as exception:
            if self.fallback:
                return self.fallback
            raise exception
        # Return None if the value is Empty
        if instance is Empty:
            return None

        # Recursively retrieve the value from child nodes, if any
        if self.child:
            instance = self.child.get_value(instance)
            if instance is Empty:
                return None

        return instance

    @classmethod
    def build(cls, expression: str, default=None) -> Optional["ExpressionNode"]:
        """
        Constructs a linked list of ExpressionNode objects based on a given expression string.

        This method recursively parses the input expression string and creates a tree of
        ExpressionNode objects, each representing a segment of the expression, starting
        from the root node.

        Args:
            expression (str): The expression string to parse. This is a dot-separated string
                              that can also contain array indices, e.g., "a.b[0].c".
            default: The default fallback value to set in each ExpressionNode object.
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
        op_type = OpType.OBJ  # Start with object type by default
        in_brackets = False
        br_margin = 0
        exp_len = len(expression)
        while index < exp_len:
            if expression[index] in [".", "[", "]"] or index == exp_len - 1:
                end = index + 1 if index == exp_len - 1 else index
                _op_type = OpType.ARRAY if in_brackets else OpType.OBJ
                sub_expression = expression[start:end]
                start = index + 1
                if sub_expression:
                    node = cls(sub_expression, expression, _op_type, fallback=default)
                    if not root:
                        root = node
                    if current:
                        current.child = node
                    current = node
                if expression[index] == "[":
                    if in_brackets:
                        raise InvalidSourceExpression(
                            "`{}` Syntax error in source expression, Array index must be in the following pattern "
                            "`item[n]`".format(expression)
                        )
                    in_brackets = True
                    br_margin += 1

                elif expression[index] == "]":
                    if not in_brackets:
                        raise InvalidSourceExpression(
                            "`{}` Syntax error in source expression, Array index must be in the following pattern "
                            "`item[n]`".format(expression)

                        )
                    in_brackets = False
                    br_margin -= 1

                else:
                    if index < exp_len - 2:
                        if expression[index+1] == "[":
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
    # b = E("sections.something", fallback=[], cast=list, flat=True, conditions=[])
    # d = [
    #
    # ]
    #
    # __t = {
    #     ""
    # }

    roots = ExpressionNode.build("a[0][1]")
    print(roots)
