import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import numpy as np
from copy import deepcopy

from model.structure import Structure
from solver.fem_solver import solve_structure
from optimizer.topology_optimizer import TopologyOptimizer
from view.visualization import plot_structure
from persistence.io_handler import IOHandler

st.set_page_config(page_title="TopoOptimizer 2D", layout="wide")


def _has_forces(structure: Structure) -> bool:
    """Prüft ob mindestens eine Kraft definiert ist."""
    return any(n.force_x != 0 or n.force_y != 0 for n in structure.nodes)


def _has_bcs(structure: Structure) -> bool:
    """Prüft ob mindestens eine Lagerung definiert ist."""
    return any(n.fix_x or n.fix_y for n in structure.nodes)


def _apply_default_bcs(structure: Structure) -> None:
    """Standard-Randbedingungen: Festlager unten links, Loslager unten rechts, Kraft unten Mitte."""
    bottom = structure.height - 1

    nid = structure._node_id(0, bottom)
    structure.nodes[nid].fix_x = 1
    structure.nodes[nid].fix_y = 1

    nid = structure._node_id(structure.width - 1, bottom)
    structure.nodes[nid].fix_y = 1

    mid_x = structure.width // 2
    nid = structure._node_id(mid_x, bottom)
    structure.nodes[nid].force_y = -0.5


def main():
    st.title("2D Topologie-Optimierung")

    # Session State
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

    # --- Sidebar ---
    st.sidebar.header("Gitter")
    width = st.sidebar.slider("Breite (Nodes)", 3, 30, 10)
    height = st.sidebar.slider("Höhe (Nodes)", 3, 15, 6)

    if st.sidebar.button("Struktur initialisieren"):
        s = Structure(width, height)
        _apply_default_bcs(s)
        st.session_state.structure = s
        st.session_state.structure_base = deepcopy(s)
        st.session_state.u = None
        st.session_state.energies = None
        st.session_state.energy_history = []

    if st.session_state.structure:
        if st.sidebar.button("Standard-Lagerung setzen"):
            _apply_default_bcs(st.session_state.structure)
            st.session_state.structure_base = deepcopy(st.session_state.structure)
            st.session_state.u = None
            st.session_state.energies = None

    st.sidebar.markdown("---")
    st.sidebar.header("Speichern / Laden")

    uploaded = st.sidebar.file_uploader("Struktur laden (.json)", type=["json"])
    if uploaded is not None and uploaded.name != st.session_state.last_uploaded:
        try:
            s_loaded = IOHandler.load_from_bytes(uploaded.read())
            st.session_state.structure = s_loaded
            st.session_state.structure_base = deepcopy(s_loaded)
            st.session_state.u = None
            st.session_state.energies = None
            st.session_state.energy_history = []
            st.session_state.last_uploaded = uploaded.name
            st.session_state.status_msg = f"Struktur geladen: {uploaded.name}"
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Ladefehler: {e}")

    st.sidebar.markdown("---")
    st.sidebar.header("Darstellung")
    scale_factor = st.sidebar.slider("Verformungs-Skalierung", 0.0, 2.0, 1.0, 0.05)

    st.sidebar.markdown("---")
    st.sidebar.header("Optimierer")
    mass_fraction = st.sidebar.slider("Massenreduktionsfaktor", 0.05, 1.0, 0.5, 0.05)

    # --- Hauptbereich ---
    s = st.session_state.structure

    if not s:
        st.info("Struktur initialisieren (Sidebar links).")
        return

    col_plot, col_ctrl = st.columns([3, 1])

    with col_plot:
        # Knotenauswahl
        sel_c1, sel_c2 = st.columns(2)
        sel_x = sel_c1.slider("Knoten X", 0, s.width - 1, 0)
        sel_y = sel_c2.slider("Knoten Y", 0, s.height - 1, 0)

        selected_node = next(
            (n for n in s.nodes if int(n.x) == sel_x and int(n.y) == sel_y), None
        )

        fig = plot_structure(
            s,
            energies=st.session_state.energies,
            scale_factor=scale_factor,
            highlight_node=selected_node,
        )
        st.pyplot(fig)

        dl1, dl2 = st.columns(2)
        dl1.download_button(
            "Struktur (JSON)",
            IOHandler.to_json_bytes(s),
            file_name="struktur.json",
            mime="application/json",
            use_container_width=True,
        )
        dl2.download_button(
            "Bild (PNG)",
            IOHandler.to_png_bytes(fig),
            file_name="struktur.png",
            mime="image/png",
            use_container_width=True,
        )

    with col_ctrl:
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

        if st.button("1 Schritt"):
            try:
                if not _has_forces(s):
                    st.warning("Keine Kräfte definiert — bitte zuerst Kräfte setzen.")
                else:
                    if st.session_state.u is None:
                        st.session_state.u = solve_structure(s)
                        if st.session_state.u is not None:
                            st.session_state.energies = TopologyOptimizer.compute_spring_energies(
                                s, st.session_state.u
                            )

                    if st.session_state.u is None:
                        st.error("FEM konnte nicht gelöst werden.")
                    else:
                        removed = TopologyOptimizer.optimization_step(s, st.session_state.u)
                        if removed is None:
                            st.warning("Kein Knoten mehr entfernbar.")
                        else:
                            u = solve_structure(s)
                            st.session_state.u = u
                            st.session_state.energies = (
                                TopologyOptimizer.compute_spring_energies(s, u) if u is not None else None
                            )
                            total_e = sum(st.session_state.energies.values()) if st.session_state.energies else 0
                            st.session_state.energy_history.append(total_e)
                            st.session_state.status_msg = f"Knoten {removed} entfernt"
                            st.rerun()
            except Exception as e:
                st.error(f"Optimierer-Fehler: {e}")

        if st.button(f"Optimieren ({int(mass_fraction * 100)}% Masse)"):
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

        if st.button("Reset"):
            s2 = Structure(s.width, s.height)
            st.session_state.structure = s2
            st.session_state.structure_base = deepcopy(s2)
            st.session_state.u = None
            st.session_state.energies = None
            st.session_state.energy_history = []
            st.rerun()

        # --- Statistiken ---
        st.markdown("---")
        st.metric("Knoten aktiv", f"{s.active_node_count()} / {len(s.nodes)}")
        st.metric("Federn aktiv", f"{s.active_spring_count()} / {len(s.springs)}")

        if st.session_state.energy_history:
            st.line_chart(st.session_state.energy_history)


if __name__ == "__main__":
    main()
