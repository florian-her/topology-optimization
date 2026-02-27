import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
from copy import deepcopy

from model.structure import Structure
from model.material import Material
from solver.fem_solver import solve_structure
from optimizer.topology_optimizer import TopologyOptimizer
from optimizer.validators import StructureValidator
from view.visualization import plot_structure
from persistence.io_handler import IOHandler
from view.jokes import get_shuffled_jokes

st.set_page_config(page_title="TopoOptimizer 2D", layout="wide")

_DEFAULT_MATERIAL_NAMES = {m.name for m in Material.defaults()}


def _has_forces(structure: Structure) -> bool:
    """Prüft ob aktive Knoten mit Kräften vorhanden sind."""
    return any(n.force_x != 0 or n.force_y != 0 for n in structure.nodes if n.active)


def _has_bcs(structure: Structure) -> bool:
    """Prüft ob aktive Knoten mit Lagern vorhanden sind."""
    return any(n.fix_x or n.fix_y for n in structure.nodes if n.active)


def _apply_default_bcs(structure: Structure) -> None:
    """Setzt Standard-Lager und Kraft auf die Struktur."""
    bottom = structure.height - 1

    nid = structure._node_id(0, bottom)
    structure.nodes[nid].fix_x = 1
    structure.nodes[nid].fix_y = 1

    nid = structure._node_id(structure.width - 1, bottom)
    structure.nodes[nid].fix_y = 1

    mid_x = structure.width // 2
    structure.nodes[structure._node_id(mid_x, 0)].force_y = -0.5


