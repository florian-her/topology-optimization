import numpy as np

class Spring:
    def __init__(self, spring_id, node_a, node_b, k=1000.0):
        self.id = spring_id
        self.node_a = node_a  # Instanz von Node
        self.node_b = node_b  # Instanz von Node
        self.k = k            # Federsteifigkeit
        self.active = True    # Für die Topologie-Optimierung

    def get_length(self):
        return np.linalg.norm(self.node_a.pos - self.node_b.pos)

    def get_stiffness_matrix(self):
        # Hier später die 4x4 Element-Steifigkeitsmatrix
        pass