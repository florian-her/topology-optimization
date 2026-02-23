# topology-optimization

Interactive web application for 2D structural topology optimization. Defines mechanical structures as spring-mass systems on a graph, solves for displacements via FEM, and iteratively removes low-energy nodes to maximize stiffness.

## Installation

**Virtuelle Umgebung erstellen und aktivieren (erforderlich):**

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

**Dependencies installieren:**
```bash
pip install -r requirements.txt
```

## Starten

```bash
streamlit run view/app.py
```

## Tests

```bash
python -m pytest tests/
```

## Projektstruktur

```
topo_optimizer/
├── model/
│   ├── node.py              # Klasse Node (Position, Freiheitsgrade, Lager, Kräfte)
│   ├── spring.py            # Klasse Spring (Steifigkeit, Steifigkeitsmatrix, Energie)
│   ├── structure.py         # Klasse Structure (verwaltet Nodes + Springs)
│   └── graph.py             # Graph-Wrapper (NetworkX), Zusammenhangsprüfung
├── solver/
│   ├── fem_solver.py        # Globale Steifigkeitsmatrix assemblieren, LGS lösen
│   └── matrix_utils.py      # Transformationsmatrix, Regularisierung
├── optimizer/
│   ├── topology_optimizer.py  # Iterative Optimierung, Energiekriterium
│   └── validators.py          # Zusammenhangsprüfung, Lastpfad-Check
├── view/
│   ├── app.py               # Streamlit Hauptseite
│   ├── sidebar.py           # Eingabe: Bauraum, Kräfte, Lager
│   └── visualization.py     # Struktur-Plot, Verformung, Heatmap
├── persistence/
│   └── io_handler.py        # Speichern/Laden (JSON), Bild-Export
├── tests/
│   ├── test_solver.py
│   ├── test_optimizer.py
│   └── test_mbb_beam.py
├── requirements.txt
└── README.md
```
