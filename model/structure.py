from .node import Node
from .spring import Spring


class Structure:
    def __init__(self, width: int, height: int):
        """Initialisiert eine rechteckige Gitterstruktur aus Knoten und Federn.

        Parameters
        ----------
        width : int
            Anzahl der Knoten in x-Richtung.
        height : int
            Anzahl der Knoten in y-Richtung.
        """
        assert width >= 2, "Breite muss mindestens 2 sein."
        assert height >= 2, "Höhe muss mindestens 2 sein."
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

        Knoten-ID-Schema: id = y * width + x
        Pro Zelle werden 4 Federn erzeugt: horizontal, vertikal, diagonal \\, diagonal /
        """
        for y in range(self.height):
            for x in range(self.width):
                nid = self._node_id(x, y)
                self.nodes.append(Node(nid, float(x), float(y)))

        spring_id = 0
        for y in range(self.height):
            for x in range(self.width):
                nid = self._node_id(x, y)

                if x < self.width - 1:
                    self.springs.append(Spring(spring_id, self.nodes[nid], self.nodes[self._node_id(x + 1, y)]))
                    spring_id += 1

                if y < self.height - 1:
                    self.springs.append(Spring(spring_id, self.nodes[nid], self.nodes[self._node_id(x, y + 1)]))
                    spring_id += 1

                if x < self.width - 1 and y < self.height - 1:
                    self.springs.append(Spring(spring_id, self.nodes[nid], self.nodes[self._node_id(x + 1, y + 1)]))
                    spring_id += 1

                if x < self.width - 1 and y < self.height - 1:
                    self.springs.append(Spring(spring_id, self.nodes[self._node_id(x + 1, y)], self.nodes[self._node_id(x, y + 1)]))
                    spring_id += 1

    def remove_node(self, node_id: int) -> None:
        """Entfernt einen Massenpunkt und alle daran angeschlossenen Federn.

        Parameters
        ----------
        node_id : int
            ID des zu entfernenden Knotens.
        """
        assert 0 <= node_id < len(self.nodes), f"Ungültige Knoten-ID: {node_id}"
        node = self.nodes[node_id]
        assert node.active, f"Knoten {node_id} ist bereits entfernt."

        node.active = False
        for spring in self.springs:
            if spring.node_a.id == node_id or spring.node_b.id == node_id:
                spring.active = False

    def active_node_count(self) -> int:
        """Gibt die Anzahl aktiver Knoten zurück."""
        return sum(1 for n in self.nodes if n.active)

    def active_spring_count(self) -> int:
        """Gibt die Anzahl aktiver Federn zurück."""
        return sum(1 for s in self.springs if s.active)

    def __str__(self) -> str:
        return (f"Structure({self.width}x{self.height}, "
                f"nodes={self.active_node_count()}/{len(self.nodes)}, "
                f"springs={self.active_spring_count()}/{len(self.springs)})")

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    s = Structure(3, 3)
    print(f"{s}")
    s.remove_node(4)
    print(f"Nach Entfernen von Knoten 4: {s}")
    print(f"Aktive Knoten: {s.active_node_count()}")
