"""
event-stream library for `awscrt`.
"""

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from enum import IntEnum
from typing import Any, Union
from uuid import UUID

__all__ = ['HeaderType', 'Header']


_BYTE_MIN = -2**7
_BYTE_MAX = 2**7 - 1
_INT16_MIN = -2**15
_INT16_MAX = 2**15 - 1
_INT32_MIN = -2**31
_INT32_MAX = 2**31 - 1
_INT64_MIN = -2**63
_INT64_MAX = 2**63 - 1


class HeaderType(IntEnum):
    """Supported types for the value within a Header"""

    BOOL_TRUE = 0
    """Value is True.

    No actual value is transmitted on the wire."""

    BOOL_FALSE = 1
    """Value is False.

    No actual value is transmitted on the wire."""

    BYTE = 2
    """Value is signed 8-bit int."""

    INT16 = 3
    """Value is signed 16-bit int."""

    INT32 = 4
    """Value is signed 32-bit int."""

    INT64 = 5
    """Value is signed 64-bit int."""

    BYTE_BUF = 6
    """Value is raw bytes."""

    STRING = 7
    """Value is a str.

    Transmitted on the wire as utf-8"""

    TIMESTAMP = 8
    """Value is a posix timestamp (seconds since Unix epoch).

    Transmitted on the wire as a 64-bit int"""

    UUID = 9
    """Value is a UUID.

    Transmitted on the wire as 16 bytes"""

    def __format__(self, format_spec):
        # override so formatted string doesn't simply look like an int
        return str(self)


