import streamlit as st
import numpy as np
from model.structure import Structure
from view.visualization import plot_structure

st.set_page_config(page_title="TopoOptimizer 2D", layout="wide")

def main():
    st.title("2D Topologie-Optimierung")
    st.write("Optimierung von Stabwerkstrukturen mittels FEM.")

    # 2. Session State Initialisierung für Streamlit
    if 'structure' not in st.session_state:
        st.session_state.structure = None
    if 'optimized' not in st.session_state:
        st.session_state.optimized = False

    # 3. Sidebar für Eingabeparameter
    st.sidebar.header("Parameter")
    width = st.sidebar.slider("Breite (Nodes)", 5, 50, 20)
    height = st.sidebar.slider("Höhe (Nodes)", 5, 20, 10)
    
    if st.sidebar.button("Struktur initialisieren"):
        st.session_state.structure = Structure(width, height)
        st.session_state.optimized = False
        st.success(f"Raster mit {width}x{height} Nodes erstellt.")

    st.sidebar.subheader("Randbedingungen")

    if st.session_state.structure:
        # Button für Standard-Lagerung (Linke Seite fest)
        if st.sidebar.button("Linke Seite fixieren"):
            for node in st.session_state.structure.nodes:
                if node.x == 0:
                    node.fix_x = 1
                    node.fix_y = 1
            st.sidebar.success("Lager links gesetzt!")

        # Button für eine Last (Rechte Seite, Mitte)
        if st.sidebar.button("Last rechts mittig setzen"):
            max_x = st.session_state.structure.width - 1
            mid_y = st.session_state.structure.height // 2
            for node in st.session_state.structure.nodes:
                if node.x == max_x and node.y == mid_y:
                    node.force_y = -10.0 # Kraft nach unten
            st.sidebar.success("Last gesetzt!")

    # 4. Hauptbereich: Darstellung & Steuerung
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Visualisierung")
        if st.session_state.structure:
            # Nutzt deine visualization.py
            fig = plot_structure(st.session_state.structure)
            st.pyplot(fig)
        else:
            st.info("Bitte initialisiere zuerst eine Struktur in der Sidebar.")

    with col2:
        st.subheader("Aktionen")
        if st.session_state.structure:
            if st.button("FEM Analyse starten"):
                from solver.fem_solver import FEMSolver
                solver = FEMSolver(st.session_state.structure)
                try:
                    solver.solve()
                    st.session_state.optimized = True # Trigger für Re-Drawing
                    st.success("Berechnung fertig!")
                except Exception as e:
                    st.error(str(e))
                
            if st.button("Optimierungsschritt"):
                # Hier später optimizer/topology_optimizer.py aufrufen
                st.write("Elemente entfernt (Dummy)")

# Start der App
if __name__ == "__main__":
    main()