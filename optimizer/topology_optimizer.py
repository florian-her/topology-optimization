import numpy as np
import numpy.typing as npt

from model.structure import Structure
from solver.fem_solver import solve_structure
from optimizer.validators import StructureValidator


class TopologyOptimizer:
    """Iterativer Topologieoptimierer auf Basis der Verformungsenergie.

    Strategie: Pro Schritt wird die 1 aktivste Feder mit der geringsten
    Verformungsenergie entfernt, sofern der Zusammenhang gewährleistet bleibt.
    """

    @staticmethod
    def compute_spring_energies(
        structure: Structure,
        u: npt.NDArray[np.float64],
    ) -> dict[int, float]:
        """Berechnet die Verformungsenergie jeder aktiven Feder.

        Formel: E = 0.5 * u_e^T @ Ko @ u_e
        (u_e = Verschiebungsvektor der 4 DOFs des Federelements)

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        u : npt.NDArray[np.float64]
            Globaler Verschiebungsvektor.

        Returns
        -------
        dict[int, float]
            Mapping spring_id → Verformungsenergie.
        """
        energies: dict[int, float] = {}

        for spring in structure.springs:
            if not spring.active:
                continue

            i = spring.node_a.id
            j = spring.node_b.id
            u_e = np.array([u[2 * i], u[2 * i + 1], u[2 * j], u[2 * j + 1]])
            Ko = spring.get_stiffness_matrix()
            energies[spring.id] = 0.5 * float(u_e @ Ko @ u_e)

        return energies

    @staticmethod
    def optimization_step(
        structure: Structure,
        u: npt.NDArray[np.float64],
    ) -> int | None:
        """Entfernt die Feder mit der geringsten Verformungsenergie.

        Prüft Zusammenhang VOR dem Entfernen. Überspringt Federn, die den
        Zusammenhang zerstören würden (Brücken im Graphen).

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird in-place modifiziert).
        u : npt.NDArray[np.float64]
            Globaler Verschiebungsvektor der aktuellen FEM-Lösung.

        Returns
        -------
        int | None
            spring_id der entfernten Feder, oder None wenn keine entfernt werden kann.
        """
        energies = TopologyOptimizer.compute_spring_energies(structure, u)

        if not energies:
            return None

        # Aufsteigend nach Energie sortieren
        sorted_springs = sorted(energies.items(), key=lambda x: x[1])

        for spring_id, energy in sorted_springs:
            if StructureValidator.can_remove_spring(structure, spring_id):
                spring = next(s for s in structure.springs if s.id == spring_id)
                spring.active = False
                return spring_id

        return None  # Alle Federn sind Brücken

    @staticmethod
    def run(
        structure: Structure,
        n_steps: int,
    ) -> list[float]:
        """Führt n_steps Optimierungsschritte durch.

        In jedem Schritt: FEM lösen → schwächste entfernbare Feder deaktivieren.

        Parameters
        ----------
        structure : Structure
            Die Ausgangsstruktur (wird in-place modifiziert).
        n_steps : int
            Anzahl der Optimierungsschritte.

        Returns
        -------
        list[float]
            Gesamt-Verformungsenergie nach jedem Schritt.
        """
        assert n_steps > 0, "n_steps muss positiv sein."

        energy_history: list[float] = []

        for step in range(n_steps):
            u = solve_structure(structure)

            if u is None:
                print(f"Schritt {step}: FEM konnte nicht gelöst werden — Abbruch.")
                break

            energies = TopologyOptimizer.compute_spring_energies(structure, u)
            total_energy = sum(energies.values())
            energy_history.append(total_energy)

            removed = TopologyOptimizer.optimization_step(structure, u)

            if removed is None:
                print(f"Schritt {step}: Keine Feder mehr entfernbar — Abbruch.")
                break

        return energy_history


if __name__ == "__main__":
    from model.structure import Structure

    print("=" * 60)
    print("Topologieoptimierung: 4x4-Kragarm")
    print("=" * 60)

    s = Structure(4, 4)

    # Linke Spalte fixieren
    for y in range(s.height):
        nid = s._node_id(0, y)
        s.nodes[nid].fix_x = 1
        s.nodes[nid].fix_y = 1

    # Kraft an Mitte rechts (y=1)
    mid_right = s._node_id(s.width - 1, s.height // 2)
    s.nodes[mid_right].force_y = 10.0

    history = TopologyOptimizer.run(s, n_steps=10)
    active_springs = sum(1 for sp in s.springs if sp.active)

    print(f"\nAktive Federn nach 10 Schritten: {active_springs}")
    print(f"Energie-Verlauf: {[f'{e:.4f}' for e in history]}")
