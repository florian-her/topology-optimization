import numpy as np

class FEMSolver:
    def __init__(self, structure):
        self.structure = structure
        self.n_nodes = len(structure.nodes)
        self.size = 2 * self.n_nodes
        self.f = np.zeros(self.size)

    def solve(self):
        # 1. Globale Steifigkeitsmatrix K aufbauen
        K = np.zeros((self.size, self.size))
        
        for spring in self.structure.springs:
            if not spring.active:
                continue
            
            # Indizes der Knoten holen
            idx_a = 2 * spring.node_a.id
            idx_b = 2 * spring.node_b.id
            dofs = [idx_a, idx_a + 1, idx_b, idx_b + 1]
            
            # Nutzt die 4x4 Matrix aus spring.py
            k_ele = spring.get_stiffness_matrix()
            
            # In globale Matrix einsortieren
            for i in range(4):
                for j in range(4):
                    K[dofs[i], dofs[j]] += k_ele[i, j]
        
        # 2. Kraftvektor f füllen
        for node in self.structure.nodes:
            self.f[2*node.id] = node.force_x
            self.f[2*node.id + 1] = node.force_y
            
        # 3. Lager (Randbedingungen) anwenden mit Penalty-Methode
        penalty = 1e15
        for node in self.structure.nodes:
            if node.fix_x:
                K[2*node.id, 2*node.id] += penalty
            if node.fix_y:
                K[2*node.id + 1, 2*node.id + 1] += penalty
        
        # 4. Gleichungssystem lösen: K * u = f
        try:
            u = np.linalg.solve(K, self.f)
            
            # 5. Ergebnisse zurück in die Knoten schreiben
            for node in self.structure.nodes:
                node.u_x = u[2*node.id]
                node.u_y = u[2*node.id + 1]
            return u
        except np.linalg.LinAlgError:
            raise Exception("Matrix ist singulär! Hast du Lager gesetzt?")