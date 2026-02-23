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
        werden aktive Federn nach Energie eingefärbt (blau=niedrig, rot=hoch).
    scale_factor : float, optional
        Skalierungsfaktor für Verformungsdarstellung (0 = unverformt).
        Bei 1.0 entspricht die max. Verschiebung 20% des Knotenabstands.
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

    # Verschiebungen normalisieren: scale_factor=1 → max. Auslenkung = 0.2 Gittereinheiten
    if scale_factor > 0:
        u_vals = [v for node in structure.nodes if node.active
                  for v in (abs(node.u_x), abs(node.u_y))]
        u_max = max(u_vals) if u_vals else 0.0
        effective_scale = (scale_factor * 0.2 / u_max) if u_max > 1e-9 else 0.0
    else:
        effective_scale = 0.0

    # Farb-Normierung auf Energiewerte
    norm = None
    cmap = plt.cm.RdYlBu_r  # blau=niedrig, rot=hoch
    if energies:
        vals = list(energies.values())
        e_min, e_max = min(vals), max(vals)
        norm = mcolors.Normalize(vmin=e_min, vmax=e_max if e_max > e_min else e_min + 1e-9)

    def _px(node) -> float:
        return node.x + node.u_x * effective_scale

    def _py(node) -> float:
        return node.y + node.u_y * effective_scale

    # 1. Federn zeichnen
    for spring in structure.springs:
        xa = [_px(spring.node_a), _px(spring.node_b)]
        ya = [_py(spring.node_a), _py(spring.node_b)]

        if not spring.active:
            # Gelöschte Federn: gestrichelt, sehr transparent
            ax.plot(xa, ya, color='#bbbbbb', linewidth=0.4,
                    linestyle='--', alpha=0.35, zorder=1)
        elif norm is not None and spring.id in energies:
            color = cmap(norm(energies[spring.id]))
            ax.plot(xa, ya, color=color, linewidth=2.0, zorder=2)
        else:
            ax.plot(xa, ya, color='steelblue', linewidth=1.5, zorder=2)

    # 2. Knoten zeichnen
    for node in structure.nodes:
        if not node.active:
            # Gelöschte Knoten: kleines X an ursprünglicher Position
            ax.plot(node.x, node.y, 'x', color='#aaaaaa',
                    markersize=4, alpha=0.4, zorder=2)
            continue

        px, py = _px(node), _py(node)

        if node.fix_x and node.fix_y:
            # Festlager: ausgefülltes Dreieck
            ax.plot(px, py, marker='^', color='black', markersize=8, zorder=4)
        elif node.fix_x or node.fix_y:
            # Loslager: Dreieck mit weißer Füllung
            ax.plot(px, py, marker='^', color='black', markersize=8,
                    markerfacecolor='white', zorder=4)
        elif node.force_x != 0 or node.force_y != 0:
            ax.plot(px, py, 'o', color='red', markersize=6, zorder=4)
            fx, fy = node.force_x, node.force_y
            s = 0.4 / (max(abs(fx), abs(fy)) + 1e-9)
            ax.annotate("", xy=(px + fx * s, py - fy * s),
                        xytext=(px, py),
                        arrowprops=dict(arrowstyle="->", color="red", lw=2))
        else:
            ax.plot(px, py, 'o', color='#555555', markersize=3, zorder=3)

    # 3. Ausgewählten Knoten hervorheben
    if highlight_node is not None:
        ax.plot(_px(highlight_node), _py(highlight_node),
                'o', color='magenta', markersize=12,
                markeredgecolor='black', zorder=5)

    # 4. Colorbar wenn Energien vorhanden
    if norm is not None:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, ax=ax, label="Verformungsenergie", shrink=0.8)

    active_n = structure.active_node_count()
    active_s = structure.active_spring_count()
    total_n = len(structure.nodes)
    total_s = len(structure.springs)
    ax.set_title(
        f"Struktur {structure.width}×{structure.height}  |  "
        f"Knoten: {active_n}/{total_n}  |  Federn: {active_s}/{total_s} aktiv"
    )
    ax.set_aspect('equal')
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.invert_yaxis()
    ax.grid(True, linestyle='--', alpha=0.3)

    return fig
