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


def _apply_boundary_conditions(structure: Structure) -> None:
    """Setzt Standard-Randbedingungen: linke Spalte fixiert, Kraft rechts-Mitte."""
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
        _apply_boundary_conditions(s)
        st.session_state.structure = s
        st.session_state.u = None
        st.session_state.energies = None
        st.session_state.energy_history = []

    st.sidebar.markdown("---")
    st.sidebar.header("Optimierer")
    n_steps = st.sidebar.number_input("Schritte", min_value=1, max_value=500, value=10, step=1)

    # --- Hauptbereich ---
    col_plot, col_ctrl = st.columns([4, 1])

    with col_plot:
        if st.session_state.structure:
            fig = plot_structure(st.session_state.structure, st.session_state.energies)
            st.pyplot(fig)
        else:
            st.info("Struktur initialisieren (Sidebar links).")

    with col_ctrl:
        st.subheader("Aktionen")
        s = st.session_state.structure

        if s:
            # FEM lösen
            if st.button("FEM lösen"):
                with st.spinner("Löse Ku=F …"):
                    u = solve_structure(s)
                if u is None:
                    st.error("FEM konnte nicht gelöst werden.")
                else:
                    st.session_state.u = u
                    st.session_state.energies = TopologyOptimizer.compute_spring_energies(s, u)
                    total_e = sum(st.session_state.energies.values())
                    st.success(f"Energie: {total_e:.4f}")

            # Einzelschritt
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

            # N Schritte
            if st.button(f"{n_steps} Schritte"):
                with st.spinner(f"Optimiere {n_steps} Schritte …"):
                    history = TopologyOptimizer.run(s, n_steps=int(n_steps))
                    st.session_state.energy_history.extend(history)
                    u = solve_structure(s)
                    st.session_state.u = u
                    st.session_state.energies = (
                        TopologyOptimizer.compute_spring_energies(s, u) if u is not None else None
                    )
                active = sum(1 for sp in s.springs if sp.active)
                st.success(f"{len(history)} Schritte · {active} Federn aktiv")

            # Reset
            if st.button("Reset"):
                s2 = Structure(s.width, s.height)
                _apply_boundary_conditions(s2)
                st.session_state.structure = s2
                st.session_state.u = None
                st.session_state.energies = None
                st.session_state.energy_history = []

            # Statistiken
            st.markdown("---")
            active = sum(1 for sp in s.springs if sp.active)
            st.metric("Federn aktiv", f"{active} / {len(s.springs)}")

            if st.session_state.energy_history:
                st.line_chart(st.session_state.energy_history)


if __name__ == "__main__":
    main()
