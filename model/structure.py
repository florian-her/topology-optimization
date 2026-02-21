import numpy as np
from .node import Node
from .spring import Spring


class Structure:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.nodes: list[Node] = []
        self.springs: list[Spring] = []
        self.generate_grid()

    def _node_id(self, x: int, y: int) -> int:
        """Gibt die Knoten-ID für Gitterposition (x, y) zurück (row-major)."""
        return y * self.width + x

    def generate_grid(self) -> None:
        """Erzeugt ein 2D-Gitter aus Knoten und Federn.

        Knoten-ID-Schema (row-major): id = y * width + x
        Pro Zelle werden 4 Federn erzeugt: horizontal, vertikal, diagonal \\, diagonal /
        """
        # 1. Knoten erstellen
        for y in range(self.height):
            for x in range(self.width):
                nid = self._node_id(x, y)
                self.nodes.append(Node(nid, float(x), float(y)))

        # 2. Federn erstellen
        spring_id = 0
        for y in range(self.height):
            for x in range(self.width):
                nid = self._node_id(x, y)

                # Horizontal (→): node(x,y) → node(x+1,y)
                if x < self.width - 1:
                    self.springs.append(Spring(spring_id, self.nodes[nid], self.nodes[self._node_id(x + 1, y)]))
                    spring_id += 1

                # Vertikal (↓): node(x,y) → node(x,y+1)
                if y < self.height - 1:
                    self.springs.append(Spring(spring_id, self.nodes[nid], self.nodes[self._node_id(x, y + 1)]))
                    spring_id += 1

                # Diagonal \ (↘): node(x,y) → node(x+1,y+1)
                if x < self.width - 1 and y < self.height - 1:
                    self.springs.append(Spring(spring_id, self.nodes[nid], self.nodes[self._node_id(x + 1, y + 1)]))
                    spring_id += 1

                # Diagonal / (↙): node(x+1,y) → node(x,y+1)
                if x < self.width - 1 and y < self.height - 1:
                    self.springs.append(Spring(spring_id, self.nodes[self._node_id(x + 1, y)], self.nodes[self._node_id(x, y + 1)]))
                    spring_id += 1

    def __str__(self) -> str:
        return f"Structure({self.width}x{self.height}, nodes={len(self.nodes)}, springs={len(self.springs)})"

    def __repr__(self) -> str:
        return self.__str__()