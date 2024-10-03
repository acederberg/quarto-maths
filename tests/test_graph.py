import pytest

from dsa.graph import Node, dijkstra


class TestDijkstra:
    def test_basic(self):

        # NOTE: Demonstration from wikipedia: https://en.wikipedia.org/wiki/Dijkstra's_algorithm
        #
        #     +--- B --------+
        #    /      \         \
        #   / 7      \ 10      \ 15
        #  /          \         \
        # A ---------- C ------- D
        #  \   9      /   11    /
        #   \        / 2       / 6
        #    \      /         /
        #     +--- F -------- E
        #     14        9

        A, B, C, D, E, F = (Node(identity=str(k + 1)) for k in range(6))
        A.connect((7, B), (9, C), (14, F))
        B.connect((15, D), (10, C))
        C.connect((11, D), (2, F))
        E.connect((9, F), (6, D))

        _path = dijkstra(A, E)
        assert _path is not None

        path = list(_path)
        assert list(node.identity for node in path) == ["1", "2", "3", "6", "5"]
        assert E.color == 28

    def graph_2(self):

        # NOTE: Graph should look like this:
        #
        #    +------ C -------+
        #   /  10        10    \
        #  /                    \
        # A -------- B --------- E
        #  \  100        1000   /
        #   \                  /
        #    +------ D -------+
        #       0         0

        A, B, C, D, E = (Node(identity=identity) for identity in "ABCDE")

        A.connect((0, D), (100, B), (10, C))
        E.connect((0, D), (1000, B), (10, C))

        return {"A": A, "B": B, "C": C, "D": D, "E": E}

    @pytest.mark.skip
    @pytest.mark.parametrize(
        "graph, solution_path, solution_distance",
        [
            ("1", ["A", "B"], 100),
            ("1", ["A", "D", "E"], 0),
            ("1", ["A", "D", "E", "C"], 10),
            ("1", ["E", "D", "A", "C"], 10),
            ("1", ["B", "A", "D", "E", "C"], 10),
        ],
        indirect=["graph"],
    )
    def test_dijkstra(
        self,
        graph: dict[str, Node],
        solution_path: list[str],
        solution_distance: int,
    ):
        start_key, stop_key = solution_path[0], solution_path[-1]
        start, stop = graph[start_key], graph[stop_key]

        soln = dijkstra(start, stop)
        assert soln is not None

        path = list(soln)
        assert list(node.identity for node in path) == solution_path
        assert solution_distance == stop.color


# class TestGraph:
# def test_layers(self):
#
#     node = Node(identity="1")
#
#     odd, even = node, Node(identity="2")
#
#     for k in range(2, 100):
#
#         odd_next = Node(identity=str(2 * k - 1))
#         even_next = Node(identity=str(2 * k))
#
#         # Note: Pairity connected.
#         even.connect((k, even_next))
#         odd.connect((k, odd_next))
#
#         # Note: Next connected
#         odd.connect((k, even))
#         odd_next.connect((k, even))
#
#         # yield odd, even
#
#         even, odd = even_next, odd_next
#
#     for layer in node.layers():
#         yield layer
