import secrets
from typing import Any, Callable, Generator

import yaml
from typing_extensions import Self

from dsa import queue


# start snippet node
class Node:
    identity: str
    color: int | None
    neighbors: set[tuple[int, Self]]

    def __init__(
        self,
        color: int | None = None,
        *,
        neighbors: set[tuple[int, Self]] | None = None,
        identity: str | None = None,
    ):
        self.identity = identity if identity is not None else secrets.token_hex(4)
        self.color = color
        self.neighbors = neighbors if neighbors is not None else set()

        # NOTE: Ensure symetry. Since this graph is not directed, A a neighbor
        #       of B implies B is a neighbor of A. Think about how the relation
        #       on the graph could be represented as an adjaceny matrix and how
        #       the matrix would be the transpose of itself.
        self.connect(*self.neighbors)

    def __str__(self):
        n = "\n".join(
            f"  - identity: {node.identity}\n    distance: {distance}\n    color: {node.color}"
            for distance, node in self.neighbors
        )
        return f"identity: {self.identity}\ncolor: {self.color}:\nneighbors:\n{n}"

    def __hash__(self) -> int:
        return int(self.identity, 16)

    @classmethod
    def _layers(
        cls, previous: set[tuple[int, Self]], exclude: set[Self]
    ) -> set[tuple[int, Self]]:

        out = set()
        visited = set()
        for prev_distance, prev in previous:
            for node_distance, node in prev.neighbors:
                if node in exclude or node in visited:
                    continue

                out.add((node_distance, node))
                visited.add(node)

        return out

    def layers(self) -> Generator[set[tuple[int, Self]], None, None]:
        exclude = set()
        layer = {(0, self)}

        while len(layer):
            yield layer
            exclude |= set(map(lambda item: item[1], layer))
            layer = self._layers(layer, exclude)

    # end snippet node

    # ----------------------------------------------------------------------- #
    # helpers

    def connect(self, *nodes: tuple[int, Self]):
        self.neighbors |= {(color, node) for color, node in nodes}
        for color, node in nodes:
            node.neighbors.add((color, self))

    @classmethod
    def _from_dict(cls, raw: dict[str, Any]):

        neighbors = raw.pop("neighbors", [])
        node = cls(**raw)
        neighbors = (
            (raw_item.pop("weight"), cls._from_dict(raw_item)) for raw_item in neighbors
        )
        node.connect(*neighbors)
        return node

    @classmethod
    def from_dict(cls, raw: dict[str, Any]):
        return cls._from_dict(raw.copy())

    def to_dict(
        self,
        depth: int = 1,
        exclude: set[Self] | None = None,
    ):
        return self._to_dict(set() if exclude is None else exclude.copy(), depth=depth)

    def _to_dict(
        self,
        visited: set[Self],
        depth: int = 1,
        *,
        _weight: int | None = None,
        _depth: int = 0,
    ):

        visited.add(self)

        out = {
            "identity": self.identity,
            "color": self.color,
        }
        if _weight is not None:
            out["weight"] = _weight

        if _depth < depth:
            out["neighbors"] = [
                node._to_dict(visited, depth, _weight=_weight, _depth=_depth + 1)
                for _weight, node in self.neighbors
                if node not in visited
            ]

        return out


def dijkstra(node_start: Node, node_stop: Node):

    def key(node: Node, weight: int, next_node: Node):
        next_node.color = weight + node.color
        return weight + node.color

    node = node_start
    node.color = 0

    visited: set[Node] = set()
    path = queue.Queue[Node]()

    while True:

        path.enqueue(node)
        if node == node_stop:
            break

        if not (next_layer := node._layers({(0, node)}, visited)):
            return None

        _, next_node = min(next_layer, key=lambda item: key(node, *item))
        visited.add(node)
        node = next_node

    return path