class Header:
    """A header in an event-stream message.

    Each header has a name, value, and type.
    :class:`HeaderType` enumerates the supported value types.

    Create a header with one of the Header.from_X() functions.
    """

    def __init__(self, name: str, value: Any, header_type: HeaderType):
        # do not call directly, use Header.from_xyz() methods.
        self._name = name
        self._value = value
        self._type = header_type

    @classmethod
    def from_bool(cls, name: str, value: bool) -> 'Header':
        """Create a Header of type :attr:`~HeaderType.BOOL_TRUE` or :attr:`~HeaderType.BOOL_FALSE`"""
        if value:
            return cls(name, True, HeaderType.BOOL_TRUE)
        else:
            return cls(name, False, HeaderType.BOOL_FALSE)

    @classmethod
    def from_byte(cls, name: str, value: int) -> 'Header':
        """Create a Header of type :attr:`~HeaderType.BYTE`

        The value must fit in an 8-bit signed int"""
        value = int(value)
        if value < _BYTE_MIN or value > _BYTE_MAX:
            raise ValueError("Value {} cannot fit in signed 8-bit byte".format(value))
        return cls(name, value, HeaderType.BYTE)

    @classmethod
    def from_int16(cls, name: str, value: int) -> 'Header':
        """Create a Header of type :attr:`~HeaderType.INT16`

        The value must fit in an 16-bit signed int"""
        value = int(value)
        if value < _INT16_MIN or value > _INT16_MAX:
            raise ValueError("Value {} cannot fit in signed 16-bit int".format(value))
        return cls(name, value, HeaderType.INT16)

    @classmethod
    def from_int32(cls, name: str, value: int) -> 'Header':
        """Create a Header of type :attr:`~HeaderType.INT32`

        The value must fit in an 32-bit signed int"""
        value = int(value)
        if value < _INT32_MIN or value > _INT32_MAX:
            raise ValueError("Value {} cannot fit in signed 32-bit int".format(value))
        return cls(name, value, HeaderType.INT32)

    @classmethod
    def from_int64(cls, name: str, value: int) -> 'Header':
        """Create a Header of type :attr:`~HeaderType.INT64`

        The value must fit in an 64-bit signed int"""
        value = int(value)
        if value < _INT64_MIN or value > _INT64_MAX:
            raise ValueError("Value {} cannot fit in signed 64-bit int".format(value))
        return cls(name, value, HeaderType.INT64)

    @classmethod
    def from_byte_buf(cls, name: str, value: Union[bytes, bytearray]) -> 'Header':
        """Create a Header of type :attr:`~HeaderType.BYTE_BUF`

        The value must be a bytes-like object"""
        return cls(name, value, HeaderType.BYTE_BUF)

    @classmethod
    def from_string(cls, name: str, value: str) -> 'Header':
        """Create a Header of type :attr:`~HeaderType.STRING`"""
        value = str(value)
        return cls(name, value, HeaderType.STRING)

    @classmethod
    def from_timestamp(cls, name: str, value: int) -> 'Header':
        """Create a Header of type :attr:`~HeaderType.TIMESTAMP`

        Value must be a posix timestamp (seconds since Unix epoch)"""

        value = int(value)
        if value < _INT64_MIN or value > _INT64_MAX:
            raise ValueError("Value {} exceeds timestamp limits".format(value))
        return cls(name, value, HeaderType.TIMESTAMP)

    @classmethod
    def from_uuid(cls, name: str, value: UUID) -> 'Header':
        """Create a Header of type :attr:`~HeaderType.UUID`

        The value must be a UUID"""

        if not isinstance(value, UUID):
            raise TypeError("Value must be UUID, not {}".format(type(value)))
        return cls(name, value, HeaderType.UUID)

    @classmethod
    def _from_binding_tuple(cls, binding_tuple):
        # native code deals with a simplified tuple, rather than full class
        name, value, header_type = binding_tuple
        header_type = HeaderType(header_type)
        if header_type == HeaderType.UUID:
            value = UUID(bytes=value)
        return cls(name, value, header_type)

    def _as_binding_tuple(self):
        # native code deals with a simplified tuple, rather than full class
        if self._type == HeaderType.UUID:
            value = self._value.bytes
        else:
            value = self._value
        return (self._name, value, self._type)

    @property
    def name(self) -> str:
        """Header name"""
        return self._name

    @property
    def type(self) -> HeaderType:
        """Header type"""
        return self._type

    @property
    def value(self) -> Any:
        """Header value

        The header's type determines the value's type.
        Use the value_as_X() methods for type-checked queries."""
        return self._value

    def _value_as(self, header_type: HeaderType) -> Any:
        if self._type != header_type:
            raise TypeError("Header type is {}, not {}".format(self._type, header_type))
        return self._value

    def value_as_bool(self) -> bool:
        """Return bool value

        Raises an exception if type is not :attr:`~HeaderType.BOOL_TRUE` or :attr:`~HeaderType.BOOL_FALSE`"""
        if self._type == HeaderType.BOOL_TRUE:
            return True
        if self._type == HeaderType.BOOL_FALSE:
            return False
        raise TypeError(
            "Header type is {}, not {} or {}".format(
                self._type,
                HeaderType.BOOL_TRUE,
                HeaderType.BOOL_FALSE))

    def value_as_byte(self) -> int:
        """Return value of 8-bit signed int

        Raises an exception if type is not :attr:`~HeaderType.BYTE`"""
        return self._value_as(HeaderType.BYTE)

    def value_as_int16(self) -> int:
        """Return value of 16-bit signed int

        Raises an exception if type is not :attr:`~HeaderType.INT16`"""
        return self._value_as(HeaderType.INT16)

    def value_as_int32(self) -> int:
        """Return value of 32-bit signed int

        Raises an exception if type is not :attr:`~HeaderType.INT32`"""
        return self._value_as(HeaderType.INT32)

    def value_as_int64(self) -> int:
        """Return value of 64-bit signed int

        Raises an exception if type is not :attr:`~HeaderType.INT64`"""
        return self._value_as(HeaderType.INT64)

    def value_as_byte_buf(self) -> Union[bytes, bytearray]:
        """Return value of bytes

        Raises an exception if type is not :attr:`~HeaderType.BYTE_BUF`"""
        return self._value_as(HeaderType.BYTE_BUF)

    def value_as_string(self) -> str:
        """Return value of string

        Raises an exception if type is not :attr:`~HeaderType.STRING`"""
        return self._value_as(HeaderType.STRING)

    def value_as_timestamp(self) -> int:
        """Return value of timestamp (seconds since Unix epoch)

        Raises an exception if type is not :attr:`~HeaderType.TIMESTAMP`"""
        return self._value_as(HeaderType.TIMESTAMP)

    def value_as_uuid(self) -> UUID:
        """Return value of UUID

        Raises an exception if type is not :attr:`~HeaderType.UUID`"""
        return self._value_as(HeaderType.UUID)

    def __str__(self):
        return "{}: {} <{}>".format(
            self._name,
            repr(self._value),
            self._type.name)

    def __repr__(self):
        return "{}({}, {}, {})".format(
            self.__class__.__name__,
            repr(self._name),
            repr(self._value),
            repr(self._type))
