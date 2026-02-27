# 2D Topologie-Optimierung

Interaktive Web-App zur 2D-Topologieoptimierung mechanischer Strukturen — gebaut mit Python und Streamlit.

Uni-Abschlussprojekt, MCI Innsbruck, Softwaredesign ILV, WS 2025/26.

**Live-Demo:** [topology-optimization.streamlit.app](https://topology-optimization.streamlit.app/)

---

## Installation & Start

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
streamlit run view/app.py
```

## Tests

```bash
python -m pytest tests/
```

---

## Projektstruktur

```
topology-optimization/
├── model/
│   ├── node.py              # Knoten: Position, Lager, Kräfte
│   ├── spring.py            # Feder: Steifigkeit, lokale Steifigkeitsmatrix
│   ├── structure.py         # Struktur: Gitter aus Knoten + Federn
│   ├── material.py          # Materialdatenbank (Stahl, Alu, Titan, …)
│   └── graph.py             # NetworkX-Wrapper für Zusammenhangsprüfungen
├── solver/
│   ├── fem_solver.py        # K·u = F assemblieren und lösen
│   └── matrix_utils.py      # Transformationsmatrizen, Richtungsvektoren
├── optimizer/
│   ├── topology_optimizer.py  # Kern-Algorithmus, Batch-Steuerung, Symmetrie
│   └── validators.py          # Zusammenhang-, Lastpfad- und Stabilitätsprüfung
├── view/
│   ├── app.py               # Streamlit-App, Session-State, Tabs
│   ├── sidebar.py           # Eingabe: Gitter, Kräfte, Lager, Material
│   └── visualization.py     # Plotly-Plot: Struktur, Verformung, Heatmap
├── persistence/
│   └── io_handler.py        # JSON speichern/laden, PNG/GIF exportieren
└── tests/
    ├── test_solver.py
    ├── test_optimizer.py
    └── test_mbb_beam.py
```

---

## Wie funktioniert das?

### FEM-Solver

Die Struktur ist ein **Feder-Massen-Gitter** — jeder Knoten hat 2 Freiheitsgrade (x und y). Aus den einzelnen Federn wird eine globale Steifigkeitsmatrix `K` zusammengebaut, Randbedingungen (Lager, Kräfte) werden reingebracht, und das Gleichungssystem `K·u = F` wird mit `scipy.sparse.linalg.spsolve` gelöst. Das Ergebnis sind die Verschiebungen aller Knoten.

Steifigkeiten: horizontal/vertikal `k = 1.0`, diagonal `k = 1/√2`.

### Optimierungsalgorithmus

Wir nutzen einen **knotenbasierten ESO-Ansatz** (Evolutionary Structural Optimization):

1. FEM lösen → Verschiebungen `u`
2. Verformungsenergie jeder Feder: `E = 0.5 · uᵀ · K · u`
3. Energie auf die Endknoten verteilen → jeder Knoten bekommt einen Energiewert
4. Die "unwichtigsten" Knoten (niedrigste Energie) in einem Batch entfernen
5. Validierung: Struktur muss zusammenhängend bleiben, alle Lasten müssen noch zu einem Lager kommen
6. Wiederholen bis Ziel-Massenanteil erreicht

Alternativ würde **SIMP** (industrieüblicher Standard) kontinuierliche Materialdichten verwenden — das ergibt glattere, ästhetischere Ergebnisse. Knotenbasiert ist dafür einfacher umzusetzen und liefert strukturell ähnliche Topologien.

### Topologie-Validator

Vor jedem Knotenentfernen werden drei Dinge geprüft:
- **Zusammenhang**: bleibt der Graph in einem Stück? (NetworkX)
- **Lastpfade**: kann jede Kraft noch ein Lager erreichen?
- **Mechanismen**: werden Nachbarknoten instabil (nur noch parallele Federn)?

---

## Features

### Genau vs. Schnell — und warum das wichtig ist

Die **genaue Methode** löst nach jedem Batch neu die FEM und prüft jeden Kandidaten vollständig durch den Validator. Das ist korrekt, aber langsam. Bei einem 60×10-Gitter mit 50% Masse kann das schon mal 1–2 Minuten dauern, weil gegen Ende des Optimierungsvorgangs fast jeder einzelne Knoten einzeln geprüft werden muss (Batch-Größe 1) und dabei jedes Mal das komplette LGS neu gelöst wird.

Die **schnelle Methode** überspringt einen Teil der Validierungen und arbeitet mit größeren Batches durch. Das ist deutlich schneller, kann aber früher abbrechen — nämlich dann, wenn die Struktur in einen Zustand kommt, aus dem heraus kein weiterer valider Schritt mehr gefunden wird, obwohl der Ziel-Massenanteil noch nicht erreicht ist.

### Adaptive Batch-Größen

Wir entfernen nicht immer gleich viele Knoten pro Schritt. Am Anfang (viel Material übrig) sind größere Batches sinnvoll — da kann man problemlos 20–30 Knoten auf einmal rauswerfen, ohne die Struktur zu gefährden. Je näher man dem Ziel kommt, desto kleiner wird der Batch, bis man am Ende bei Einzelknoten landet. Das verhindert, dass kurz vor dem Ziel die Struktur durch einen zu großen Schritt auseinanderfällt.

### Symmetrie für mehr Speed

Da die genaue Methode so lange braucht, gibt es einen **Symmetrie-Modus**: wird ein Knoten entfernt, fliegt sein gespiegeltes Pendant automatisch mit. Das halbiert die Anzahl der nötigen Iterationen und macht die Optimierung deutlich schneller — außerdem entstehen dadurch symmetrische Strukturen, was bei symmetrischen Lasten das physikalisch richtige Ergebnis ist.

### Materialdatenbank

Stahl, Aluminium, Titan und Beton sind voreingestellt. Das E-Modul des gewählten Materials skaliert die Steifigkeiten direkt. Eigene Materialien lassen sich in der App anlegen.

### Weitere Features

| Feature | Beschreibung |
|---|---|
| Dehnungs-Heatmap | Farbkodierte Darstellung der Federdehnungen |
| Verformungsanzeige | Überlagerter Plot der verformten Struktur |
| Spannungsbegrenzung | Optimierung stoppt bei Überschreitung eines Grenzwerts |
| GIF-Export | Animierter Export des Optimierungsverlaufs |
| JSON Speichern/Laden | Vollständiger Struktur-Zustand speicherbar und wiederherstellbar |
| Interaktive Knotenauswahl | Knoten per Klick auswählen und Infos einsehen |
| Standard-Lagerung | Ein-Klick MBB-Balken Konfiguration |

---

## Deployment

Die App ist via **Streamlit Community Cloud** deployed und öffentlich erreichbar:

[topology-optimization.streamlit.app](https://topology-optimization.streamlit.app/)

---

## Einsatz von KI

Dieses Projekt wurde mit Unterstützung von **Claude (Anthropic)** entwickelt. KI wurde verwendet für:

- Implementierung und Debugging des FEM-Solvers und Validators
- Entwicklung des adaptiven Batch-Algorithmus und der Symmetrie-Logik
- Unterstützung beim Streamlit-UI-Aufbau
- Code-Reviews und Refactoring

Die fachlichen Grundlagen (FEM, ESO, Validierungslogik) kommen aus dem Studium — KI hat geholfen, diese schneller und sauberer in funktionierenden Code umzusetzen.

---

## Tech-Stack

**Python 3.11** · **Streamlit** · **NumPy/SciPy** · **NetworkX** · **Plotly** · **pytest**