def _tab_struktur(s: Structure, scale_factor: float, mass_fraction: float,
                  stress_ratio_limit: float | None = None,
                  opt_mode: str = "Genau") -> None:
    col_plot, col_ctrl = st.columns([3, 1])

    with col_plot:
        fig = plot_structure(
            s,
            energies=st.session_state.stresses,
            scale_factor=scale_factor,
            highlight_node_id=st.session_state.selected_node_id,
        )
        event = st.plotly_chart(
            fig, on_select="rerun", selection_mode=("points",),
            use_container_width=True,
        )
        if event and event.selection and event.selection.points:
            nid = event.selection.points[0].get("customdata", [None])[0]
            if nid is not None:
                st.session_state.selected_node_id = int(nid)

        selected_node = next(
            (n for n in s.nodes if n.id == st.session_state.selected_node_id), None
        )
        if st.session_state.selected_node_id is not None:
            if st.button("Auswahl aufheben", key="deselect"):
                st.session_state.selected_node_id = None
                st.rerun()

    with col_ctrl:
        # --- Material-Selektor ---
        mat_names = [m.name for m in st.session_state.materials]
        current_idx = next(
            (i for i, m in enumerate(st.session_state.materials) if m.name == s.material.name), 0
        )
        sel_name = st.selectbox("Material", mat_names, index=current_idx)
        sel_mat = next(m for m in st.session_state.materials if m.name == sel_name)
        st.caption(f"E={sel_mat.E} GPa · σ={sel_mat.yield_strength} MPa · ρ={sel_mat.density} kg/m³")

        if sel_mat.name != s.material.name:
            s.material = sel_mat
            if st.session_state.structure_base:
                st.session_state.structure_base.material = sel_mat
            st.session_state.u = None
            st.session_state.stresses = None
            st.rerun()

        st.markdown("---")

        # --- Knoten-Editor ---
        if selected_node:
            st.subheader(f"Knoten {selected_node.id}")
            st.caption(f"({selected_node.x:.0f}, {selected_node.y:.0f})")

            with st.form("node_editor"):
                c1, c2 = st.columns(2)
                fix_x = c1.checkbox("Fix X", value=bool(selected_node.fix_x))
                fix_y = c2.checkbox("Fix Y", value=bool(selected_node.fix_y))
                force_x = st.number_input("Fx [N]", value=float(selected_node.force_x), step=0.1)
                force_y = st.number_input("Fy [N]", value=float(selected_node.force_y), step=0.1)

                if st.form_submit_button("Anwenden"):
                    selected_node.fix_x = 1 if fix_x else 0
                    selected_node.fix_y = 1 if fix_y else 0
                    selected_node.force_x = force_x
                    selected_node.force_y = force_y
                    st.session_state.structure_base = deepcopy(st.session_state.structure)
                    st.session_state.u = None
                    st.session_state.stresses = None
                    st.rerun()

            no_bc = not selected_node.fix_x and not selected_node.fix_y
            no_force = selected_node.force_x == 0 and selected_node.force_y == 0
            if no_bc and no_force:
                if st.button("Knoten entfernen", type="secondary", key="remove_node"):
                    if StructureValidator.can_remove_node(s, selected_node.id):
                        s.remove_node(selected_node.id)
                        st.session_state.structure_base.remove_node(selected_node.id)
                        st.session_state.u = None
                        st.session_state.stresses = None
                        st.session_state.selected_node_id = None
                        st.rerun()
                    else:
                        st.warning("Knoten kann nicht entfernt werden (Struktur würde zerfallen).")

        st.markdown("---")

        # --- FEM + Optimizer ---
        st.subheader("Analyse")

        if st.session_state.status_msg:
            st.success(st.session_state.status_msg)
            st.session_state.status_msg = None

        if st.button("FEM lösen"):
            try:
                if not _has_bcs(s):
                    st.warning("Keine Lagerung definiert — bitte zuerst Lager setzen.")
                elif not _has_forces(s):
                    st.warning("Keine Kräfte definiert — bitte zuerst Kräfte setzen.")
                else:
                    with st.spinner("Löse Ku=F …"):
                        u = solve_structure(s)
                    if u is None:
                        st.error("FEM konnte nicht gelöst werden.")
                    else:
                        st.session_state.u = u
                        st.session_state.stresses = TopologyOptimizer.compute_spring_stresses(s, u)
                        max_s = max(st.session_state.stresses.values()) if st.session_state.stresses else 0.0
                        st.session_state.status_msg = f"Max. Dehnung: {max_s:.4f} %"
                        st.rerun()
            except Exception as e:
                st.error(f"FEM-Fehler: {e}")

        btn_label = "Original wiederherstellen" if mass_fraction >= 1.0 else f"Optimieren ({int(mass_fraction * 100)}% Masse)"
        if st.button(btn_label):
            try:
                if not _has_forces(st.session_state.structure_base):
                    st.warning("Keine Kräfte definiert — bitte zuerst Kräfte setzen.")
                elif not _has_bcs(st.session_state.structure_base):
                    st.warning("Keine Lagerung definiert — bitte zuerst Lager setzen.")
                else:
                    s_fresh = deepcopy(st.session_state.structure_base)
                    st.session_state.structure = s_fresh
                    st.session_state.energy_history = []
                    if mass_fraction >= 1.0:
                        u = solve_structure(s_fresh)
                        st.session_state.u = u
                        st.session_state.stresses = (
                            TopologyOptimizer.compute_spring_stresses(s_fresh, u) if u is not None else None
                        )
                        st.session_state.status_msg = "Originalstruktur wiederhergestellt"
                    else:
                        import time as _time

                        bar = st.progress(0, text="Optimierung startet ...")
                        joke_area = st.empty()
                        jokes = get_shuffled_jokes()
                        joke_state = {"idx": 0, "last_t": _time.monotonic()}
                        joke_area.info(jokes[0])

                        def _on_progress(frac: float, n_active: int, n_target: int) -> None:
                            pct = min(int(frac * 100), 100)
                            bar.progress(
                                frac,
                                text=f"Optimierung: {pct}% · {n_active} → {n_target} Knoten",
                            )
                            now = _time.monotonic()
                            if now - joke_state["last_t"] >= 10:
                                joke_state["idx"] = (joke_state["idx"] + 1) % len(jokes)
                                joke_state["last_t"] = now
                                joke_area.info(jokes[joke_state["idx"]])

                        run_fn = TopologyOptimizer.run_fast if opt_mode == "Schnell" else TopologyOptimizer.run
                        history = run_fn(
                            s_fresh,
                            mass_fraction=mass_fraction,
                            on_progress=_on_progress,
                            stress_ratio_limit=stress_ratio_limit,
                        )
                        bar.progress(1.0, text="Optimierung abgeschlossen")
                        joke_area.empty()
                        st.session_state.energy_history.extend(history)
                        u = solve_structure(s_fresh)
                        st.session_state.u = u
                        st.session_state.stresses = (
                            TopologyOptimizer.compute_spring_stresses(s_fresh, u) if u is not None else None
                        )
                        n_final = s_fresh.active_node_count()
                        target_n = max(2, int(len(s_fresh.nodes) * mass_fraction))
                        msg = f"{len(history)} Schritte · {n_final} Knoten aktiv"
                        if n_final > target_n:
                            if stress_ratio_limit is not None:
                                msg += f" (Spannungsgrenze {stress_ratio_limit}× erreicht)"
                            elif opt_mode == "Schnell":
                                pct_reached = n_final / len(s_fresh.nodes) * 100
                                msg += f" (Schnellmodus: {pct_reached:.0f}% erreicht)"
                        st.session_state.status_msg = msg
                    st.rerun()
            except Exception as e:
                st.error(f"Optimierer-Fehler: {e}")

        st.markdown("---")
        st.metric("Knoten aktiv", f"{s.active_node_count()} / {len(s.nodes)}")
        st.metric("Federn aktiv", f"{s.active_spring_count()} / {len(s.springs)}")

        if st.session_state.energy_history:
            st.line_chart(st.session_state.energy_history)

        u = st.session_state.u
        if u is not None:
            import numpy as np
            with st.expander("Ergebnisbericht", expanded=False):
                n_active = s.active_node_count()
                n_total = len(s.nodes)
                reduction = (1 - n_active / n_total) * 100

                displacements = [
                    np.sqrt(u[2 * n.id] ** 2 + u[2 * n.id + 1] ** 2)
                    for n in s.nodes if n.active
                ]
                max_disp = max(displacements) if displacements else 0.0

                compliance = float(np.dot(u, u))

                stresses = st.session_state.stresses
                max_stress = max(stresses.values()) if stresses else 0.0

                c1, c2 = st.columns(2)
                c1.metric("Massenreduktion", f"{reduction:.1f} %")
                c2.metric("Max. Verschiebung", f"{max_disp:.4f}")
                c1.metric("Compliance (u·u)", f"{compliance:.4f}")
                c2.metric("Max. Dehnung", f"{max_stress:.4f} %")


