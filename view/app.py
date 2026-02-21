import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import numpy as np

from model.structure import Structure
from solver.fem_solver import solve_structure
from optimizer.topology_optimizer import TopologyOptimizer
from view.visualization import plot_structure

st.set_page_config(page_title="TopoOptimizer 2D", layout="wide")


def _apply_default_bcs(structure: Structure) -> None:
    """Standard-Randbedingungen: linke Spalte fixiert, Kraft rechts-Mitte."""
    for y in range(structure.height):
        nid = structure._node_id(0, y)
        structure.nodes[nid].fix_x = 1
        structure.nodes[nid].fix_y = 1

    mid_y = structure.height // 2
    nid = structure._node_id(structure.width - 1, mid_y)
    structure.nodes[nid].force_y = 1.0


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

    # --- Sidebar ---
    st.sidebar.header("Gitter")
    width = st.sidebar.slider("Breite (Nodes)", 3, 30, 10)
    height = st.sidebar.slider("Höhe (Nodes)", 3, 15, 6)

    if st.sidebar.button("Struktur initialisieren"):
        s = Structure(width, height)
        st.session_state.structure = s
        st.session_state.u = None
        st.session_state.energies = None
        st.session_state.energy_history = []

    if st.session_state.structure:
        if st.sidebar.button("Standard-Lagerung setzen"):
            _apply_default_bcs(st.session_state.structure)
            st.session_state.u = None
            st.session_state.energies = None

    st.sidebar.markdown("---")
    st.sidebar.header("Darstellung")
    scale_factor = st.sidebar.slider("Verformungs-Skalierung", 0.0, 50.0, 0.0, 0.5)

    st.sidebar.markdown("---")
    st.sidebar.header("Optimierer")
    n_steps = st.sidebar.number_input("Schritte", min_value=1, max_value=500, value=10, step=1)

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
                    st.session_state.u = None
                    st.session_state.energies = None
                    st.rerun()

        st.markdown("---")

        # --- FEM + Optimizer ---
        st.subheader("Analyse")

        if st.button("FEM lösen"):
            try:
                with st.spinner("Löse Ku=F …"):
                    u = solve_structure(s)
                if u is None:
                    st.error("FEM konnte nicht gelöst werden.")
                else:
                    st.session_state.u = u
                    st.session_state.energies = TopologyOptimizer.compute_spring_energies(s, u)
                    total_e = sum(st.session_state.energies.values())
                    st.success(f"Energie: {total_e:.4f}")
            except AssertionError as e:
                st.error(str(e))

        if st.button("1 Schritt"):
            if st.session_state.u is None:
                st.warning("Zuerst FEM lösen.")
            else:
                removed = TopologyOptimizer.optimization_step(s, st.session_state.u)
                if removed is None:
                    st.warning("Keine Feder mehr entfernbar.")
                else:
                    u = solve_structure(s)
                    st.session_state.u = u
                    st.session_state.energies = (
                        TopologyOptimizer.compute_spring_energies(s, u) if u is not None else None
                    )
                    total_e = sum(st.session_state.energies.values()) if st.session_state.energies else 0
                    st.session_state.energy_history.append(total_e)
                    st.success(f"Feder {removed} entfernt")

        if st.button(f"{int(n_steps)} Schritte"):
            with st.spinner(f"Optimiere {int(n_steps)} Schritte …"):
                history = TopologyOptimizer.run(s, n_steps=int(n_steps))
                st.session_state.energy_history.extend(history)
                u = solve_structure(s)
                st.session_state.u = u
                st.session_state.energies = (
                    TopologyOptimizer.compute_spring_energies(s, u) if u is not None else None
                )
            active = sum(1 for sp in s.springs if sp.active)
            st.success(f"{len(history)} Schritte · {active} Federn aktiv")

        if st.button("Reset"):
            s2 = Structure(s.width, s.height)
            st.session_state.structure = s2
            st.session_state.u = None
            st.session_state.energies = None
            st.session_state.energy_history = []
            st.rerun()

        # --- Statistiken ---
        st.markdown("---")
        active = sum(1 for sp in s.springs if sp.active)
        st.metric("Federn aktiv", f"{active} / {len(s.springs)}")

        if st.session_state.energy_history:
            st.line_chart(st.session_state.energy_history)


if __name__ == "__main__":
    main()
