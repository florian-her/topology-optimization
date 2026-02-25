import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
from copy import deepcopy

from model.structure import Structure
from model.material import Material
from solver.fem_solver import solve_structure
from optimizer.topology_optimizer import TopologyOptimizer
from view.visualization import plot_structure
from persistence.io_handler import IOHandler

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
    nid = structure._node_id(mid_x, bottom)
    structure.nodes[nid].force_y = -0.5


def _tab_struktur(s: Structure, scale_factor: float, mass_fraction: float) -> None:
    col_plot, col_ctrl = st.columns([3, 1])

    with col_plot:
        fig = plot_structure(
            s,
            energies=st.session_state.energies,
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
            st.session_state.energies = None

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
                    st.session_state.energies = None
                    st.rerun()

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
                        st.session_state.energies = TopologyOptimizer.compute_spring_energies(s, u)
                        total_e = sum(st.session_state.energies.values())
                        st.session_state.status_msg = f"Energie: {total_e:.4f}"
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
                        st.session_state.energies = (
                            TopologyOptimizer.compute_spring_energies(s_fresh, u) if u is not None else None
                        )
                        st.session_state.status_msg = "Originalstruktur wiederhergestellt"
                    else:
                        with st.spinner(f"Optimiere bis {int(mass_fraction * 100)}% Masse …"):
                            history = TopologyOptimizer.run(s_fresh, mass_fraction=mass_fraction)
                            st.session_state.energy_history.extend(history)
                            u = solve_structure(s_fresh)
                            st.session_state.u = u
                            st.session_state.energies = (
                                TopologyOptimizer.compute_spring_energies(s_fresh, u) if u is not None else None
                            )
                        st.session_state.status_msg = (
                            f"{len(history)} Schritte · {s_fresh.active_node_count()} Knoten aktiv"
                        )
                    st.rerun()
            except Exception as e:
                st.error(f"Optimierer-Fehler: {e}")

        st.markdown("---")
        st.metric("Knoten aktiv", f"{s.active_node_count()} / {len(s.nodes)}")
        st.metric("Federn aktiv", f"{s.active_spring_count()} / {len(s.springs)}")

        if st.session_state.energy_history:
            st.line_chart(st.session_state.energy_history)


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
            energies=st.session_state.energies,
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
                st.session_state.energies = None
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
    if "energies" not in st.session_state:
        st.session_state.energies = None
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
        st.session_state.energies = None
        st.session_state.energy_history = []
        st.session_state.selected_node_id = None

    if st.session_state.structure:
        if st.sidebar.button("Standard-Lagerung setzen"):
            _apply_default_bcs(st.session_state.structure)
            st.session_state.structure_base = deepcopy(st.session_state.structure)
            st.session_state.u = None
            st.session_state.energies = None

    st.sidebar.markdown("---")
    st.sidebar.header("Darstellung")
    scale_factor = st.sidebar.slider("Verformungs-Skalierung", 0.0, 2.0, 1.0, 0.05)

    st.sidebar.markdown("---")
    st.sidebar.header("Optimierer")
    mass_fraction = st.sidebar.slider("Massenreduktionsfaktor", 0.05, 1.0, 0.5, 0.05)

    # --- Tabs ---
    tab_struct, tab_io, tab_mat = st.tabs(["Struktur & Analyse", "Speichern / Laden", "Materialien"])

    with tab_mat:
        _tab_materialien()

    with tab_struct:
        s = st.session_state.structure
        if not s:
            st.info("Struktur initialisieren (Sidebar links).")
        else:
            _tab_struktur(s, scale_factor, mass_fraction)

    with tab_io:
        s = st.session_state.structure
        if not s:
            st.info("Struktur initialisieren (Sidebar links).")
        else:
            _tab_speichern(s, scale_factor)


if __name__ == "__main__":
    main()