def _structure_key(s: Structure) -> tuple:
    """Schlüssel zur Erkennung von Änderungen der Basisstruktur."""
    return (
        s.width, s.height, s.material.name, s.active_node_count(),
        round(sum(n.force_x + n.force_y for n in s.nodes if n.active), 4),
        sum(n.fix_x + n.fix_y for n in s.nodes if n.active),
    )


@st.fragment
def _tab_gif(s: Structure) -> None:
    st.header("GIF-Export")

    col1, col2, col3, col4 = st.columns(4)
    start_pct = col1.slider("Start (%)", 30, 100, 100, 5, key="gif_start")
    end_pct   = col2.slider("End (%)",    5,  95,  30, 5, key="gif_end")
    n_frames  = col3.slider("Frames",     2,  20,   8, 1, key="gif_frames")
    fps       = col4.slider("FPS",        1,  10,   2, 1, key="gif_fps")

    if end_pct >= start_pct:
        st.warning("End-% muss kleiner als Start-% sein.")
        return

    if st.button("GIF erstellen", use_container_width=True):
        if not _has_bcs(st.session_state.structure_base):
            st.warning("Keine Lagerung definiert.")
        elif not _has_forces(st.session_state.structure_base):
            st.warning("Keine Kräfte definiert.")
        else:
            try:
                base = st.session_state.structure_base
                cur_key = _structure_key(base)

                if st.session_state.gif_base_key != cur_key:
                    st.session_state.gif_checkpoints = {}
                    st.session_state.gif_png_cache = {}
                    st.session_state.gif_base_key = cur_key

                checkpoints: dict[float, Structure] = st.session_state.gif_checkpoints
                png_cache: dict[float, bytes] = st.session_state.gif_png_cache

                start_frac = start_pct / 100.0
                end_frac   = end_pct   / 100.0
                mass_fracs = [
                    start_frac + (end_frac - start_frac) * i / (n_frames - 1)
                    for i in range(n_frames)
                ]

                # Besten Startpunkt aus Cache laden (Checkpoint >= start_frac)
                above = {k: v for k, v in checkpoints.items() if k >= start_frac - 0.01}
                if above:
                    best_k = min(above)
                    s_gif = deepcopy(above[best_k])
                    if best_k > start_frac + 0.02 and start_frac < 1.0:
                        TopologyOptimizer.run(s_gif, mass_fraction=start_frac)
                else:
                    s_gif = deepcopy(base)
                    if start_frac < 1.0:
                        TopologyOptimizer.run(s_gif, mass_fraction=start_frac)
                checkpoints[round(start_frac, 2)] = deepcopy(s_gif)

                import time as _time

                png_frames = []
                cached_count = 0
                bar = st.progress(0, f"Frame 0 / {n_frames}")
                joke_area = st.empty()
                jokes = get_shuffled_jokes()
                joke_state = {"idx": 0, "last_t": _time.monotonic()}
                joke_area.info(jokes[0])

                for idx, target_frac in enumerate(mass_fracs):
                    rounded = round(target_frac, 2)
                    if rounded in png_cache:
                        png_frames.append(png_cache[rounded])
                        cached_count += 1
                    else:
                        if rounded in checkpoints:
                            s_gif = deepcopy(checkpoints[rounded])
                        else:
                            if target_frac < 1.0:
                                TopologyOptimizer.run(s_gif, mass_fraction=target_frac)
                            checkpoints[rounded] = deepcopy(s_gif)

                        u = solve_structure(s_gif)
                        energies = (
                            TopologyOptimizer.compute_spring_stresses(s_gif, u)
                            if u is not None else None
                        )
                        fig = plot_structure(s_gif, energies=energies, scale_factor=0)
                        png = fig.to_image(format="png", width=900, height=550, scale=1.5)
                        png_cache[rounded] = png
                        png_frames.append(png)

                    bar.progress((idx + 1) / n_frames, f"Frame {idx + 1} / {n_frames}")
                    now = _time.monotonic()
                    if now - joke_state["last_t"] >= 10:
                        joke_state["idx"] = (joke_state["idx"] + 1) % len(jokes)
                        joke_state["last_t"] = now
                        joke_area.info(jokes[joke_state["idx"]])

                joke_area.empty()

                st.session_state.gif_checkpoints = checkpoints
                st.session_state.gif_png_cache = png_cache
                st.session_state.gif_bytes = IOHandler.to_gif_bytes(png_frames, fps=fps)
                msg = f"GIF erstellt: {n_frames} Frames"
                if cached_count:
                    msg += f" ({cached_count} aus Cache)"
                st.success(msg)
            except Exception as e:
                st.error(f"GIF-Fehler: {e}")

    if st.session_state.get("gif_bytes"):
        st.download_button(
            "GIF herunterladen",
            st.session_state.gif_bytes,
            file_name=f"optimierung_{s.width}x{s.height}.gif",
            mime="image/gif",
            use_container_width=True,
        )
        st.image(st.session_state.gif_bytes)


