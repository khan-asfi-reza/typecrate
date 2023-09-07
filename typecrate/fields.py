import warnings
from collections import OrderedDict
from typing import Any, Callable, Dict, Iterable, List, Optional

from typecrate.datatype import Empty, Null


class Type:
    """
    Type Class combines all fields
    """

    pass


def is_list_or_tuple(value: Any) -> bool:
    """
    Checks if the value is a list or a tuple
    :param value: Value that needs to be validated
    :return: bool
    """
    return value and (isinstance(value, list) or isinstance(value, tuple))


def create_list_if_none(value: Any) -> List:
    """
    Creates an empty list if the given value is None or Null,
    :param value: Value to be converted to a list or None
    :return: List
    """
    return [] if value is None else list(value)


def warn(_logic: bool, warning_msg):
    """
    Warns in the cli
    :param _logic: Logic to check
    :param warning_msg: Warning msg
    :return: Noting
    """
    if _logic:
        warnings.warn(warning_msg, Warning)


# Adapted from: django-rest-framework/serializers
NOT_READ_ONLY_WRITE_ONLY = "May not set both `read_only` and `write_only`"
NOT_READ_ONLY_REQUIRED = "May not set both `read_only` and `required`"
NOT_REQUIRED_DEFAULT = "May not set both `required` and `default`"


# Adapted from: django-rest-framework/serializers
def to_choices_dict(choices: Iterable) -> Dict:
    """
    Convert choices into key/value dicts.

    to_choices_dict([1]) -> {1: 1}
    to_choices_dict([(1, '1st'), (2, '2nd')]) -> {1: '1st', 2: '2nd'}
    to_choices_dict([('Group', ((1, '1st'), 2))]) -> {'Group': {1: '1st', 2: '2'}}

    :param choices: List or choices
    :return: Dictionary of choices
    """
    # Allow single, paired or grouped choices style:
    # choices = [1, 2, 3]
    # choices = [(1, 'First'), (2, 'Second'), (3, 'Third')]
    # choices = [('Category', ((1, 'First'), (2, 'Second'))), (3, 'Third')]
    ret = OrderedDict()
    for choice in choices:
        if not isinstance(choice, (list, tuple)):
            # single choice
            ret[choice] = choice
        else:
            key, value = choice
            if isinstance(value, (list, tuple)):
                # grouped choices (category, sub choices)
                ret[key] = to_choices_dict(value)
            else:
                # paired choice (key, display value)
                ret[key] = value
    return ret


# Adapted from: django-rest-framework/serializers
def flatten_choices_dict(choices: Dict) -> Dict:
    """
    Convert a group choices dict into a flat dict of choices.

    flatten_choices_dict({1: '1st', 2: '2nd'}) -> {1: '1st', 2: '2nd'}
    flatten_choices_dict({'Group': {1: '1st', 2: '2nd'}}) -> {1: '1st', 2: '2nd'}

    :param choices: Dictionary of choices
    :return: Flat choice dictionary
    """
    ret = OrderedDict()
    for key, value in choices.items():
        if isinstance(value, dict):
            # grouped choices (category, sub choices)
            for sub_key, sub_value in value.items():
                ret[sub_key] = sub_value
        else:
            # choice (key, display value)
            ret[key] = value
    return ret


def ErrorMsg(field: str, error_msg: str, help_text: str) -> Dict[str, str]:
    """
    Standard error message builder
    :param field: The field where the error was captured
    :param error_msg: Descriptive error
    :param help_text: Descriptive help message
    :return: Dictionary of Errors
    """
    return {
        "error": field if field else "non_field",
        "message": error_msg,
        "help": help_text,
    }


class ValidationError(Exception):
    def __init__(self, msg: Any, *args):
        self.msg = msg
        super(ValidationError, self).__init__(msg, *args)


