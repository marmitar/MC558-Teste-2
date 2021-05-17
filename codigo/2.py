from __future__ import annotations
from enum import Enum, unique
from typing import Callable, Iterable, Iterator, Optional, Tuple, Type, Union
from graphviz import Digraph
from functools import cached_property
from matplotlib import colors


@unique
class Cor(str, Enum):
    AZUL = 'blue'
    VERM = 'red'

    @property
    def marker(self) -> str:
        return self.name[0]

def rgba(color: str, alpha: float=1.0) -> str:
    return colors.to_hex(colors.to_rgb(color) + (alpha,), keep_alpha=True)


class Graph:
    def __init__(self) -> None:
        self.nodes: set[Node] = set()
        self.edges: dict[Edge, Cor] = {}
        self.root: Optional[Node] = None

    def __contains__(self, value: Union[Node, Edge]) -> bool:
        if isinstance(value, Node):
            return value in self.nodes
        elif isinstance(value, tuple):
            return value in self.edges
        else:
            raise TypeError()

    def add_node(self, node: Node) -> None:
        if node in self:
            raise ValueError()
        self.nodes.add(node)
        self.root = node

    def add_edge(self, tail: Node, head: Node, cor: Cor) -> None:
        if (tail, head) in self:
            raise ValueError()
        self.edges[tail, head] = cor

    def cor(self, tail: Node, head: Node) -> Cor:
        return self.edges[tail, head]

    def show(self, node: Optional[Node] = None, *, indent: str = '  ') -> None:
        root = node or self.root
        if root is None:
            print('*', 'EMPTY', '*')
            return

        Print = Callable[[str], None]
        Neighbor = Union[Node, tuple[Node, Cor]]
        def show_node(node: Neighbor, print: Print, indent: str):
            if isinstance(node, tuple):
                node, cor = node
                print(f'{cor.marker} {node}')
            else:
                print(str(self))

            def inner_print(text: str):
                print(indent + text)

            for neigh in node.neighbors:
                cor = self.cor(node, neigh)
                self.show_node((neigh, cor), inner_print, indent=indent)

        show_node(root, print, indent)

    def viz(self, node: Optional[Node] = None, *, path: Optional[Path]=None) -> Digraph:
        graph = Digraph()
        root = node or self.root
        if root is None:
            return graph
        visited: set[Node] = set()

        if path is None:
            edges = frozenset(self.edges.keys())
            nodes = frozenset(self.nodes)
        else:
            edges = frozenset(path.edges)
            nodes = frozenset(path)

        def alpha(node: Union[Node, Edge]):
            if node in nodes or node in edges:
                return 1.0
            else:
                return 0.5

        def add_node(node: Node):
            cor = rgba('k', alpha(node))
            graph.node(node.name, color=cor, fontcolor=cor)
            visited.add(node)

        def add_edge(tail: Node, head: Node):
            cor = rgba(self.cor(tail, head), alpha((tail, head)))
            graph.edge(tail.name, head.name, color=cor)

        def viz_node(node: Node):
            if node in visited:
                return
            add_node(node)

            for neigh in node.neighbors:
                viz_node(neigh)
                add_edge(node, neigh)

        viz_node(root)
        return graph

    def vertices(self) -> str:
        return '{' + ', '.join(sorted(map(str, self.nodes))) + '}'

    def edges(self, *, color: bool=False) -> str:
        if color:
            edges = (f'{tail}{head}#{cor.marker}' for (tail, head), cor in self.edges.items())
        else:
            edges = (f'{tail}{head}' for tail, head in self.edges.keys())
        return '{' + ', '.join(sorted(edges)) + '}'

    def __str__(self) -> str:
        return f'Graph({self.vertices()}, {self.edges()})'


def visualize(root: Union[Node, Path, None]=None, *, render: bool=True) -> None:
    if isinstance(root, Path):
        graph = Node.graph.viz(path=root)
    else:
        graph = Node.graph.viz(root)

    if render:
        graph.render('graph', view=True, cleanup=True, quiet_view=True)
    return graph


class Node:
    graph = Graph()

    def __init__(self, *edges: tuple[Cor, Node]):
        self.graph.add_node(self)

        for cor, node in edges:
            self.graph.add_edge(self, node, cor)

        self.neighbors = tuple(node for _, node in edges)

    def __hash__(self) -> int:
        return hash(id(self))

    @cached_property
    def name(self) -> str:
        for name, var in globals().items():
            if var is self:
                return name.lower()
        raise NameError()

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'Node({self.name})'

    def show(self, *, all: bool = True) -> None:
        self.graph.show(self if not all else None)

    def paths(self) -> Iterator[Path]:
        yield Path(self)

        for node in self.neighbors:
            for path in node.paths():
                yield self + path

    def azul(self) -> int:
        cnt = 0
        for path in self.paths():
            if path.valid and path.cor() is Azul:
                cnt += 1
        return cnt

    def verm(self) -> int:
        cnt = 0
        for path in self.paths():
            if path.valid and path.cor() is Verm:
                cnt += 1
        return cnt

    @classmethod
    def all(cls) -> Tuple[Node, ...]:
        return tuple(sorted(Node.graph.nodes, key=lambda n: n.name))


class Path(tuple[Node, ...]):
    graph = Node.graph

    def __new__(cls: Type[Path], *args: Union[Node, Iterable[Node]]) -> Path:
        nodes = []
        for arg in args:
            if isinstance(arg, Node):
                nodes.append(arg)
            else:
                nodes.extend(arg)
        path = super().__new__(cls, nodes)
        for edge in path.edges:
            assert edge in cls.graph
        return path

    def __add__(self, other: Union[Path, Node]) -> Path:
        return Path(self, other)

    def __radd__(self, other: Union[Path, Node]) -> Path:
        return Path(other, self)

    def __str__(self) -> str:
        return '(' + ', '.join(str(node) for node in self) + ')'

    def __repr__(self) -> str:
        return f'Path{str(self)}'

    @classmethod
    def all(cls) -> Iterator[Path]:
        yield Path()

        for node in cls.graph.nodes:
            for path in node.paths():
                yield path

    @cached_property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(zip(self[:-1], self[1:]))

    def cor(self) -> Optional[Cor]:
        if len(self.edges) > 0:
            return self.graph.cor(*self.edges[0])

    @cached_property
    def valid(self) -> bool:
        for cur, next in zip(self.edges[:-1], self.edges[1:]):
            if self.graph.cor(*cur) is Azul:
                continue
            if self.graph.cor(*next) is Verm:
                return False
        return True


Edge = tuple[Node, Node]

Azul = Cor.AZUL
Verm = Cor.VERM


Z = Node()
Y = Node((Azul, Z))
X = Node((Verm, Y), (Azul, Z))
W = Node((Verm, X), (Azul, Y))
V = Node()
U = Node((Azul, Y), (Verm, W), (Verm, V))
T = Node((Verm, X), (Azul, W))
S = Node((Azul, V), (Azul, T), (Verm, X))
R = Node((Azul, S))
Q = Node((Azul, T), (Azul, S), (Verm, R))
P = Node((Azul, U), (Verm, Q), (Verm, S))


print('Name', *(f'{node.name:>3s}'   for node in Node.all()))
print('Azul', *(f'{node.azul():3d}' for node in Node.all()))
print('Verm', *(f'{node.verm():3d}' for node in Node.all()))
