import numpy as np
import numpy.typing as npt


class Node:
    def __init__(self, node_id: int, x: float, y: float):
        """Initialisiert einen Massenpunkt im 2D-Gitter.

        Parameters
        ----------
        node_id : int
            Eindeutige Knoten-ID.
        x : float
            x-Koordinate (Ursprung links oben, x→rechts).
        y : float
            y-Koordinate (positiv nach unten).
        """
        self.id = node_id
        self.x = x
        self.y = y
        self.active = True

        # Freiheitsgrade: 0 = frei, 1 = fixiert (Lager)
        self.fix_x = 0
        self.fix_y = 0

        # Externe Kräfte in Newton (Konvention: negativ = nach unten)
        self.force_x = 0.0
        self.force_y = 0.0

        # FEM-Ergebnisse: Verschiebungen
        self.u_x = 0.0
        self.u_y = 0.0

    @property
    def pos(self) -> npt.NDArray[np.float64]:
        return np.array([self.x, self.y])

    def __str__(self) -> str:
        return (f"Node(id={self.id}, pos=({self.x:.0f},{self.y:.0f}), "
                f"active={self.active}, fix=({self.fix_x},{self.fix_y}), "
                f"F=({self.force_x:.2f},{self.force_y:.2f}))")

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    n = Node(0, 0.0, 0.0)
    print(f"{n}")
    n.fix_x = 1
    n.force_y = -1.0
    print(f"{n}")
    n.active = False
    print(f"{n}")
