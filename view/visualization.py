import matplotlib.pyplot as plt

def plot_structure(structure, scale_factor=1.0, highlight_node=None):
    """
    Zeigt die Struktur an.
    highlight_node: Ein Node-Objekt, das farblich hervorgehoben werden soll (zum Bearbeiten).
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if structure is None:
        return fig

    # 1. Federn (Linien)
    for spring in structure.springs:
        if spring.active:
            x = [spring.node_a.x + spring.node_a.u_x * scale_factor, 
                 spring.node_b.x + spring.node_b.u_x * scale_factor]
            y = [spring.node_a.y + spring.node_a.u_y * scale_factor, 
                 spring.node_b.y + spring.node_b.u_y * scale_factor]
            ax.plot(x, y, color='black', linewidth=1, zorder=1)

    # 2. Knoten (Normale Punkte)
    x_nodes = [n.x + n.u_x * scale_factor for n in structure.nodes]
    y_nodes = [n.y + n.u_y * scale_factor for n in structure.nodes]
    ax.scatter(x_nodes, y_nodes, color='blue', s=20, zorder=2)

    # 3. Lager und Kräfte
    for node in structure.nodes:
        curr_x = node.x + node.u_x * scale_factor
        curr_y = node.y + node.u_y * scale_factor
        
        if node.fix_x or node.fix_y:
            ax.plot(curr_x, curr_y, 'r^', markersize=10, zorder=3)
        
        if abs(node.force_x) > 0 or abs(node.force_y) > 0:
            # Skalierung für Pfeil-Darstellung
            fx = node.force_x * 0.5
            fy = node.force_y * 0.5
            ax.arrow(curr_x, curr_y, fx, fy, head_width=0.2, color='green', zorder=4)

    # 4. Highlight für den ausgewählten Knoten (Magenta)
    if highlight_node:
        h_x = highlight_node.x + highlight_node.u_x * scale_factor
        h_y = highlight_node.y + highlight_node.u_y * scale_factor
        # Zeichne einen dicken Kreis um den Punkt
        ax.plot(h_x, h_y, 'o', color='magenta', markersize=12, markeredgecolor='black', zorder=5)

    ax.set_aspect('equal')
    ax.invert_yaxis() # Y nach unten (wie in Matrix-Koordinaten üblich)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    return fig