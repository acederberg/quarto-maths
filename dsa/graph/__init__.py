import secrets
from typing import Callable

import yaml
from typing_extensions import Self


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

    def __hash__(self) -> int:
        return int(self.identity, 16)

    def connect(self, *nodes: tuple[int, Self]):
        self.neighbors |= {(color, node) for color, node in nodes}
        for color, node in nodes:
            node.neighbors.add((color, self))

    # end snippet node


# start snippet dijkstra
# def _dijkstra(
#     root: Node,
#     visited: set[str],
#     paths: dict[str, list[Node]],
#     metric: Callable[[int, int], bool],
#     depth=0,
# ) -> None:
#     # NOTE: If the node started from has no color, something is wrong.
#     if root.color is None:
#         raise ValueError()
#
#     if root.identity not in paths:
#         paths[root.identity] = []
#
#     # NOTE: If the node has been visited already, do not bother. This prevents
#     #       cycles.
#     space = depth * "   "
#     print(f"{space}-> Visiting `{root.identity}`.")
#     root_path = paths[root.identity]
#     for edge_color, node in root.neighbors:
#         print(f"{space}   ...{node.identity}")
#         # NOTE: If the node does not yet have a color, overwrite the color
#         #       using the edge color. If the edge does have a color but
#         #       ``node_color_next`` would minimize color, use it instead - if
#         #       the ``node_color_next`` exceeds this, do not re-color.
#         node_color_next = edge_color + root.color
#         if (node_color := node.color) is None:
#             node.color = node_color_next
#             paths[node.identity] = [*root_path, node]
#         elif metric(node_color, node_color_next):
#             node.color = node_color_next
#             paths[node.identity] = [*root_path, node]
#
#         # NOTE: Now recurse for the above for this node and its neighbors.
#         if node.identity in visited:
#             print(f"{space}   Skipping `{root.identity}`.")
#             visited.add(root.identity)
#             continue
#
#         _dijkstra(node, visited, paths, metric, depth=depth + 1)
#
#
# def dijkstra(
#     graph: Node,
#     # *,
#     # worst: bool = False,
# ) -> dict[str, list[Node]]:
#     """Complete the graph coloring using edge colors.
#
#     :param worst: Used to generate the worst path, which is funny. Of course,
#         the 'worst' path could always be worse by adding an infitine cycle
#         between two nodes, but the condition that nodes ought not be revisted
#         makes this impossible.
#     """
#
#     graph.color = 0
#
#     paths: dict[str, list[Node]] = dict()
#
#     _dijkstra(
#         graph,
#         set(),
#         paths,
#         metric=lambda node_color, node_color_next: node_color > node_color_next,
#     )
#
#     return paths


def dijkstra(node: Node):

    visited = set()
    paths = dict()

    root = node
    paths[node.identity] = (root_path := [])

    while root is not None:

        assert root.color is not None

        least = None

        for edge_color, node in root.neighbors:

            node_color_next = edge_color + root.color
            if (node_color := node.color) is None:
                node.color = node_color_next
                paths[node.identity] = [*root_path, node]

            elif node_color > node_color_next:
                node.color = node_color_next
                paths[node.identity] = [*root_path, node]

        visited.add(root.identity)

        root = least
        root_path = paths[root.identity]

    # end snippet dijkstra


# --------------------------------------------------------------------------- #
# Tests


def test_1():
    """Test on a totally connected graph of order 10 where all edges have
    the same weight.
    """

    nn = 10
    neighbors = {(1, Node()) for _ in range(nn - 1)}
    graph = Node(neighbors=neighbors)
    paths = dijkstra(graph)

    assert isinstance(paths, dict)
    assert len(paths) == nn

    assert all(len(path) == 1 for id_, path in paths.items() if id_ != graph.identity)
    assert all(node.color == 1 for _, node in neighbors)


def test_2():

    # NOTE: Graph should look like this:
    #
    #             10
    #     C ------------> +-------+
    # 10 /                |       |
    #   /  100       1000 |       |
    # A --------> B ----> |   E   |
    #   \                 |       |
    # 0  \        0       |       |
    #     D ------------> +-------+

    A, B, C, D, E = (Node(identity=identity) for identity in "ABCDE")

    A.connect((0, D), (100, B), (10, C))
    E.connect((0, D), (1000, B), (10, C))

    assert len(A.neighbors) == 3
    assert len(B.neighbors) == 2
    assert len(C.neighbors) == 2
    assert len(D.neighbors) == 2
    assert len(E.neighbors) == 3

    def create_paths(
        start: Node,
        # worst: bool = False,
    ):
        for node in (A, B, C, D, E):
            node.color = None

        return {
            identity: list(map(lambda v: v.identity, path))
            for identity, path in dijkstra(start).items()
        }

    paths = create_paths(A)
    assert len(paths) == 5
    assert paths["E"] == ["D", "E"] and E.color == 0
    assert paths["D"] == ["D"] and D.color == 0
    assert paths["C"] == ["D", "E", "C"] and C.color == 10
    assert paths["B"] == ["B"] and B.color == 100
    assert paths["A"] == [] and A.color == 0

    paths = create_paths(B)
    assert paths["A"] == ["A"] and A.color == 100
    assert paths["B"] == [] and B.color == 0
    assert C.color == 110
    assert paths["D"] == ["A", "D"] and D.color == 100
    assert paths["E"] == ["A", "D", "E"] and E.color == 100

    paths = create_paths(C)
    assert paths["C"] == [] and C.color == 0
    assert A.color == 10
    assert B.color == 110
    assert D.color == 10

    print("=================================================")
    paths = create_paths(D)
    assert A.color == 0 and paths["A"] == ["A"]
    assert E.color == 0 and paths["E"] == ["E"]
    assert B.color == 100 and paths["B"] == ["A", "B"]
    assert C.color == 10 and paths["C"] == ["C"]
    assert D.color == 0 and paths["D"] == []
