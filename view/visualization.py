import matplotlib.pyplot as plt

def plot_structure(structure):
    """Zeig die Knoten und Federn der Struktur an."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    if structure is None:
        return fig

    # 1. Federn (Linien) zeichnen
    for spring in structure.springs:
        if spring.active:
            x_coords = [spring.node_a.x, spring.node_b.x]
            y_coords = [spring.node_a.y, spring.node_b.y]
            ax.plot(x_coords, y_coords, color='gray', linewidth=1, zorder=1)

    # 2. Knoten (Punkte) zeichnen
    x_nodes = [node.x for node in structure.nodes]
    y_nodes = [node.y for node in structure.nodes]
    ax.scatter(x_nodes, y_nodes, color='blue', s=20, zorder=2)

    ax.set_aspect('equal')
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.grid(True, linestyle='--', alpha=0.6)
    
    return fig