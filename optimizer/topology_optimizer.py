from collections.abc import Callable

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
        E_factor = structure.material.E / 210.0

        for spring in structure.springs:
            if not spring.active:
                continue

            i = spring.node_a.id
            j = spring.node_b.id
            u_e = np.array([u[2 * i], u[2 * i + 1], u[2 * j], u[2 * j + 1]])
            Ko = spring.get_stiffness_matrix() * E_factor
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
            stresses[spring.id] = abs(eps) * 100.0

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
    def _take_snapshot(structure: Structure) -> dict[str, list[bool]]:
        """Speichert den aktiven Zustand aller Knoten und Federn.

        Parameters
        ----------
        structure : Structure
            Die Struktur.

        Returns
        -------
        dict[str, list[bool]]
            Snapshot mit 'nodes' und 'springs' Listen.
        """
        return {
            "nodes": [n.active for n in structure.nodes],
            "springs": [s.active for s in structure.springs],
        }

    @staticmethod
    def _restore_snapshot(structure: Structure, snapshot: dict[str, list[bool]]) -> None:
        """Stellt den gespeicherten Zustand wieder her.

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        snapshot : dict[str, list[bool]]
            Snapshot aus _take_snapshot.
        """
        for i, active in enumerate(snapshot["nodes"]):
            structure.nodes[i].active = active
        for i, active in enumerate(snapshot["springs"]):
            structure.springs[i].active = active

    @staticmethod
    def _restore_node(structure: Structure, node_id: int) -> None:
        """Macht die Entfernung eines Knotens rückgängig.

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        node_id : int
            ID des wiederherzustellenden Knotens.
        """
        structure.nodes[node_id].active = True
        for sp in structure.springs:
            if sp.node_a.id == node_id or sp.node_b.id == node_id:
                other = sp.node_b if sp.node_a.id == node_id else sp.node_a
                if other.active:
                    sp.active = True

    @staticmethod
    def optimization_batch(
        structure: Structure,
        u: npt.NDArray[np.float64],
        batch_size: int,
        validate_fem: bool = False,
        fast_mode: bool = False,
        max_fem_attempts: int = 0,
        use_symmetry: bool = False,
    ) -> int:
        """Entfernt bis zu batch_size Knoten auf Basis einer FEM-Lösung.

        Blattknoten (Grad ≤ 1) überspringen den Zusammenhangscheck,
        durchlaufen aber die Mechanismus-Prüfung. Alle anderen
        durchlaufen den vollen can_remove_node-Check.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird direkt verändert).
        u : npt.NDArray[np.float64]
            Verschiebungsvektor aus der FEM-Lösung.
        batch_size : int
            Maximale Anzahl zu entfernender Knoten.
        validate_fem : bool
            Wenn True, wird nach jeder Entfernung ein FEM-Solve durchgeführt.
            Schlägt dieser fehl, wird die Entfernung rückgängig gemacht.
        fast_mode : bool
            Wenn True, Artikulationspunkte statt voller Zusammenhangsprüfung.
        max_fem_attempts : int
            Max. FEM-Validierungen bei validate_fem (0 = unbegrenzt).
        use_symmetry : bool
            Wenn True, wird beim Entfernen eines Knotens auch der
            linkssymmetrische Spiegelknoten entfernt (falls möglich).

        Returns
        -------
        int
            Anzahl tatsächlich entfernter Knoten.
        """
        node_energies = TopologyOptimizer.compute_node_energies(structure, u)
        if not node_energies:
            return 0

        degree: dict[int, int] = {}
        for sp in structure.springs:
            if sp.active:
                degree[sp.node_a.id] = degree.get(sp.node_a.id, 0) + 1
                degree[sp.node_b.id] = degree.get(sp.node_b.id, 0) + 1

        protected: set[int] = set()
        if fast_mode:
            import networkx as nx
            G = nx.Graph()
            G.add_nodes_from(n.id for n in structure.nodes if n.active)
            G.add_edges_from(
                (sp.node_a.id, sp.node_b.id)
                for sp in structure.springs if sp.active
            )
            protected = set(nx.articulation_points(G))

        sorted_nodes = sorted(node_energies.items(), key=lambda x: x[1])
        removed = 0
        fem_attempts = 0
        processed: set[int] = set()

        for node_id, _ in sorted_nodes:
            if removed >= batch_size:
                break
            if node_id in processed:
                continue

            if fast_mode:
                if node_id in protected:
                    continue
                can_remove = StructureValidator.neighbors_stable_after_removal(
                    structure, node_id,
                )
            elif degree.get(node_id, 0) <= 1:
                can_remove = StructureValidator.neighbors_stable_after_removal(
                    structure, node_id,
                )
            else:
                can_remove = StructureValidator.can_remove_node(structure, node_id)

            if not can_remove:
                continue

            # Spiegelknoten für Symmetrie bestimmen
            mirror_id: int | None = None
            if use_symmetry:
                x = node_id % structure.width
                y = node_id // structure.width
                m_id = y * structure.width + (structure.width - 1 - x)
                if m_id != node_id and m_id not in processed and structure.nodes[m_id].active:
                    mn = structure.nodes[m_id]
                    if not mn.fix_x and not mn.fix_y and mn.force_x == 0 and mn.force_y == 0:
                        mirror_id = m_id

            structure.remove_node(node_id)
            processed.add(node_id)

            if mirror_id is not None:
                m_deg = degree.get(mirror_id, 0)
                if fast_mode:
                    m_can = mirror_id not in protected and StructureValidator.neighbors_stable_after_removal(structure, mirror_id)
                elif m_deg <= 1:
                    m_can = StructureValidator.neighbors_stable_after_removal(structure, mirror_id)
                else:
                    m_can = StructureValidator.can_remove_node(structure, mirror_id)
                if m_can:
                    structure.remove_node(mirror_id)
                    processed.add(mirror_id)
                else:
                    mirror_id = None

            if validate_fem:
                fem_attempts += 1
                if solve_structure(structure) is None:
                    TopologyOptimizer._restore_node(structure, node_id)
                    processed.discard(node_id)
                    if mirror_id is not None:
                        TopologyOptimizer._restore_node(structure, mirror_id)
                        processed.discard(mirror_id)
                    if 0 < max_fem_attempts <= fem_attempts:
                        break
                    continue

            removed += 1
            if mirror_id is not None:
                removed += 1

        return removed

    @staticmethod
    def _adaptive_batch_size(
        progress: float,
        n_active: int,
    ) -> int:
        """Berechnet die Batch-Größe abhängig vom Fortschritt.

        Parameters
        ----------
        progress : float
            Fortschritt der Optimierung (0.0 = Start, 1.0 = Ziel erreicht).
        n_active : int
            Aktuell aktive Knoten.

        Returns
        -------
        int
            Anzahl Knoten die in diesem Schritt entfernt werden.
        """
        if progress < 0.30:
            frac = 0.02
        elif progress < 0.60:
            frac = 0.01
        elif progress < 0.85:
            frac = 0.002
        else:
            frac = 0.0

        if frac > 0.0:
            return max(1, int(n_active * frac))
        return 1

    @staticmethod
    def run(
        structure: Structure,
        mass_fraction: float,
        on_progress: Callable[[float, int, int], None] | None = None,
        stress_ratio_limit: float | None = None,
        fast_mode: bool = False,
        use_symmetry: bool = False,
    ) -> list[float]:
        """Führt die Optimierung durch bis der Massenanteil erreicht ist.

        Verwendet adaptive Batch-Größen: am Anfang werden mehr Knoten
        pro FEM-Solve entfernt, gegen Ende wird einzeln entfernt
        für maximale Genauigkeit.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird direkt verändert).
        mass_fraction : float
            Anteil der Knoten die übrig bleiben sollen, z.B. 0.5 = 50%.
        on_progress : Callable[[float, int, int], None] | None
            Optionaler Callback(fortschritt, aktive_knoten, ziel_knoten).
        stress_ratio_limit : float | None
            Maximales Verhältnis σ_max / σ_ref. None = keine Begrenzung.

        Returns
        -------
        list[float]
            Gesamtenergie nach jedem FEM-Solve.
        """
        assert 0.0 < mass_fraction < 1.0, "mass_fraction muss zwischen 0 und 1 liegen."

        total_nodes = len(structure.nodes)
        target_nodes = max(2, int(total_nodes * mass_fraction))
        nodes_to_remove = total_nodes - target_nodes

        energy_history: list[float] = []

        stress_ref: float | None = None
        if stress_ratio_limit is not None:
            u_ref = solve_structure(structure)
            if u_ref is not None:
                ref_stresses = TopologyOptimizer.compute_spring_stresses(structure, u_ref)
                stress_ref = max(ref_stresses.values()) if ref_stresses else None

        if on_progress:
            on_progress(0.0, total_nodes, target_nodes)

        consecutive_failures = 0
        snapshot = None
        snapshot_u = None
        max_reported_progress = 0.0
        min_reported_active = total_nodes

        while structure.active_node_count() > target_nodes:
            u = solve_structure(structure)

            if u is None:
                if snapshot is None:
                    break
                TopologyOptimizer._restore_snapshot(structure, snapshot)
                if fast_mode:
                    halved = TopologyOptimizer._halving_fallback(
                        structure, snapshot_u,
                        n_active - target_nodes, fast_mode=True,
                    )
                    snapshot = None
                    if halved == 0:
                        break
                    n_active = structure.active_node_count()
                    removed_so_far = total_nodes - n_active
                    progress = min(removed_so_far / nodes_to_remove, 1.0) if nodes_to_remove > 0 else 1.0
                    if on_progress:
                        max_reported_progress = max(max_reported_progress, progress)
                        min_reported_active = min(min_reported_active, n_active)
                        on_progress(max_reported_progress, min_reported_active, target_nodes)
                    continue
                removed = TopologyOptimizer.optimization_batch(
                    structure, snapshot_u, batch_size=1, validate_fem=True,
                    use_symmetry=use_symmetry,
                )
                snapshot = None
                if removed == 0:
                    break
                n_active = structure.active_node_count()
                removed_so_far = total_nodes - n_active
                progress = min(removed_so_far / nodes_to_remove, 1.0) if nodes_to_remove > 0 else 1.0
                if on_progress:
                    max_reported_progress = max(max_reported_progress, progress)
                    min_reported_active = min(min_reported_active, n_active)
                    on_progress(max_reported_progress, min_reported_active, target_nodes)
                continue

            if stress_ref is not None and stress_ratio_limit is not None:
                cur_stresses = TopologyOptimizer.compute_spring_stresses(structure, u)
                if cur_stresses:
                    stress_max = max(cur_stresses.values())
                    if stress_max / stress_ref > stress_ratio_limit:
                        break

            spring_energies = TopologyOptimizer.compute_spring_energies(structure, u)
            energy_history.append(sum(spring_energies.values()))

            n_active = structure.active_node_count()
            removed_so_far = total_nodes - n_active
            progress = min(removed_so_far / nodes_to_remove, 1.0) if nodes_to_remove > 0 else 1.0

            if fast_mode:
                if progress < 0.50:
                    frac = 0.03
                elif progress < 0.80:
                    frac = 0.015
                else:
                    frac = 0.005
                batch_size = min(30, max(1, int(n_active * frac)))
            else:
                batch_size = TopologyOptimizer._adaptive_batch_size(progress, n_active)
            batch_size = min(batch_size, n_active - target_nodes)

            snapshot = TopologyOptimizer._take_snapshot(structure)
            snapshot_u = u

            removed = TopologyOptimizer.optimization_batch(
                structure, u, batch_size, fast_mode=fast_mode,
                use_symmetry=use_symmetry,
            )
            if removed == 0:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    break
                continue

            consecutive_failures = 0
            TopologyOptimizer._cleanup_dangling(structure)
            n_active = structure.active_node_count()
            removed_so_far = total_nodes - n_active
            progress = min(removed_so_far / nodes_to_remove, 1.0) if nodes_to_remove > 0 else 1.0
            if on_progress:
                max_reported_progress = max(max_reported_progress, progress)
                min_reported_active = min(min_reported_active, n_active)
                on_progress(max_reported_progress, min_reported_active, target_nodes)

        if snapshot is not None and solve_structure(structure) is None:
            TopologyOptimizer._restore_snapshot(structure, snapshot)

        TopologyOptimizer._cleanup_dangling(structure)

        return energy_history

    @staticmethod
    def _halving_fallback(
        structure: Structure,
        u: npt.NDArray[np.float64],
        remaining: int,
        fast_mode: bool = False,
    ) -> int:
        """Halbiert die Batch-Größe bis eine Entfernung FEM-stabil ist.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird direkt verändert).
        u : npt.NDArray[np.float64]
            Verschiebungsvektor.
        remaining : int
            Verbleibende zu entfernende Knoten.
        fast_mode : bool
            Ob schnelle Prüfungen verwendet werden sollen.

        Returns
        -------
        int
            Anzahl entfernter Knoten, oder 0 bei Misserfolg.
        """
        batch_size = min(20, remaining)
        snapshot = TopologyOptimizer._take_snapshot(structure)

        for _ in range(6):
            removed = TopologyOptimizer.optimization_batch(
                structure, u, batch_size, fast_mode=fast_mode,
            )
            if removed > 0 and solve_structure(structure) is not None:
                return removed
            TopologyOptimizer._restore_snapshot(structure, snapshot)
            batch_size = max(1, batch_size // 2)

        return 0

    @staticmethod
    def _cleanup_dangling(structure: Structure) -> int:
        """Entfernt iterativ alle Blattknoten (Grad ≤ 1) die keine Lager oder Kräfte tragen.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird direkt verändert).

        Returns
        -------
        int
            Anzahl entfernter Knoten.
        """
        total_removed = 0
        changed = True
        while changed:
            changed = False
            degree: dict[int, int] = {}
            for sp in structure.springs:
                if sp.active:
                    degree[sp.node_a.id] = degree.get(sp.node_a.id, 0) + 1
                    degree[sp.node_b.id] = degree.get(sp.node_b.id, 0) + 1

            for node in structure.nodes:
                if not node.active:
                    continue
                if node.fix_x or node.fix_y:
                    continue
                if node.force_x != 0 or node.force_y != 0:
                    continue
                if degree.get(node.id, 0) <= 1:
                    structure.remove_node(node.id)
                    total_removed += 1
                    changed = True

        return total_removed

    @staticmethod
    def run_fast(
        structure: Structure,
        mass_fraction: float,
        on_progress: Callable[[float, int, int], None] | None = None,
        stress_ratio_limit: float | None = None,
        use_symmetry: bool = False,
    ) -> list[float]:
        """Schnelle Optimierung mit größeren Batches und leichterer Validierung.

        Verwendet Artikulationspunkt-Check statt voller Zusammenhangsprüfung
        und größere Batch-Größen für weniger FEM-Solves.

        Parameters
        ----------
        structure : Structure
            Die Struktur (wird direkt verändert).
        mass_fraction : float
            Anteil der Knoten die übrig bleiben sollen.
        on_progress : Callable[[float, int, int], None] | None
            Optionaler Callback(fortschritt, aktive_knoten, ziel_knoten).
        stress_ratio_limit : float | None
            Maximales Verhältnis σ_max / σ_ref. None = keine Begrenzung.

        Returns
        -------
        list[float]
            Gesamtenergie nach jedem FEM-Solve.
        """
        return TopologyOptimizer.run(
            structure, mass_fraction, on_progress, stress_ratio_limit,
            fast_mode=True, use_symmetry=use_symmetry,
        )


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
