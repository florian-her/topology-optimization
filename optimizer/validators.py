import networkx as nx

from model.structure import Structure


class StructureValidator:
    """Prüft strukturelle Integrität: Zusammenhang und Lastpfad."""

    @staticmethod
    def is_connected(structure: Structure) -> bool:
        """Prüft ob alle aktiven Knoten zusammenhängend sind.

        Parameters
        ----------
        structure : Structure
            Die zu prüfende Struktur.

        Returns
        -------
        bool
            True wenn alle aktiven Knoten verbunden sind, False sonst.
        """
        active_ids = [n.id for n in structure.nodes if n.active]
        if len(active_ids) <= 1:
            return True

        G = nx.Graph()
        G.add_nodes_from(active_ids)
        G.add_edges_from(
            (s.node_a.id, s.node_b.id)
            for s in structure.springs
            if s.active
        )
        return nx.is_connected(G)

    @staticmethod
    def has_load_paths(structure: Structure) -> bool:
        """Prüft ob jeder aktive Kraftknoten einen Pfad zu einem aktiven Lagerknoten hat.

        Parameters
        ----------
        structure : Structure
            Die zu prüfende Struktur.

        Returns
        -------
        bool
            True wenn alle Lastpfade vorhanden sind, False sonst.
        """
        G = nx.Graph()
        G.add_nodes_from(n.id for n in structure.nodes if n.active)
        G.add_edges_from(
            (s.node_a.id, s.node_b.id)
            for s in structure.springs
            if s.active
        )

        support_ids = {
            n.id for n in structure.nodes
            if n.active and (n.fix_x or n.fix_y)
        }

        if not support_ids:
            return False

        for node in structure.nodes:
            if not node.active:
                continue
            if node.force_x != 0 or node.force_y != 0:
                if not any(nx.has_path(G, node.id, s_id) for s_id in support_ids):
                    return False

        return True

    @staticmethod
    def can_remove_node(structure: Structure, node_id: int) -> bool:
        """Prüft ob ein Knoten entfernt werden kann.

        Kriterien:
        1. Graph bleibt zusammenhängend (nur aktive Knoten/Federn)
        2. Alle Lastpfade bleiben erhalten

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        node_id : int
            ID des zu prüfenden Knotens.

        Returns
        -------
        bool
            True wenn beide Kriterien erfüllt sind, False sonst.
        """
        node = structure.nodes[node_id]
        assert node.active, f"Knoten {node_id} ist bereits inaktiv."

        node.active = False
        affected_springs = []
        for spring in structure.springs:
            if spring.active and (spring.node_a.id == node_id or spring.node_b.id == node_id):
                spring.active = False
                affected_springs.append(spring)

        connected = StructureValidator.is_connected(structure)
        load_paths_ok = StructureValidator.has_load_paths(structure) if connected else False

        node.active = True
        for spring in affected_springs:
            spring.active = True

        return connected and load_paths_ok


if __name__ == "__main__":
    from model.structure import Structure

    s = Structure(3, 3)
    print(f"Zusammenhängend: {StructureValidator.is_connected(s)}")
    print(f"Lastpfade OK: {StructureValidator.has_load_paths(s)}")

    s.nodes[0].fix_x = 1
    s.nodes[0].fix_y = 1
    s.nodes[2].force_y = -1.0
    print(f"Knoten 4 entfernbar: {StructureValidator.can_remove_node(s, 4)}")
