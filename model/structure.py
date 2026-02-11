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
        """Erzeugt ein 2D-Gitter aus Knoten und Federn."""
        # 1. Knoten erstellen
        node_id = 0
        for y in range(self.height):
            for x in range(self.width):
                self.nodes.append(Node(node_id, float(x), float(y)))
                node_id += 1
        
        # 2. Federn erstellen (Horizontale und Vertikale Verbindungen) zunächst vereinfacht
        spring_id = 0
        for i in range(len(self.nodes)):
            # Verbinde horizontal (wenn nicht am rechten Rand)
            if (i + 1) % self.width != 0:
                self.springs.append(Spring(spring_id, self.nodes[i], self.nodes[i+1]))
                spring_id += 1