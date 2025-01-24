"""Helpers for use with type annotation.

Use the empty classes in this module when annotating the types of Pyrsistent
objects, instead of using the actual collection class.

For example,

    from pyrsistent import pvector
    from pyrsistent.typing import PVector

    myvector: PVector[str] = pvector(['a', 'b', 'c'])

"""
from __future__ import absolute_import

try:
    from typing import Container
    from typing import Hashable
    from typing import Generic
    from typing import Iterable
    from typing import Mapping
    from typing import Sequence
    from typing import Sized
    from typing import TypeVar

    __all__ = [
        'CheckedPMap',
        'CheckedPSet',
        'CheckedPVector',
        'PBag',
        'PDeque',
        'PList',
        'PMap',
        'PSet',
        'PVector',
    ]

    T = TypeVar('T')
    T_co = TypeVar('T_co', covariant=True)
    KT = TypeVar('KT')
    VT = TypeVar('VT')
    VT_co = TypeVar('VT_co', covariant=True)

    class CheckedPMap(Mapping[KT, VT_co], Hashable):
        pass

    # PSet.add and PSet.discard have different type signatures than that of Set.
    class CheckedPSet(Generic[T_co], Hashable):
        pass

    class CheckedPVector(Sequence[T_co], Hashable):
        pass

    class PBag(Container[T_co], Iterable[T_co], Sized, Hashable):
        pass

    class PDeque(Sequence[T_co], Hashable):
        pass

    class PList(Sequence[T_co], Hashable):
        pass

    class PMap(Mapping[KT, VT_co], Hashable):
        pass

    # PSet.add and PSet.discard have different type signatures than that of Set.
    class PSet(Generic[T_co], Hashable):
        pass

    class PVector(Sequence[T_co], Hashable):
        pass

    class PVectorEvolver(Generic[T]):
        pass

    class PMapEvolver(Generic[KT, VT]):
        pass

    class PSetEvolver(Generic[T]):
        pass
except ImportError:
    pass
