import numpy as np
import numpy.typing as npt

from model.structure import Structure
from solver.fem_solver import solve_structure
from optimizer.validators import StructureValidator


class TopologyOptimizer:
    """Iterativer Topologieoptimierer auf Basis der Verformungsenergie.

    Strategie: Pro Schritt wird der Knoten mit der geringsten Knotenimportanz
    entfernt, sofern Zusammenhang und Lastpfade erhalten bleiben.
    """

    @staticmethod
    def compute_spring_energies(
        structure: Structure,
        u: npt.NDArray[np.float64],
    ) -> dict[int, float]:
        """Berechnet die Verformungsenergie jeder aktiven Feder.

        Formel: c^(i,j) = 0.5 * u_e^T @ Ko @ u_e

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
    def compute_node_energies(
        structure: Structure,
        u: npt.NDArray[np.float64],
    ) -> dict[int, float]:
        """Berechnet die Knotenimportanz als Summe der halben Federenergien.

        Formel:
            c_node = sum(c^(i,j) / 2) für alle angrenzenden aktiven Federn

        Nur freie aktive Knoten (nicht fixiert, nicht belastet) werden bewertet.

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        u : npt.NDArray[np.float64]
            Globaler Verschiebungsvektor.

        Returns
        -------
        dict[int, float]
            Mapping node_id → Knotenimportanz (nur optimierbare Knoten).
        """
        spring_energies = TopologyOptimizer.compute_spring_energies(structure, u)

        node_energy: dict[int, float] = {}
        for spring in structure.springs:
            if not spring.active:
                continue
            half_e = spring_energies[spring.id] / 2.0
            for nid in (spring.node_a.id, spring.node_b.id):
                node_energy[nid] = node_energy.get(nid, 0.0) + half_e

        result: dict[int, float] = {}
        for node in structure.nodes:
            if not node.active:
                continue
            if node.fix_x or node.fix_y:
                continue
            if node.force_x != 0 or node.force_y != 0:
                continue
            result[node.id] = node_energy.get(node.id, 0.0)

        return result

    @staticmethod
    def optimization_step(
        structure: Structure,
        u: npt.NDArray[np.float64],
    ) -> int | None:
        """Entfernt den Knoten mit der geringsten Knotenimportanz.

        Prüft Zusammenhang und Lastpfade VOR dem Entfernen.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird in-place modifiziert).
        u : npt.NDArray[np.float64]
            Globaler Verschiebungsvektor der aktuellen FEM-Lösung.

        Returns
        -------
        int | None
            node_id des entfernten Knotens, oder None wenn keiner entfernt werden kann.
        """
        node_energies = TopologyOptimizer.compute_node_energies(structure, u)

        if not node_energies:
            return None

        sorted_nodes = sorted(node_energies.items(), key=lambda x: x[1])

        for node_id, _ in sorted_nodes:
            if StructureValidator.can_remove_node(structure, node_id):
                structure.remove_node(node_id)
                return node_id

        return None

    @staticmethod
    def run(
        structure: Structure,
        mass_fraction: float,
    ) -> list[float]:
        """Optimiert die Struktur bis zum Ziel-Massenanteil.

        Schleife:
        FEM lösen → Knotenimportanzen berechnen → schwächsten entfernbaren
        Knoten deaktivieren → wiederholen bis Ist-Masse ≤ Soll-Masse.

        Parameters
        ----------
        structure : Structure
            Die Ausgangsstruktur (wird in-place modifiziert).
        mass_fraction : float
            Ziel-Massenanteil [0, 1]. 0.5 = 50% der Knoten behalten.

        Returns
        -------
        list[float]
            Gesamt-Verformungsenergie nach jedem Schritt.
        """
        assert 0.0 < mass_fraction < 1.0, "mass_fraction muss zwischen 0 und 1 liegen."

        total_nodes = structure.active_node_count()
        target_nodes = max(2, int(total_nodes * mass_fraction))

        energy_history: list[float] = []

        while structure.active_node_count() > target_nodes:
            u = solve_structure(structure)
            if u is None:
                break

            spring_energies = TopologyOptimizer.compute_spring_energies(structure, u)
            total_energy = sum(spring_energies.values())
            energy_history.append(total_energy)

            removed = TopologyOptimizer.optimization_step(structure, u)
            if removed is None:
                break

        return energy_history


if __name__ == "__main__":
    from model.structure import Structure

    print("=" * 60)
    print("Topologieoptimierung: 4x4-Kragarm (Massenreduktion 50%)")
    print("=" * 60)

    s = Structure(4, 4)

    for y in range(s.height):
        nid = s._node_id(0, y)
        s.nodes[nid].fix_x = 1
        s.nodes[nid].fix_y = 1

    mid_right = s._node_id(s.width - 1, s.height // 2)
    s.nodes[mid_right].force_y = -1.0

    history = TopologyOptimizer.run(s, mass_fraction=0.5)
    print(f"\nAktive Knoten nach Optimierung: {s.active_node_count()} / {len(s.nodes)}")
    print(f"Energie-Verlauf: {[f'{e:.4f}' for e in history]}")
