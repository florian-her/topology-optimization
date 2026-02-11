import numpy as np

class Node:
    def __init__(self, node_id, x, y):
        self.id = node_id
        self.x = x
        self.y = y
        
        # Freiheitsgrade (Degree of Freedom)
        # 0: frei, 1: fixiert (Lager)
        self.fix_x = 0
        self.fix_y = 0
        
        # Externe Kräfte in Newton
        self.force_x = 0.0
        self.force_y = 0.0

    @property
    def pos(self):
        return np.array([self.x, self.y])