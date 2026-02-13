import matplotlib.pyplot as plt

def plot_structure(structure, scale_factor=1.0):
    """Zeigt die Knoten und Federn an, inklusive Verformung."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    if structure is None:
        return fig

    # 1. Federn (Linien) zeichnen
    for spring in structure.springs:
        if spring.active:
            # Wir berechnen die verformte Position: Original + (Verschiebung * Faktor)
            x_coords = [
                spring.node_a.x + spring.node_a.u_x * scale_factor, 
                spring.node_b.x + spring.node_b.u_x * scale_factor
            ]
            y_coords = [
                spring.node_a.y + spring.node_a.u_y * scale_factor, 
                spring.node_b.y + spring.node_b.u_y * scale_factor
            ]
            ax.plot(x_coords, y_coords, color='black', linewidth=1, zorder=1)

    # 2. Knoten (Punkte) zeichnen
    x_nodes = [n.x + n.u_x * scale_factor for n in structure.nodes]
    y_nodes = [n.y + n.u_y * scale_factor for n in structure.nodes]
    ax.scatter(x_nodes, y_nodes, color='blue', s=20, zorder=2)

    # 3. Lager (Rot) und Kräfte (Grün) markieren
    for node in structure.nodes:
        curr_x = node.x + node.u_x * scale_factor
        curr_y = node.y + node.u_y * scale_factor
        if node.fix_x or node.fix_y:
            ax.plot(curr_x, curr_y, 'r^', markersize=10)
        if abs(node.force_y) > 0:
            ax.arrow(curr_x, curr_y, 0, node.force_y * 0.05, 
                     head_width=0.2, color='green', zorder=3)

    ax.set_aspect('equal')
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.grid(True, linestyle='--', alpha=0.6)
    
    return fig