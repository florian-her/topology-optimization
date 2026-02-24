import numpy as np
import numpy.typing as npt

from model.structure import Structure
from solver.fem_solver import solve_structure
from optimizer.validators import StructureValidator


class TopologyOptimizer:
    """Optimiert die Struktur indem unwichtige Knoten schrittweise entfernt werden."""

    @staticmethod
    def compute_spring_energies(
        structure: Structure,
        u: npt.NDArray[np.float64],
    ) -> dict[int, float]:
        """Berechnet die Verformungsenergie jeder aktiven Feder.

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        u : npt.NDArray[np.float64]
            Verschiebungsvektor aus der FEM-Lösung.

        Returns
        -------
        dict[int, float]
            Feder-ID → Verformungsenergie.
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
        """Berechnet die Wichtigkeit jedes Knotens aus den Federenergien.

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        u : npt.NDArray[np.float64]
            Verschiebungsvektor aus der FEM-Lösung.

        Returns
        -------
        dict[int, float]
            Knoten-ID → Wichtigkeit (nur freie, unbelastete Knoten).
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
        """Entfernt den unwichtigsten Knoten, wenn Struktur intakt bleibt.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird direkt verändert).
        u : npt.NDArray[np.float64]
            Verschiebungsvektor aus der FEM-Lösung.

        Returns
        -------
        int | None
            ID des entfernten Knotens, oder None falls keiner entfernbar.
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
        """Führt die Optimierung durch bis der Massenanteil erreicht ist.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird direkt verändert).
        mass_fraction : float
            Anteil der Knoten die übrig bleiben sollen, z.B. 0.5 = 50%.

        Returns
        -------
        list[float]
            Gesamtenergie nach jedem Schritt.
        """
        assert 0.0 < mass_fraction < 1.0, "mass_fraction muss zwischen 0 und 1 liegen."

        total_nodes = len(structure.nodes)
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
