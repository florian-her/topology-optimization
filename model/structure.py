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
                # Horizontale Feder (nach rechts)
                if x < self.width - 1:
                    self.springs.append(Spring(spring_id, node_map[(x, y)], node_map[(x+1, y)]))
                    spring_id += 1
                # Vertikale Feder (nach unten)
                if y < self.height - 1:
                    self.springs.append(Spring(spring_id, node_map[(x, y)], node_map[(x, y+1)]))
                    spring_id += 1
                # Diagonale 1 (rechts-unten)
                if x < self.width - 1 and y < self.height - 1:
                    self.springs.append(Spring(spring_id, node_map[(x, y)], node_map[(x+1, y+1)]))
                    spring_id += 1
                # Diagonale 2 (links-unten)
                if x > 0 and y < self.height - 1:
                    self.springs.append(Spring(spring_id, node_map[(x, y)], node_map[(x-1, y+1)]))
                    spring_id += 1