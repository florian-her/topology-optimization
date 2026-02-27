import numpy as np
import numpy.typing as npt


class Node:
    def __init__(self, node_id: int, x: float, y: float):
        """Erstellt einen Knoten mit Position und ID.

        Parameters
        ----------
        node_id : int
            Eindeutige ID des Knotens.
        x : float
            x-Position im Gitter.
        y : float
            y-Position im Gitter.
        """
        self.id = node_id
        self.x = x
        self.y = y
        
        # Binäre variable der Topologieoptimierung 
        self.active = True

        # Lager-Randbedingungen (kinematische Lagerungen)
        self.fix_x = 0
        self.fix_y = 0

        # Kraft-Randbedingungen (äußere Knotenlastvektoren)
        self.force_x = 0.0
        self.force_y = 0.0

        # Primäre Lösungsgrößen des FEM-Gleichungssystems (K·u = F)
        self.u_x = 0.0
        self.u_y = 0.0

    @property
    def pos(self) -> npt.NDArray[np.float64]:
        # Vektorielle Basis für die Berechnung der lokalen Elementrichtungsvektoren
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