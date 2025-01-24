from __future__ import annotations

import numbers
import typing

from pyrsistent import pmap
import attr

from jsonschema.exceptions import UndefinedTypeCheck


# unfortunately, the type of pmap is generic, and if used as the attr.ib
# converter, the generic type is presented to mypy, which then fails to match
# the concrete type of a type checker mapping
# this "do nothing" wrapper presents the correct information to mypy
def _typed_pmap_converter(
    init_val: typing.Mapping[
        str,
        typing.Callable[["TypeChecker", typing.Any], bool],
    ],
) -> typing.Mapping[str, typing.Callable[["TypeChecker", typing.Any], bool]]:
    return typing.cast(
        typing.Mapping[
            str,
            typing.Callable[["TypeChecker", typing.Any], bool],
        ],
        pmap(init_val),
    )


def is_array(checker, instance):
    return isinstance(instance, list)


def is_bool(checker, instance):
    return isinstance(instance, bool)


def is_integer(checker, instance):
    # bool inherits from int, so ensure bools aren't reported as ints
    if isinstance(instance, bool):
        return False
    return isinstance(instance, int)


def is_null(checker, instance):
    return instance is None


def is_number(checker, instance):
    # bool inherits from int, so ensure bools aren't reported as ints
    if isinstance(instance, bool):
        return False
    return isinstance(instance, numbers.Number)


def is_object(checker, instance):
    return isinstance(instance, dict)


def is_string(checker, instance):
    return isinstance(instance, str)


def is_any(checker, instance):
    return True


@attr.s(frozen=True)
class TypeChecker(object):
    """
    A ``type`` property checker.

    A `TypeChecker` performs type checking for a `Validator`. Type
    checks to perform are updated using `TypeChecker.redefine` or
    `TypeChecker.redefine_many` and removed via `TypeChecker.remove`.
    Each of these return a new `TypeChecker` object.

    Arguments:

        type_checkers (dict):

            The initial mapping of types to their checking functions.
    """

    _type_checkers: typing.Mapping[
        str, typing.Callable[["TypeChecker", typing.Any], bool],
    ] = attr.ib(
        default=pmap(),
        converter=_typed_pmap_converter,
    )

    def is_type(self, instance, type):
        """
        Check if the instance is of the appropriate type.

        Arguments:

            instance (object):

                The instance to check

            type (str):

                The name of the type that is expected.

        Returns:

            bool: Whether it conformed.


        Raises:

            `jsonschema.exceptions.UndefinedTypeCheck`:
                if type is unknown to this object.
        """
        try:
            fn = self._type_checkers[type]
        except KeyError:
            raise UndefinedTypeCheck(type) from None

        return fn(self, instance)

    def redefine(self, type, fn):
        """
        Produce a new checker with the given type redefined.

        Arguments:

            type (str):

                The name of the type to check.

            fn (collections.abc.Callable):

                A function taking exactly two parameters - the type
                checker calling the function and the instance to check.
                The function should return true if instance is of this
                type and false otherwise.

        Returns:

            A new `TypeChecker` instance.
        """
        return self.redefine_many({type: fn})

    def redefine_many(self, definitions=()):
        """
        Produce a new checker with the given types redefined.

        Arguments:

            definitions (dict):

                A dictionary mapping types to their checking functions.

        Returns:

            A new `TypeChecker` instance.
        """
        return attr.evolve(
            self, type_checkers=self._type_checkers.update(definitions),
        )

    def remove(self, *types):
        """
        Produce a new checker with the given types forgotten.

        Arguments:

            types (~collections.abc.Iterable):

                the names of the types to remove.

        Returns:

            A new `TypeChecker` instance

        Raises:

            `jsonschema.exceptions.UndefinedTypeCheck`:

                if any given type is unknown to this object
        """

        checkers = self._type_checkers
        for each in types:
            try:
                checkers = checkers.remove(each)
            except KeyError:
                raise UndefinedTypeCheck(each)
        return attr.evolve(self, type_checkers=checkers)


draft3_type_checker = TypeChecker(
    {
        "any": is_any,
        "array": is_array,
        "boolean": is_bool,
        "integer": is_integer,
        "object": is_object,
        "null": is_null,
        "number": is_number,
        "string": is_string,
    },
)
draft4_type_checker = draft3_type_checker.remove("any")
draft6_type_checker = draft4_type_checker.redefine(
    "integer",
    lambda checker, instance: (
        is_integer(checker, instance)
        or isinstance(instance, float) and instance.is_integer()
    ),
)
draft7_type_checker = draft6_type_checker
draft201909_type_checker = draft7_type_checker
draft202012_type_checker = draft201909_type_checker