def _tab_speichern(s: Structure, scale_factor: float) -> None:
    st.header("Speichern / Laden")

    col_save, col_load = st.columns(2)

    with col_save:
        st.subheader("Exportieren")
        st.download_button(
            "Struktur herunterladen (JSON)",
            IOHandler.to_json_bytes(s),
            file_name=f"struktur_{s.width}x{s.height}_{s.material.name}.json",
            mime="application/json",
            use_container_width=True,
        )

        fig_export = plot_structure(
            s,
            energies=st.session_state.stresses,
            scale_factor=scale_factor,
        )
        st.download_button(
            "Bild herunterladen (PNG)",
            IOHandler.to_png_bytes(fig_export),
            file_name=f"struktur_{s.width}x{s.height}_{s.material.name}.png",
            mime="image/png",
            use_container_width=True,
        )
        st.markdown("---")
        st.caption(
            f"Material: {s.material.name}  |  "
            f"Gitter: {s.width}×{s.height}  |  "
            f"Knoten aktiv: {s.active_node_count()}/{len(s.nodes)}  |  "
            f"Federn aktiv: {s.active_spring_count()}/{len(s.springs)}"
        )

    with col_load:
        st.subheader("Laden")
        uploaded = st.file_uploader("Struktur laden (.json)", type=["json"])
        if uploaded is not None and uploaded.name != st.session_state.last_uploaded:
            try:
                s_loaded = IOHandler.load_from_bytes(uploaded.read())
                if not any(m.name == s_loaded.material.name for m in st.session_state.materials):
                    st.session_state.materials.append(s_loaded.material)
                st.session_state.structure = s_loaded
                st.session_state.structure_base = deepcopy(s_loaded)
                st.session_state.u = None
                st.session_state.stresses = None
                st.session_state.energy_history = []
                st.session_state.last_uploaded = uploaded.name
                st.session_state.selected_node_id = None
                st.session_state.status_msg = f"Struktur geladen: {uploaded.name}"
                st.rerun()
            except Exception as e:
                st.error(f"Ladefehler: {e}")


