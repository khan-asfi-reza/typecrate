import math
import string


class MToken:
    """Defines constants for different types of mathematical tokens."""

    NUMBER = "NUMBER"  # Token type for numeric literals
    OPERATOR = "OPERATOR"  # Token type for operators
    FUNCTION = "FUNCTION"  # Token type for function names
    VARIABLE = "VARIABLE"  # Token type for variables
    EOF = "EOF"  # Token type for end-of-file marker


class MOperator:
    """Defines constants for different types of mathematical operators."""

    ADD = "+"  # Addition
    SUBTRACT = "-"  # Subtraction
    MULTIPLY = "*"  # Multiplication
    DIVIDE = "/"  # Division
    MODULO = "%"  # Modulo
    LPAREN = "("  # Left parenthesis
    RPAREN = ")"  # Right parenthesis


class MathParser:
    """
    A math parser to evaluate mathematical expressions.

    Attributes:
        tokens (list): A list of tokens parsed from the input.
        index (int): Current index in the list of tokens.
        paren_count (int): Count of parentheses to ensure matching.
        functions (dict): Mapping from function names to their implementations.
    """

    def __init__(self):
        """Initializes the parser object and supported functions."""
        self.tokens = []  # List to store tokens
        self.index = 0  # Index to navigate the list of tokens
        self.paren_count = 0  # Counter for parentheses
        # Map of supported function names to their actual implementations
        self.functions = {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "exp": math.exp,
        }

    def tokenize(self, expression):
        """
        Tokenizes an expression into numbers, operators, functions, and variables.

        Args:
            expression (str): The input expression to tokenize.

        Raises:
            ValueError: When an unrecognized character is encountered.
        """
        self.tokens = []  # Clear the token list
        self.index = 0  # Reset the index
        self.paren_count = 0  # Reset the parentheses count

        if not expression.strip():  # Check for empty input
            raise ValueError("Empty input provided.")

        i = 0
        while i < len(expression):
            # If the character is a digit or a decimal point
            if expression[i].isdigit() or (
                expression[i] == "."
                and i + 1 < len(expression)
                and expression[i + 1].isdigit()
            ):
                start = i  # Record the start index of the number
                while i < len(expression) and (
                    expression[i].isdigit() or expression[i] == "."
                ):
                    i += 1  # Increment index while it is a part of the number
                num_str = expression[start:i]
                num = (
                    float(num_str) if "." in num_str else int(num_str)
                )  # Parse as float if it contains '.', otherwise as int
                self.tokens.append((MToken.NUMBER, num))  # Append as a NUMBER token
            # If the character is an operator
            elif expression[i] in (
                MOperator.ADD,
                MOperator.SUBTRACT,
                MOperator.MULTIPLY,
                MOperator.DIVIDE,
                MOperator.MODULO,
                MOperator.LPAREN,
                MOperator.RPAREN,
            ):
                self.tokens.append(
                    (MToken.OPERATOR, expression[i])
                )  # Append as an OPERATOR token
                i += 1  # Move to the next character
            # If the character is an alphabetic character (function/variable)
            elif expression[i] in string.ascii_letters + "@{}":
                start = i  # Record the start index of the name
                while (
                    i < len(expression)
                    and expression[i] in string.ascii_letters + "@{}"
                ):
                    i += 1  # Increment index while it is a part of the name
                name = expression[start:i]
                if name in self.functions:
                    self.tokens.append(
                        (MToken.FUNCTION, name)
                    )  # Append as a FUNCTION token if it is a recognized function name
                else:
                    self.tokens.append(
                        (MToken.VARIABLE, name)
                    )  # Otherwise, append as a VARIABLE token
            # If the character is a space or tab, skip it
            elif expression[i] in " \t":
                i += 1
            else:
                raise ValueError(
                    f"Unknown character: {expression[i]}"
                )  # Raise an error for unrecognized characters

        self.tokens.append((MToken.EOF, None))  # Append an EOF token at the end

    def parse(self, expression, variables=None):
        """
        Parses and evaluates a mathematical expression.

        Args:
            expression (str): The expression to parse.
            variables (dict): Dictionary containing variable values.

        Returns:
            float: The evaluated result.
        """
        if variables is None:
            variables = {}
        self.tokenize(expression)  # Tokenize the input expression
        return self.expr(variables)  # Evaluate and return the result

    def consume(self, expected_type):
        """
        Consumes a token, checking its type.

        Args:
            expected_type (str): The expected token type to consume.

        Returns:
            value: The value of the consumed token.

        Raises:
            ValueError: When the token type doesn't match the expected type.
        """
        if (
            self.tokens[self.index][0] == expected_type
        ):  # Check if the current token type matches the expected type
            self.index += 1  # Move to the next token
            return self.tokens[self.index - 1][
                1
            ]  # Return the value of the consumed token
        else:
            raise ValueError(
                f"Expected {expected_type}, got {self.tokens[self.index][0]}"
            )  # Raise an error if types don't match

    def expr(self, variables):
        """
        Evaluates addition and subtraction expressions.

        Args:
            variables (dict): Dictionary containing variable values.

        Returns:
            float: The evaluated result.
        """
        result = self.term(variables)  # Start by evaluating the first term
        # Loop as long as we see addition or subtraction operators
        while self.tokens[self.index][0] == MToken.OPERATOR and self.tokens[self.index][
            1
        ] in (MOperator.ADD, MOperator.SUBTRACT):
            op = self.consume(MToken.OPERATOR)  # Consume the operator
            if op == MOperator.ADD:
                result += self.term(variables)  # Add the next term
            else:
                result -= self.term(variables)  # Subtract the next term
        return result

    def term(self, variables):
        """
        Evaluates multiplication, division, and modulo expressions.

        Args:
            variables (dict): Dictionary containing variable values.

        Returns:
            float: The evaluated result.
        """
        result = self.factor(variables)  # Start by evaluating the first factor
        # Loop as long as we see multiplication, division, or modulo operators
        while self.tokens[self.index][0] == MToken.OPERATOR and self.tokens[self.index][
            1
        ] in (MOperator.MULTIPLY, MOperator.DIVIDE, MOperator.MODULO):
            op = self.consume(MToken.OPERATOR)  # Consume the operator
            if op == MOperator.MULTIPLY:
                result *= self.factor(variables)  # Multiply by the next factor
            elif op == MOperator.DIVIDE:
                divisor = self.factor(variables)  # Divide by the next factor
                if divisor == 0:
                    raise ValueError("Division by zero")
                result /= divisor
            else:
                result %= self.factor(variables)  # Take modulo by the next factor
        return result

    def factor(self, variables):
        """
        Evaluates numbers, functions, and expressions inside parentheses.

        Args:
            variables (dict): Dictionary containing variable values.

        Returns:
            float: The evaluated result.
        """
        if self.tokens[self.index][0] == MToken.FUNCTION:  # If the token is a function
            func_name = self.consume(MToken.FUNCTION)  # Consume the function name
            self.consume(MToken.OPERATOR)  # Assume a '(' follows the function name
            arg = self.expr(variables)  # Evaluate the expression within the function
            self.consume(MToken.OPERATOR)  # Consume ')'
            return self.functions[func_name](
                arg
            )  # Call the function with the evaluated argument
        elif self.tokens[self.index][0] == MToken.OPERATOR and self.tokens[self.index][
            1
        ] in (
            MOperator.ADD,
            MOperator.SUBTRACT,
        ):  # If the token is a unary plus or minus
            op = self.consume(MToken.OPERATOR)  # Consume the operator
            num = self.factor(variables)  # Evaluate the factor after the unary operator
            return (
                num if op == MOperator.ADD else -num
            )  # Return the value, negated if necessary
        elif self.tokens[self.index][0] == MToken.NUMBER:  # If the token is a number
            return self.consume(MToken.NUMBER)  # Consume and return the number
        elif (
            self.tokens[self.index][0] == MToken.VARIABLE
        ):  # If the token is a variable
            var_name = self.consume(MToken.VARIABLE)  # Consume the variable name
            if var_name in variables:
                return variables[
                    var_name
                ]  # Return the value of the variable from the dictionary
            else:
                raise ValueError(
                    f"Unknown variable: {var_name}"
                )  # Raise an error for unknown variables
        elif (
            self.tokens[self.index][0] == MToken.OPERATOR
            and self.tokens[self.index][1] == MOperator.LPAREN
        ):  # If the token is a '('
            self.consume(MToken.OPERATOR)  # Consume '('
            result = self.expr(
                variables
            )  # Evaluate the expression within the parentheses
            self.consume(MToken.OPERATOR)  # Consume ')'
            return result  # Return the evaluated result
        else:
            raise ValueError(
                f"Unexpected token: {self.tokens[self.index][0]}"
            )  # Raise an error for any other token


if __name__ == "__main__":
    parser = MathParser()
    v = {"@x": 5, "@y": 10}
    print(parser.parse("sqrt(@y) + sin(@x)", v))  # Example usage with variables