def required_validator(value: Any, field: str = "", help_text: str = ""):
    """
    Checks if a value is empty or not
    :param value: The given value to check
    :param field: The field where the error occurred
    :param help_text: Descriptive error message
    :return:
    """
    if value is None or value is Empty:
        raise ValidationError(
            ErrorMsg(
                field=field if field else "non_field",
                error_msg="`{0}` must not be null".format(field),
                help_text=help_text,
            )
        )


def null_validator(value: Any, field: str = "", help_text: str = ""):
    """
    Validates if the value is null or not
    :param value: The given value to check
    :param field: The field where the error occurred
    :param help_text:
    :return: Nothing
    :rtype: None
    :raises ValidationError
    :raise ValidationError
    """
    if value is None or value is Null:
        raise ValidationError(
            ErrorMsg(
                field=field if field else "non_field",
                error_msg="`{0}` must not be null".format(field),
                help_text=help_text,
            )
        )


"""
Tree -> 
Node 1 -> Node 2
       -> Node 3
       -> Node 4 -> Node 5

Node1|Node2|Node3|Node4.Node5

"""


def parse_source(source: str):
    """
    Parse source and create source tree.

    Convert `A.B.C`
    Source tree -> A -> B -> C
    Which will later run operation on a data in the following manner
    in a dictionary

    Example::
        >> x = {"a": {"b": {"c": "TypeCrate"}}
        >> x["a"]["b"]["c"]

    Convert `A.B?.C?`
    B and C is optional
    Similar to javascript's object

    ```
    let a = {a: {}}

    a.b?.c? [ Null ]
    ```
    Source tree -> A -> B? -> C?

    :param source:
    :return:
    """


class Field:
    def __init__(
        self,
        _type,
        *,
        source=None,
        default=Empty,
        nullable=False,
        required=True,
        optional=False,
        validators=None,
        choices=None,
        read_only=False,
        write_only=False,
        help_text="",
        error_help_text="",
        value_processor=lambda val: val,
    ):
        if required is None:
            required = default is Empty and not read_only

        # Some combinations of keyword arguments do not make sense.
        # Adapted from: django-rest-framework/serializers
        assert not (read_only and write_only), NOT_READ_ONLY_WRITE_ONLY
        assert not (read_only and required), NOT_READ_ONLY_REQUIRED
        assert not (required and default is not Empty), NOT_REQUIRED_DEFAULT

        self._type = _type
        self.source = self.__class__.__name__ if not source else source
        self.default = default
        self.nullable = nullable

        self.required = required
        self.optional = optional

        if is_list_or_tuple(validators):
            raise TypeError("`validators` must be list or tuple")
        self._validators = create_list_if_none(validators)

        if is_list_or_tuple(choices):
            raise TypeError("`choices` must be list or tuple")
        self.choices = create_list_if_none(choices)

        self.read_only = read_only
        self.write_only = write_only
        self.help_text = help_text
        self.error_help_text = error_help_text

        self.parent = None
        self.field_name = None
        self.source_root = None

        if not callable(value_processor):
            raise TypeError("`value_processor` must be a callable/function")
        self.value_processor = value_processor

    def __get_validators(self) -> List[Callable]:
        """
        Get validators
        Check if null_validation is required
        and required_validation is required
        :return: List of validators
        """
        validators = []
        if self.required:
            validators.append(required_validator)
        if self.nullable:
            validators.append(null_validator)
        return validators

    def get_default_validators(self) -> Optional[List]:
        """
        Default validators for inheritance
        :return: Default validators
        """

    @property
    def validators(self):
        """
        Validators is a lazily loaded property
        Initially loads the validators from `__get_validators()`
        Also checks for validators in `default_validators`
        `default_validators` is for future classes to validate
        :return:
        """
        validators = self.__get_validators()
        validators += self._validators
        default_validators = self.get_default_validators()
        if default_validators:
            validators += default_validators
        return validators

    def bind(self, field_name: str, parent: Any):
        self.field_name = field_name
        self.parent = parent
        if not self.source:
            self.source = field_name
