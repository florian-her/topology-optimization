import numpy as np
from .node import Node
from .spring import Spring

class Structure:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.nodes = []
        self.springs = []
        self.generate_grid()

    def generate_grid(self):
        """Erzeugt ein 2D-Gitter mit stabilisierenden Diagonalen."""
        self.nodes = []
        self.springs = []
        node_map = {}

        # 1. Knoten erstellen
        node_id = 0
        for y in range(self.height):
            for x in range(self.width):
                new_node = Node(node_id, float(x), float(y))
                self.nodes.append(new_node)
                node_map[(x, y)] = new_node
                node_id += 1
        
        # 2. Federn erstellen
        spring_id = 0
        
        for y in range(self.height):
            for x in range(self.width):
                current = node_map[(x, y)]
                
                # Vorgaben: k=1 für gerade, k=0.707 für schräge
                targets = [
                    (1, 0, 1.0),                 # Rechts (k=1)
                    (0, 1, 1.0),                 # Unten (k=1)
                    (1, 1, 1.0 / np.sqrt(2)),    # Diagonal Rechts-Unten
                    (-1, 1, 1.0 / np.sqrt(2))    # Diagonal Links-Unten
                ]
                
                for dx, dy, k_val in targets:
                    nx, ny = x + dx, y + dy
                    if (nx, ny) in node_map:
                        neighbor = node_map[(nx, ny)]
                        self.springs.append(Spring(spring_id, current, neighbor, k=k_val))
                        spring_id += 1