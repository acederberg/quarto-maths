from typing import Generic, TypeVar

T_Container = TypeVar("T_Container", bound="Container")


class Item(Generic[T_Container]): ...


class Container: ...


T_Item = TypeVar("T_Item", bound="Item[T_Container]")


class Config(Generic[T_Container, T_Item]):

    items: dict[str, T_Item]
    container: T_Container


config = Config[Container, Item]()

config.items
