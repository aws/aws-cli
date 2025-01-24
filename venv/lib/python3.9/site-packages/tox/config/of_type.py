"""
Group together configuration values that belong together (such as base tox configuration, tox environment configs)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from itertools import product
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterable, TypeVar, cast

from tox.config.loader.api import ConfigLoadArgs, Loader
from tox.config.loader.convert import Factory

if TYPE_CHECKING:
    from tox.config.main import Config  # pragma: no cover


T = TypeVar("T")
V = TypeVar("V")


class ConfigDefinition(ABC, Generic[T]):
    """Abstract base class for configuration definitions"""

    def __init__(self, keys: Iterable[str], desc: str) -> None:
        self.keys = keys
        self.desc = desc

    @abstractmethod
    def __call__(self, conf: Config, loaders: list[Loader[T]], args: ConfigLoadArgs) -> T:
        raise NotImplementedError

    def __eq__(self, o: Any) -> bool:
        return type(self) == type(o) and (self.keys, self.desc) == (o.keys, o.desc)

    def __ne__(self, o: Any) -> bool:
        return not (self == o)


class ConfigConstantDefinition(ConfigDefinition[T]):
    """A configuration definition whose value is defined upfront (such as the tox environment name)"""

    def __init__(
        self,
        keys: Iterable[str],
        desc: str,
        value: Callable[[], T] | T,
    ) -> None:
        super().__init__(keys, desc)
        self.value = value

    def __call__(
        self,
        conf: Config,  # noqa: U100
        loaders: list[Loader[T]],  # noqa: U100
        args: ConfigLoadArgs,  # noqa: U100
    ) -> T:
        if callable(self.value):
            value = self.value()
        else:
            value = self.value
        return value

    def __eq__(self, o: Any) -> bool:
        return type(self) == type(o) and super().__eq__(o) and self.value == o.value


_PLACE_HOLDER = object()


class ConfigDynamicDefinition(ConfigDefinition[T]):
    """A configuration definition that comes from a source (such as in memory, an ini file, a toml file, etc.)"""

    def __init__(
        self,
        keys: Iterable[str],
        desc: str,
        of_type: type[T],
        default: Callable[[Config, str | None], T] | T,
        post_process: Callable[[T], T] | None = None,
        factory: Factory[T] = None,
    ) -> None:
        super().__init__(keys, desc)
        self.of_type = of_type
        self.default = default
        self.post_process = post_process
        self.factory = factory
        self._cache: object | T = _PLACE_HOLDER

    def __call__(
        self,
        conf: Config,
        loaders: list[Loader[T]],
        args: ConfigLoadArgs,
    ) -> T:
        if self._cache is _PLACE_HOLDER:
            for key, loader in product(self.keys, loaders):
                chain_key = f"{loader.section.key}.{key}"
                if chain_key in args.chain:
                    raise ValueError(f"circular chain detected {', '.join(args.chain[args.chain.index(chain_key):])}")
                args.chain.append(chain_key)
                try:
                    value = loader.load(key, self.of_type, self.factory, conf, args)
                except KeyError:
                    continue
                else:
                    break
                finally:
                    del args.chain[-1]
            else:
                value = self.default(conf, args.env_name) if callable(self.default) else self.default
            if self.post_process is not None:
                value = self.post_process(value)
            self._cache = value
        return cast(T, self._cache)

    def __repr__(self) -> str:
        values = ((k, v) for k, v in vars(self).items() if k != "post_process" and v is not None)
        return f"{type(self).__name__}({', '.join(f'{k}={v}' for k, v in values)})"

    def __eq__(self, o: Any) -> bool:
        return (
            type(self) == type(o)
            and super().__eq__(o)
            and (self.of_type, self.default, self.post_process) == (o.of_type, o.default, o.post_process)
        )


__all__ = [
    "ConfigLoadArgs",
    "ConfigDefinition",
    "ConfigDynamicDefinition",
    "ConfigConstantDefinition",
]
