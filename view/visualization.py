import plotly.graph_objects as go
import plotly.colors as pc

from model.structure import Structure

_N_BINS = 20


def plot_structure(
    structure: Structure,
    energies: dict[int, float] | None = None,
    scale_factor: float = 0.0,
    highlight_node_id: int | None = None,
) -> go.Figure:
    """Zeichnet Knoten und Federn der Struktur als interaktive Plotly-Figur.

    Parameters
    ----------
    structure : Structure
        Die Struktur.
    energies : dict[int, float] | None, optional
        Mapping spring_id → Verformungsenergie.
    scale_factor : float, optional
        Skalierungsfaktor für Verformungsdarstellung.
    highlight_node_id : int | None, optional
        ID des hervorzuhebenden Knotens (magenta).

    Returns
    -------
    go.Figure
        Plotly-Figur.
    """
    fig = go.Figure()

    if structure is None:
        return fig

    # Verschiebungen normalisieren
    if scale_factor > 0:
        u_vals = [v for node in structure.nodes if node.active
                  for v in (abs(node.u_x), abs(node.u_y))]
        u_max = max(u_vals) if u_vals else 0.0
        u_ref = u_max * (structure.material.E / 210.0)
        effective_scale = (scale_factor * 0.2 / u_ref) if u_ref > 1e-9 else 0.0
    else:
        effective_scale = 0.0

    def _px(node) -> float:
        return node.x + node.u_x * effective_scale

    def _py(node) -> float:
        return node.y + node.u_y * effective_scale

    # --- Federn ---
    # Inaktive Federn: eine gestrichelte graue Spur
    ix, iy = [], []
    for sp in structure.springs:
        if not sp.active:
            ix += [_px(sp.node_a), _px(sp.node_b), None]
            iy += [_py(sp.node_a), _py(sp.node_b), None]
    if ix:
        fig.add_trace(go.Scatter(
            x=ix, y=iy, mode="lines",
            line=dict(color="#bbbbbb", width=0.8, dash="dash"),
            opacity=0.35, hoverinfo="skip", showlegend=False,
        ))

    if energies:
        vals = list(energies.values())
        e_min, e_max = min(vals), max(vals)
        e_range = e_max - e_min if e_max > e_min else 1e-9

        # Aktive Federn in _N_BINS Energie-Gruppen eingefärbt
        bins: dict[int, tuple[list, list]] = {b: ([], []) for b in range(_N_BINS)}
        for sp in structure.springs:
            if sp.active and sp.id in energies:
                t = (energies[sp.id] - e_min) / e_range
                b = min(int(t * _N_BINS), _N_BINS - 1)
                bins[b][0].extend([_px(sp.node_a), _px(sp.node_b), None])
                bins[b][1].extend([_py(sp.node_a), _py(sp.node_b), None])

        for b, (bx, by) in bins.items():
            if not bx:
                continue
            t = (b + 0.5) / _N_BINS
            color = pc.sample_colorscale("RdBu_r", [t])[0]
            fig.add_trace(go.Scatter(
                x=bx, y=by, mode="lines",
                line=dict(color=color, width=2.0),
                hoverinfo="skip", showlegend=False,
            ))

        # Unsichtbare Dummy-Spur für Colorbar
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(
                colorscale="RdBu_r",
                cmin=e_min, cmax=e_max,
                color=[e_min],
                showscale=True,
                colorbar=dict(title="Verformungsenergie", thickness=15, len=0.8),
            ),
            hoverinfo="skip", showlegend=False,
        ))
    else:
        # Aktive Federn ohne Energiefärbung
        ax, ay = [], []
        for sp in structure.springs:
            if sp.active:
                ax += [_px(sp.node_a), _px(sp.node_b), None]
                ay += [_py(sp.node_a), _py(sp.node_b), None]
        if ax:
            fig.add_trace(go.Scatter(
                x=ax, y=ay, mode="lines",
                line=dict(color="steelblue", width=1.5),
                hoverinfo="skip", showlegend=False,
            ))

    # --- Knoten ---
    regular_x, regular_y, regular_ids = [], [], []
    loslager_x, loslager_y, loslager_ids = [], [], []
    festlager_x, festlager_y, festlager_ids = [], [], []
    force_x_list, force_y_list, force_ids = [], [], []
    inactive_x, inactive_y = [], []

    for node in structure.nodes:
        if not node.active:
            inactive_x.append(node.x)
            inactive_y.append(node.y)
            continue

        px, py = _px(node), _py(node)

        if node.fix_x and node.fix_y:
            festlager_x.append(px)
            festlager_y.append(py)
            festlager_ids.append(node.id)
        elif node.fix_x or node.fix_y:
            loslager_x.append(px)
            loslager_y.append(py)
            loslager_ids.append(node.id)
        elif node.force_x != 0 or node.force_y != 0:
            force_x_list.append(px)
            force_y_list.append(py)
            force_ids.append(node.id)
            fx, fy = node.force_x, node.force_y
            s = 0.4 / (max(abs(fx), abs(fy)) + 1e-9)
            fig.add_annotation(
                x=px + fx * s, y=py - fy * s,
                ax=px, ay=py,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True,
                arrowhead=2, arrowwidth=2, arrowcolor="red",
                text="",
            )
        else:
            regular_x.append(px)
            regular_y.append(py)
            regular_ids.append(node.id)

    tip = "<b>Knoten %{customdata[0]}</b><br>(%{x:.2f}, %{y:.2f})<extra></extra>"

    if regular_x:
        fig.add_trace(go.Scatter(
            x=regular_x, y=regular_y, mode="markers",
            marker=dict(color="#555555", size=6),
            customdata=[[i] for i in regular_ids],
            hovertemplate=tip, showlegend=False,
        ))
    if loslager_x:
        fig.add_trace(go.Scatter(
            x=loslager_x, y=loslager_y, mode="markers",
            marker=dict(symbol="triangle-up", color="white", size=12,
                        line=dict(color="black", width=2)),
            customdata=[[i] for i in loslager_ids],
            hovertemplate=tip, showlegend=False,
        ))
    if festlager_x:
        fig.add_trace(go.Scatter(
            x=festlager_x, y=festlager_y, mode="markers",
            marker=dict(symbol="triangle-up", color="black", size=12),
            customdata=[[i] for i in festlager_ids],
            hovertemplate=tip, showlegend=False,
        ))
    if force_x_list:
        fig.add_trace(go.Scatter(
            x=force_x_list, y=force_y_list, mode="markers",
            marker=dict(color="red", size=8),
            customdata=[[i] for i in force_ids],
            hovertemplate=tip, showlegend=False,
        ))
    if inactive_x:
        fig.add_trace(go.Scatter(
            x=inactive_x, y=inactive_y, mode="markers",
            marker=dict(symbol="x", color="#aaaaaa", size=5, opacity=0.4),
            hoverinfo="skip", showlegend=False,
        ))

    # Hervorgehobener Knoten
    if highlight_node_id is not None:
        node = next((n for n in structure.nodes if n.id == highlight_node_id), None)
        if node:
            fig.add_trace(go.Scatter(
                x=[_px(node)], y=[_py(node)], mode="markers",
                marker=dict(color="magenta", size=15,
                            line=dict(color="black", width=2)),
                hoverinfo="skip", showlegend=False,
            ))

    active_n = structure.active_node_count()
    active_s = structure.active_spring_count()
    total_n = len(structure.nodes)
    total_s = len(structure.springs)

    fig.update_layout(
        title=(
            f"{structure.material.name}  |  "
            f"Struktur {structure.width}×{structure.height}  |  "
            f"Knoten: {active_n}/{total_n}  |  Federn: {active_s}/{total_s} aktiv"
        ),
        xaxis=dict(title="x", scaleanchor="y", scaleratio=1,
                   showgrid=True, gridcolor="#eeeeee"),
        yaxis=dict(title="y", autorange="reversed",
                   showgrid=True, gridcolor="#eeeeee"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        clickmode="event+select",
        dragmode="pan",
        margin=dict(l=40, r=40, t=60, b=40),
        height=500,
    )

    return fig
