import matplotlib.pyplot as plt

def plot_structure(structure):
    fig, ax = plt.subplots(figsize=(10, 6))
    if structure is None: return fig

    # Federn zeichnen
    for spring in structure.springs:
        if spring.active:
            x = [spring.node_a.x, spring.node_b.x]
            y = [spring.node_a.y, spring.node_b.y]
            # evtl. Unterschiedliche Farben für Diagonalen
            color = 'gray' if spring.get_length() > 1.1 else 'black'
            ax.plot(x, y, color=color, linewidth=1, alpha=0.7)

    # Knoten, Lager und Kräfte zeichnen
    for node in structure.nodes:
        ax.scatter(node.x, node.y, color='blue', s=30, zorder=3)
        
        # Lager (Rote Dreiecke)
        if node.fix_x or node.fix_y:
            ax.plot(node.x, node.y, 'r^', markersize=10)
        
        # Kräfte (Grüne Pfeile)
        if abs(node.force_y) > 0:
            ax.arrow(node.x, node.y, 0, node.force_y * 0.1, 
                     head_width=0.2, color='green', zorder=4)

    ax.set_aspect('equal')
    ax.invert_yaxis() # Falls (0,0) oben links sein soll (wie in Hilfestellung)
    ax.grid(True, linestyle='--', alpha=0.3)
    return fig