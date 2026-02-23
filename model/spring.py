import numpy as np
import numpy.typing as npt

class Spring:
    def __init__(self, spring_id, node_a, node_b, k: float | None = None):
        """Initialisiert eine Feder zwischen zwei Knoten.

        Parameter
        ----------
        spring_id : int
            Eindeutige Feder-ID.
        node_a : Node
            FErste node (start).
        node_b : Node
            Zweite node (ende).
        k : float | None, optional
            Federsteifigkeit. If None, auto-detected from geometry:
            - 1.0 for horizontal/vertical springs
            - 1/√2 ≈ 0.707 for diagonal springs (±45°)
        """
        self.id = spring_id
        self.node_a = node_a
        self.node_b = node_b
        self.k = k
        self.active = True

    def get_length(self) -> float:
        """Calculate the current length of the spring.

        Returns
        -------
        float
            Euclidean distance between node_a and node_b.
        """
        return np.linalg.norm(self.node_a.pos - self.node_b.pos)

    def get_direction_vector(self) -> npt.NDArray[np.float64]:
        """Calculate the normalized direction vector from node_a to node_b.

        Returns
        -------
        npt.NDArray[np.float64]
            Normalized 2D vector [ex, ey].
        """
        length = self.get_length()
        assert length > 1e-9, f"Spring {self.id} has zero length (degenerate element)."

        e_n = (self.node_b.pos - self.node_a.pos) / length
        return e_n

    def get_stiffness(self) -> float:
        """Get or calculate spring stiffness based on orientation.

        Returns
        -------
        float
            1.0 for horizontal/vertical springs.
            1/√2 ≈ 0.707 for diagonal springs (±45°).
        """
        if self.k is not None:
            return self.k

        # Auto-detect from geometry
        dx = self.node_b.x - self.node_a.x
        dy = self.node_b.y - self.node_a.y

        angle_deg = abs(np.degrees(np.arctan2(dy, dx)))

        # Diagonal bei 45° oder 135° (±5° Toleranz)
        if abs(angle_deg - 45) < 5 or abs(angle_deg - 135) < 5:
            return 1.0 / np.sqrt(2.0)
        else:
            return 1.0

    def get_stiffness_matrix(self) -> npt.NDArray[np.float64]:
        """Calculate the 4x4 element stiffness matrix in global coordinates.

        Uses the formula from the FEM theory:
        K_local = k * [[1, -1], [-1, 1]]  (2x2)
        O = outer(e_n, e_n)                (orientation matrix)
        K_element = kron(K_local, O)       (4x4)

        Returns
        -------
        npt.NDArray[np.float64]
            4x4 stiffness matrix ordered as [node_a_x, node_a_y, node_b_x, node_b_y].
        """
        k = self.get_stiffness()
        e_n = self.get_direction_vector()

        # 2x2 lokale Steifigkeitsmatrix
        K = k * np.array([[1.0, -1.0],
                          [-1.0, 1.0]])

        # Orientierungsmatrix (outer product)
        O = np.outer(e_n, e_n)

        # 4x4 Element-Steifigkeitsmatrix (Kronecker-Produkt)
        Ko = np.kron(K, O)

        return Ko

    def __str__(self) -> str:
        """String representation of the spring."""
        return (f"Spring(id={self.id}, a={self.node_a.id}, b={self.node_b.id}, "
                f"k={self.get_stiffness():.3f}, active={self.active})")

    def __repr__(self) -> str:
        """Detailed representation of the spring."""
        return self.__str__()


if __name__ == "__main__":
    from node import Node

    print("=" * 60)
    print("Spring Stiffness Matrix Tests")
    print("=" * 60)

    # Test 1: Horizontal spring (wie Hilfestellung)
    print("\n1. Horizontal Spring (0,0) -> (1,0)")
    print("-" * 60)
    node_0 = Node(0, 0.0, 0.0)
    node_1 = Node(1, 1.0, 0.0)
    spring_h = Spring(0, node_0, node_1)

    print(f"{spring_h}")
    print(f"Direction vector: {spring_h.get_direction_vector()}")
    print(f"Stiffness: {spring_h.get_stiffness()}")
    K_h = spring_h.get_stiffness_matrix()
    print(f"Stiffness Matrix Ko:\n{K_h}")
    print("\nExpected (from Hilfestellung):")
    print("[[1, 0, -1, 0],")
    print(" [0, 0,  0, 0],")
    print(" [-1, 0, 1, 0],")
    print(" [0, 0,  0, 0]]")

    # Test 2: Vertical spring
    print("\n\n2. Vertical Spring (0,0) -> (0,1)")
    print("-" * 60)
    node_3 = Node(3, 0.0, 1.0)
    spring_v = Spring(1, node_0, node_3)

    print(f"{spring_v}")
    print(f"Direction vector: {spring_v.get_direction_vector()}")
    print(f"Stiffness: {spring_v.get_stiffness()}")
    K_v = spring_v.get_stiffness_matrix()
    print(f"Stiffness Matrix Ko:\n{K_v}")
    print("\nExpected (from Hilfestellung):")
    print("[[0, 0, 0, 0],")
    print(" [0, 1, 0, -1],")
    print(" [0, 0, 0, 0],")
    print(" [0, -1, 0, 1]]")

    # Test 3: Diagonal spring (wie Hilfestellung)
    print("\n\n3. Diagonal Spring (0,0) -> (1,1)")
    print("-" * 60)
    node_2 = Node(2, 1.0, 1.0)
    spring_d = Spring(2, node_0, node_2)

    print(f"{spring_d}")
    print(f"Direction vector: {spring_d.get_direction_vector()}")
    print(f"Stiffness: {spring_d.get_stiffness():.6f}")
    K_d = spring_d.get_stiffness_matrix()
    print(f"Stiffness Matrix Ko:\n{K_d}")
    print("\nExpected (from Hilfestellung, k=1/sqrt(2) approx 0.707):")
    print("All entries approx +/-0.354 in pattern:")
    print("[[ 0.354,  0.354, -0.354, -0.354],")
    print(" [ 0.354,  0.354, -0.354, -0.354],")
    print(" [-0.354, -0.354,  0.354,  0.354],")
    print(" [-0.354, -0.354,  0.354,  0.354]]")

    # Test 4: Manual stiffness override
    print("\n\n4. Manual Stiffness Override")
    print("-" * 60)
    spring_manual = Spring(3, node_0, node_1, k=2.0)
    print(f"{spring_manual}")
    print(f"Stiffness (manual): {spring_manual.get_stiffness()}")
    K_manual = spring_manual.get_stiffness_matrix()
    print(f"First element K[0,0]: {K_manual[0, 0]:.3f} (should be 2.0)")

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)