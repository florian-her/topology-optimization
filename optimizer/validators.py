import networkx as nx

from model.structure import Structure


class StructureValidator:
    """Prüft strukturelle Integrität: Zusammenhang und Lastpfad."""

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
    def can_remove_spring(structure: Structure, spring_id: int) -> bool:
        """Prüft ob eine Feder entfernt werden kann ohne den Zusammenhang zu brechen.

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        spring_id : int
            ID der zu prüfenden Feder.

        Returns
        -------
        bool
            True wenn das Entfernen den Zusammenhang erhält, False sonst.
        """
        # Feder temporär deaktivieren
        spring = next((s for s in structure.springs if s.id == spring_id), None)
        assert spring is not None, f"Feder mit ID {spring_id} nicht gefunden."
        assert spring.active, f"Feder {spring_id} ist bereits inaktiv."

        spring.active = False
        connected = StructureValidator.is_connected(structure)
        spring.active = True

        return connected


if __name__ == "__main__":
    from model.structure import Structure

    s = Structure(3, 3)
    print(f"Zusammenhängend: {StructureValidator.is_connected(s)}")
    print(f"Feder 0 entfernbar: {StructureValidator.can_remove_spring(s, 0)}")
