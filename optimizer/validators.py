import numpy as np
import networkx as nx

from model.structure import Structure


class StructureValidator:
    """Prüft strukturelle Integrität: Zusammenhang und mechanische Stabilität."""

    @staticmethod
    def is_connected(structure: Structure) -> bool:
        """Prüft ob die Struktur (aktive Federn) zusammenhängend ist.

        Parameters
        ----------
        structure : Structure
            Die zu prüfende Struktur.

        Returns
        -------
        bool
            True wenn alle Knoten verbunden sind, False sonst.
        """
        G = nx.Graph()
        G.add_nodes_from(node.id for node in structure.nodes)
        G.add_edges_from(
            (s.node_a.id, s.node_b.id)
            for s in structure.springs
            if s.active
        )
        return nx.is_connected(G)

    @staticmethod
    def is_mechanically_stable(
        structure: Structure,
        cond_threshold: float = 1e10,
    ) -> bool:
        """Prüft ob die Steifigkeitsmatrix (mit Randbedingungen) gut konditioniert ist.

        Graph-Zusammenhang allein reicht nicht: Eine Struktur kann verbunden aber
        trotzdem ein Mechanismus sein (singuläre K-Matrix). Diese Methode prüft
        ob cond(K) unter dem Schwellenwert bleibt.

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        cond_threshold : float, optional
            Maximale erlaubte Konditionszahl, by default 1e10.

        Returns
        -------
        bool
            True wenn K gut konditioniert ist, False bei Mechanismus/Singularität.
        """
        from solver.fem_solver import assemble_global_K, get_fixed_dofs

        fixed = get_fixed_dofs(structure)
        if not fixed:
            return False

        K = assemble_global_K(structure)

        # Dirichlet-RB anwenden
        for d in fixed:
            K[d, :] = 0.0
            K[:, d] = 0.0
            K[d, d] = 1.0

        try:
            cond = np.linalg.cond(K)
            return float(cond) < cond_threshold
        except np.linalg.LinAlgError:
            return False

    @staticmethod
    def can_remove_spring(structure: Structure, spring_id: int) -> bool:
        """Prüft ob eine Feder entfernt werden kann.

        Zwei Kriterien müssen erfüllt sein:
        1. Graph bleibt zusammenhängend (schnelle Prüfung zuerst)
        2. K-Matrix bleibt gut konditioniert (kein Mechanismus)

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        spring_id : int
            ID der zu prüfenden Feder.

        Returns
        -------
        bool
            True wenn beide Kriterien erfüllt sind, False sonst.
        """
        spring = next((s for s in structure.springs if s.id == spring_id), None)
        assert spring is not None, f"Feder mit ID {spring_id} nicht gefunden."
        assert spring.active, f"Feder {spring_id} ist bereits inaktiv."

        spring.active = False

        # 1. Schnelle Prüfung: Zusammenhang
        connected = StructureValidator.is_connected(structure)

        # 2. Nur wenn verbunden: mechanische Stabilität (K-Kondition)
        stable = StructureValidator.is_mechanically_stable(structure) if connected else False

        spring.active = True

        return connected and stable


if __name__ == "__main__":
    from model.structure import Structure

    s = Structure(3, 3)
    print(f"Zusammenhängend: {StructureValidator.is_connected(s)}")
    print(f"Feder 0 entfernbar: {StructureValidator.can_remove_spring(s, 0)}")
