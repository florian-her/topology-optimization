import streamlit as st
import numpy as np
from model.structure import Structure
from view.visualization import plot_structure

st.set_page_config(page_title="TopoOptimizer 2D", layout="wide")

def main():
    st.title("2D Topologie-Optimierung")

    # 1. Init
    if 'structure' not in st.session_state:
        st.session_state.structure = None
    if 'optimized' not in st.session_state:
        st.session_state.optimized = False

    # 2. Sidebar: Nur noch Grid-Einstellungen
    st.sidebar.header("Gitter-Parameter")
    width = st.sidebar.slider("Breite", 5, 50, 20)
    height = st.sidebar.slider("Höhe", 5, 20, 10)
    
    if st.sidebar.button("Struktur initialisieren"):
        st.session_state.structure = Structure(width, height)
        st.session_state.optimized = False
        st.rerun()

    st.sidebar.markdown("---")
    scaling = st.sidebar.slider("Verformungs-Skalierung", 0.0, 10.0, 1.0, 0.1)

    # 3. Hauptbereich
    col_vis, col_tools = st.columns([3, 1])

    structure = st.session_state.structure

    with col_vis:
        st.subheader("Visualisierung & Auswahl")
        
        selected_node = None
        
        if structure:
            # Spalten, damit X und Y nebeneinander liegen
            sel_c1, sel_c2 = st.columns(2)
            
            # 1. Waagerechter Regler (X)
            sel_x = sel_c1.slider("X-Koordinate wählen", 0, structure.width - 1, 0)
            
            # 2. Senkrechter Regler (Y) - hier als normaler Slider
            sel_y = sel_c2.slider("Y-Koordinate wählen", 0, structure.height - 1, 0)

            # Den passenden Knoten im Speicher finden
            for n in structure.nodes:
                if n.x == sel_x and n.y == sel_y:
                    selected_node = n
                    break
            
            # Plotten mit Highlight
            fig = plot_structure(structure, scale_factor=scaling, highlight_node=selected_node)
            st.pyplot(fig)
        
        else:
            st.info("Bitte initialisiere eine Struktur.")

    # 4. Bearbeitungs-Menü (Rechts)
    with col_tools:
        st.subheader("Bearbeitung")
        
        if structure and selected_node:
            st.markdown(f"**Gewählt: Knoten {selected_node.id}**")
            st.markdown(f"Position: ({selected_node.x}, {selected_node.y})")
            
            # Formular für den markierten Knoten
            with st.form("node_editor"):
                st.write("Randbedingungen")
                c1, c2 = st.columns(2)
                fix_x = c1.checkbox("Fix X", value=bool(selected_node.fix_x))
                fix_y = c2.checkbox("Fix Y", value=bool(selected_node.fix_y))
                
                st.write("Kräfte [N]")
                force_x = st.number_input("Fx", value=float(selected_node.force_x), step=0.1)
                force_y = st.number_input("Fy", value=float(selected_node.force_y), step=0.1)
                
                if st.form_submit_button("Anwenden"):
                    selected_node.fix_x = 1 if fix_x else 0
                    selected_node.fix_y = 1 if fix_y else 0
                    selected_node.force_x = force_x
                    selected_node.force_y = -force_y
                    st.success("Gespeichert!")
                    st.rerun()
            
            st.markdown("---")
            
            # FEM Button
            if st.button("FEM Analyse starten"):
                from solver.fem_solver import FEMSolver
                solver = FEMSolver(structure)
                try:
                    solver.solve()
                    st.success("Fertig!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")

if __name__ == "__main__":
    main()