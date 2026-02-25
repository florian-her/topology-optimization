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
    def compute_spring_stresses(
        structure: Structure,
        u: npt.NDArray[np.float64],
    ) -> dict[int, float]:
        """Berechnet die Normalspannung jeder aktiven Feder in MPa.

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        u : npt.NDArray[np.float64]
            Verschiebungsvektor aus der FEM-Lösung.

        Returns
        -------
        dict[int, float]
            Feder-ID → |σ| in MPa  (σ = E · Δl / l₀).
        """
        E_MPa = structure.material.E * 1000.0
        stresses: dict[int, float] = {}

        for spring in structure.springs:
            if not spring.active:
                continue
            i   = spring.node_a.id
            j   = spring.node_b.id
            e_n = spring.get_direction_vector()
            l0  = spring.get_length()
            du  = np.array([u[2 * j] - u[2 * i], u[2 * j + 1] - u[2 * i + 1]])
            eps = float(np.dot(e_n, du)) / l0
            stresses[spring.id] = abs(E_MPa * eps)

        return stresses

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
        removed = TopologyOptimizer.optimization_batch(structure, u, batch_size=1)
        return None if removed == 0 else -1

    @staticmethod
    def optimization_batch(
        structure: Structure,
        u: npt.NDArray[np.float64],
        batch_size: int,
    ) -> int:
        """Entfernt bis zu batch_size Knoten auf Basis einer FEM-Lösung.

        Blattknoten (Grad ≤ 1) werden ohne Zusammenhangscheck direkt entfernt.
        Alle anderen durchlaufen den vollen can_remove_node-Check.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird direkt verändert).
        u : npt.NDArray[np.float64]
            Verschiebungsvektor aus der FEM-Lösung.
        batch_size : int
            Maximale Anzahl zu entfernender Knoten.

        Returns
        -------
        int
            Anzahl tatsächlich entfernter Knoten.
        """
        node_energies = TopologyOptimizer.compute_node_energies(structure, u)
        if not node_energies:
            return 0

        # Knotengrad einmalig berechnen (Anzahl aktiver Federn je Knoten)
        degree: dict[int, int] = {}
        for sp in structure.springs:
            if sp.active:
                degree[sp.node_a.id] = degree.get(sp.node_a.id, 0) + 1
                degree[sp.node_b.id] = degree.get(sp.node_b.id, 0) + 1

        sorted_nodes = sorted(node_energies.items(), key=lambda x: x[1])
        removed = 0

        for node_id, _ in sorted_nodes:
            if removed >= batch_size:
                break

            if degree.get(node_id, 0) <= 1:
                # Blattknoten: topologisch immer sicher zu entfernen
                structure.remove_node(node_id)
                removed += 1
            elif StructureValidator.can_remove_node(structure, node_id):
                structure.remove_node(node_id)
                removed += 1

        return removed

    @staticmethod
    def run(
        structure: Structure,
        mass_fraction: float,
        batch_fraction: float = 0.05,
    ) -> list[float]:
        """Führt die Optimierung durch bis der Massenanteil erreicht ist.

        Pro FEM-Lösung werden bis zu batch_fraction * aktive_Knoten Knoten
        auf einmal entfernt. Das reduziert die Anzahl teurer FEM-Solves
        drastisch bei moderatem Qualitätsverlust.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird direkt verändert).
        mass_fraction : float
            Anteil der Knoten die übrig bleiben sollen, z.B. 0.5 = 50%.
        batch_fraction : float, optional
            Anteil aktiver Knoten der pro FEM-Solve entfernt wird (Standard 5%).

        Returns
        -------
        list[float]
            Gesamtenergie nach jedem FEM-Solve.
        """
        assert 0.0 < mass_fraction < 1.0, "mass_fraction muss zwischen 0 und 1 liegen."
        assert 0.0 < batch_fraction <= 1.0, "batch_fraction muss zwischen 0 und 1 liegen."

        total_nodes = len(structure.nodes)
        target_nodes = max(2, int(total_nodes * mass_fraction))

        energy_history: list[float] = []

        while structure.active_node_count() > target_nodes:
            u = solve_structure(structure)
            if u is None:
                break

            spring_energies = TopologyOptimizer.compute_spring_energies(structure, u)
            energy_history.append(sum(spring_energies.values()))

            n_active = structure.active_node_count()
            batch_size = max(1, int(n_active * batch_fraction))
            batch_size = min(batch_size, n_active - target_nodes)

            removed = TopologyOptimizer.optimization_batch(structure, u, batch_size)
            if removed == 0:
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
    print(f"FEM-Solves: {len(history)} (ohne Batch wären es {len(s.nodes) // 2})")
    print(f"Energie-Verlauf: {[f'{e:.4f}' for e in history]}")