def _tab_materialien() -> None:
    st.header("Materialien")

    mat_data = [
        {
            "Name": m.name,
            "E [GPa]": m.E,
            "σ_y [MPa]": m.yield_strength,
            "ρ [kg/m³]": m.density,
            "Typ": "Standard" if m.name in _DEFAULT_MATERIAL_NAMES else "Benutzerdefiniert",
        }
        for m in st.session_state.materials
    ]
    st.dataframe(mat_data, use_container_width=True)

    custom_mats = [m for m in st.session_state.materials if m.name not in _DEFAULT_MATERIAL_NAMES]
    if custom_mats:
        st.markdown("---")
        st.subheader("Material löschen")
        to_delete = st.selectbox("Material auswählen", [m.name for m in custom_mats])
        if st.button("Löschen", type="secondary"):
            st.session_state.materials = [m for m in st.session_state.materials if m.name != to_delete]
            st.rerun()

    st.markdown("---")
    st.subheader("Neues Material hinzufügen")

    with st.form("new_material"):
        name = st.text_input("Name")
        col1, col2 = st.columns(2)
        E = col1.number_input("E-Modul [GPa]", min_value=0.1, max_value=2000.0, value=100.0, step=1.0)
        yield_strength = col2.number_input("Streckgrenze [MPa]", min_value=1.0, max_value=10000.0, value=200.0, step=10.0)
        density = st.number_input("Dichte [kg/m³]", min_value=100.0, max_value=25000.0, value=5000.0, step=100.0)

        if st.form_submit_button("Hinzufügen"):
            if not name.strip():
                st.error("Name darf nicht leer sein.")
            elif any(m.name == name.strip() for m in st.session_state.materials):
                st.error(f"Material '{name}' existiert bereits.")
            else:
                try:
                    st.session_state.materials.append(
                        Material(name.strip(), E=E, yield_strength=yield_strength, density=density)
                    )
                    st.rerun()
                except AssertionError as e:
                    st.error(str(e))


