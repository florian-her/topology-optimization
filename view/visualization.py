import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

from model.structure import Structure


def plot_structure(
    structure: Structure,
    energies: dict[int, float] | None = None,
    scale_factor: float = 0.0,
    highlight_node=None,
) -> plt.Figure:
    """Zeichnet Knoten und Federn der Struktur.

    Parameters
    ----------
    structure : Structure
        Die Struktur.
    energies : dict[int, float] | None, optional
        Mapping spring_id → Verformungsenergie. Wenn angegeben,
        werden Federn nach Energie eingefärbt (blau=niedrig, rot=hoch).
    scale_factor : float, optional
        Skalierungsfaktor für Verformungsdarstellung (0 = unverformt).
    highlight_node : Node | None, optional
        Knoten der hervorgehoben werden soll (magenta).

    Returns
    -------
    plt.Figure
        Matplotlib-Figur.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    if structure is None:
        return fig

    # Farb-Normierung auf Energiewerte
    if energies:
        vals = list(energies.values())
        e_min, e_max = min(vals), max(vals)
        norm = mcolors.Normalize(vmin=e_min, vmax=e_max if e_max > e_min else e_min + 1e-9)
        cmap = plt.cm.RdYlBu_r  # blau=niedrig, rot=hoch

    def _px(node) -> float:
        return node.x + node.u_x * scale_factor

    def _py(node) -> float:
        return node.y + node.u_y * scale_factor

    # 1. Federn zeichnen (verformt wenn scale_factor > 0)
    for spring in structure.springs:
        xa = [_px(spring.node_a), _px(spring.node_b)]
        ya = [_py(spring.node_a), _py(spring.node_b)]

        if not spring.active:
            # Inaktive Federn sehr blass anzeigen
            ax.plot(xa, ya, color='#e0e0e0', linewidth=0.5, zorder=1)
        elif energies and spring.id in energies:
            color = cmap(norm(energies[spring.id]))
            ax.plot(xa, ya, color=color, linewidth=1.5, zorder=2)
        else:
            ax.plot(xa, ya, color='steelblue', linewidth=1.0, zorder=2)

    # 2. Knoten zeichnen
    for node in structure.nodes:
        px, py = _px(node), _py(node)
        if node.fix_x or node.fix_y:
            # Gelagerte Knoten als Dreieck
            ax.plot(px, py, marker='^', color='black', markersize=7, zorder=4)
        elif node.force_x != 0 or node.force_y != 0:
            # Belastete Knoten als Stern
            ax.plot(px, py, marker='*', color='red', markersize=10, zorder=4)
            # Kraftpfeil
            fx, fy = node.force_x, node.force_y
            s = 0.4 / (max(abs(fx), abs(fy)) + 1e-9)
            ax.annotate("", xy=(px + fx * s, py + fy * s),
                        xytext=(px, py),
                        arrowprops=dict(arrowstyle="->", color="red", lw=2))
        else:
            ax.plot(px, py, 'o', color='#555555', markersize=3, zorder=3)

    # 3. Ausgewählten Knoten hervorheben
    if highlight_node is not None:
        ax.plot(_px(highlight_node), _py(highlight_node),
                'o', color='magenta', markersize=12,
                markeredgecolor='black', zorder=5)

    # 3. Colorbar wenn Energien vorhanden
    if energies:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, ax=ax, label="Verformungsenergie", shrink=0.8)

    active = sum(1 for s in structure.springs if s.active)
    total = len(structure.springs)
    ax.set_title(f"Struktur {structure.width}×{structure.height}  |  "
                 f"Federn: {active}/{total} aktiv")
    ax.set_aspect('equal')
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.invert_yaxis()  # Ursprung oben links (wie im Grid)
    ax.grid(True, linestyle='--', alpha=0.3)

    return fig
