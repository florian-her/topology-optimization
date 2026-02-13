import numpy as np
import numpy.typing as npt

class Spring:
    def __init__(self, spring_id, node_a, node_b, k: float | None = None):
        # Hier wird die Feder erstellt, die zwei Knoten verbindet.
        self.id = spring_id
        self.node_a = node_a
        self.node_b = node_b
        self.k = k
        self.active = True

    def get_length(self) -> float:
        # Gibt den Abstand zwischen den zwei Knoten zurück.
        return np.linalg.norm(self.node_a.pos - self.node_b.pos)

    def get_direction_vector(self) -> npt.NDArray[np.float64]:
        # Berechnet den Richtungsvektor von A nach B.
        length = self.get_length()
        assert length > 1e-9, f"Feder {self.id} ist zu kurz!"

        e_n = (self.node_b.pos - self.node_a.pos) / length
        return e_n

    def get_stiffness(self) -> float:
        # Holt die Steifigkeit (entweder fest oder erkennt sie am Winkel).
        if self.k is not None:
            return self.k

        # Checken ob gerade oder schräg
        dx = self.node_b.x - self.node_a.x
        dy = self.node_b.y - self.node_a.y

        angle_deg = abs(np.degrees(np.arctan2(dy, dx)))

        # Wenn schräg (45 Grad), dann k = 0.707
        if abs(angle_deg - 45) < 5 or abs(angle_deg - 135) < 5:
            return 1.0 / np.sqrt(2.0)
        else:
            return 1.0

    def get_stiffness_matrix(self) -> npt.NDArray[np.float64]:
        # Baut die 4x4 Matrix für den FEM-Solver zusammen.
        k = self.get_stiffness()
        e_n = self.get_direction_vector()

        # Kleine 2x2 Matrix
        K = k * np.array([[1.0, -1.0],
                          [-1.0, 1.0]])

        # Ausrichtung einbeziehen
        O = np.outer(e_n, e_n)

        # Zur 4x4 Matrix aufblasen
        Ko = np.kron(K, O)

        return Ko

    def __str__(self) -> str:
        # Kurz-Info zur Feder.
        return (f"Spring(id={self.id}, a={self.node_a.id}, b={self.node_b.id}, "
                f"k={self.get_stiffness():.3f}, active={self.active})")

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    from node import Node

    print("=" * 60)
    print("Tests für die Feder-Matrix")
    print("=" * 60)

    # Test 1: Waagerechte Feder
    print("\n1. Waagerechte Feder (0,0) -> (1,0)")
    print("-" * 60)
    node_0 = Node(0, 0.0, 0.0)
    node_1 = Node(1, 1.0, 0.0)
    spring_h = Spring(0, node_0, node_1)

    print(f"{spring_h}")
    K_h = spring_h.get_stiffness_matrix()
    print(f"Matrix:\n{K_h}")

    # Test 2: Senkrechte Feder
    print("\n\n2. Senkrechte Feder (0,0) -> (0,1)")
    print("-" * 60)
    node_3 = Node(3, 0.0, 1.0)
    spring_v = Spring(1, node_0, node_3)

    print(f"{spring_v}")
    K_v = spring_v.get_stiffness_matrix()
    print(f"Matrix:\n{K_v}")

    # Test 3: Diagonale Feder
    print("\n\n3. Diagonale Feder (0,0) -> (1,1)")
    print("-" * 60)
    node_2 = Node(2, 1.0, 1.0)
    spring_d = Spring(2, node_0, node_2)

    print(f"{spring_d}")
    K_d = spring_d.get_stiffness_matrix()
    print(f"Matrix:\n{K_d}")

    print("\n" + "=" * 60)
    print("Fertig!")
    print("=" * 60)