def main():
    st.title("2D Topologie-Optimierung")

    if "structure" not in st.session_state:
        st.session_state.structure = None
    if "u" not in st.session_state:
        st.session_state.u = None
    if "stresses" not in st.session_state:
        st.session_state.stresses = None
    if "energy_history" not in st.session_state:
        st.session_state.energy_history = []
    if "status_msg" not in st.session_state:
        st.session_state.status_msg = None
    if "structure_base" not in st.session_state:
        st.session_state.structure_base = None
    if "last_uploaded" not in st.session_state:
        st.session_state.last_uploaded = None
    if "materials" not in st.session_state:
        st.session_state.materials = Material.defaults()
    if "gif_bytes" not in st.session_state:
        st.session_state.gif_bytes = None
    if "gif_checkpoints" not in st.session_state:
        st.session_state.gif_checkpoints = {}
    if "gif_png_cache" not in st.session_state:
        st.session_state.gif_png_cache = {}
    if "gif_base_key" not in st.session_state:
        st.session_state.gif_base_key = None
    if "selected_node_id" not in st.session_state:
        st.session_state.selected_node_id = None

    # --- Sidebar ---
    st.sidebar.header("Gitter")
    col_w, col_h = st.sidebar.columns(2)
    width = int(col_w.number_input("Breite", min_value=2, max_value=500, value=10, step=1))
    height = int(col_h.number_input("Höhe", min_value=2, max_value=200, value=6, step=1))

    if st.sidebar.button("Struktur initialisieren"):
        s = Structure(width, height)
        st.session_state.structure = s
        st.session_state.structure_base = deepcopy(s)
        st.session_state.u = None
        st.session_state.stresses = None
        st.session_state.energy_history = []
        st.session_state.selected_node_id = None

    if st.session_state.structure:
        if st.sidebar.button("Standard-Lagerung setzen"):
            _apply_default_bcs(st.session_state.structure)
            st.session_state.structure_base = deepcopy(st.session_state.structure)
            st.session_state.u = None
            st.session_state.stresses = None
            st.session_state.energy_history = []

    st.sidebar.markdown("---")
    st.sidebar.header("Darstellung")
    scale_factor = st.sidebar.slider("Verformungs-Skalierung", 0.0, 2.0, 1.0, 0.05)

    st.sidebar.markdown("---")
    st.sidebar.header("Optimierer")
    mass_fraction = st.sidebar.slider("Massenreduktionsfaktor", 0.05, 1.0, 0.5, 0.05)
    opt_mode = st.sidebar.radio(
        "Berechnungsmethode",
        ["Genau", "Schnell"],
        horizontal=True,
        help="Genau: kleine Schritte, präzises Ergebnis. Schnell: große Schritte, 4-8× schneller, stoppt ggf. vor dem Ziel.",
    )
    stress_limit_on = st.sidebar.checkbox("Spannungsbegrenzung", value=False)
    stress_ratio_limit: float | None = None
    if stress_limit_on:
        stress_ratio_limit = st.sidebar.slider(
            "Max. Spannungsfaktor (σ_max / σ_ref)",
            min_value=1.5, max_value=10.0, value=3.0, step=0.5,
        )

    # --- Tabs ---
    tab_struct, tab_io, tab_gif, tab_mat = st.tabs(
        ["Struktur & Analyse", "Speichern / Laden", "GIF-Export", "Materialien"]
    )

    with tab_mat:
        _tab_materialien()

    with tab_struct:
        s = st.session_state.structure
        if not s:
            st.info("Struktur initialisieren (Sidebar links).")
        else:
            _tab_struktur(s, scale_factor, mass_fraction, stress_ratio_limit, opt_mode)

    with tab_io:
        s = st.session_state.structure
        if not s:
            st.info("Struktur initialisieren (Sidebar links).")
        else:
            _tab_speichern(s, scale_factor)

    with tab_gif:
        s = st.session_state.structure
        if not s:
            st.info("Struktur initialisieren (Sidebar links).")
        else:
            _tab_gif(s)


if __name__ == "__main__":
    main()
