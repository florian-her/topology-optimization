import numpy as np
import numpy.typing as npt
import networkx as nx

from model.structure import Structure


class StructureValidator:
    """Prüft ob die Struktur zusammenhängend bleibt und Lastpfade existieren."""

    @staticmethod
    def is_connected(structure: Structure) -> bool:
        """Prüft ob alle aktiven Knoten miteinander verbunden sind.

        Parameters
        ----------
        structure : Structure
            Die Struktur.

        Returns
        -------
        bool
            True wenn zusammenhängend.
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
        """Prüft ob jeder Kraftknoten ein Lager erreichen kann.

        Parameters
        ----------
        structure : Structure
            Die Struktur.

        Returns
        -------
        bool
            True wenn alle Kräfte zu einem Lager geleitet werden können.
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
    def neighbors_stable_after_removal(structure: Structure, node_id: int) -> bool:
        """Prüft ob nach Entfernen eines Knotens alle Nachbarn mechanisch stabil bleiben.

        Ein Knoten ist stabil wenn er mindestens 2 nicht-parallele Federn hat,
        sodass er in 2D voll abgestützt ist (kein Mechanismus).

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        node_id : int
            ID des Knotens der entfernt werden soll.

        Returns
        -------
        bool
            True wenn alle Nachbarn nach Entfernung stabil bleiben.
        """
        affected_spring_ids: set[int] = set()
        neighbors: set[int] = set()

        for sp in structure.springs:
            if not sp.active:
                continue
            if sp.node_a.id == node_id:
                affected_spring_ids.add(sp.id)
                neighbors.add(sp.node_b.id)
            elif sp.node_b.id == node_id:
                affected_spring_ids.add(sp.id)
                neighbors.add(sp.node_a.id)

        for nid in neighbors:
            node = structure.nodes[nid]
            if not node.active:
                continue
            if node.fix_x and node.fix_y:
                continue

            directions: list[npt.NDArray[np.float64]] = []
            for sp in structure.springs:
                if not sp.active or sp.id in affected_spring_ids:
                    continue
                if sp.node_a.id == nid or sp.node_b.id == nid:
                    directions.append(sp.get_direction_vector())

            if len(directions) < 2:
                return False

            ref = directions[0]
            all_parallel = all(
                abs(ref[0] * d[1] - ref[1] * d[0]) < 1e-6
                for d in directions[1:]
            )
            if all_parallel:
                return False

        return True

    @staticmethod
    def can_remove_node(structure: Structure, node_id: int) -> bool:
        """Prüft ob ein Knoten entfernt werden kann ohne die Struktur zu zerstören.

        Prüft drei Bedingungen:
        1. Graph bleibt zusammenhängend
        2. Lastpfade bleiben erhalten
        3. Keine Nachbarknoten werden zu Mechanismen (nur parallele Federn)

        Parameters
        ----------
        structure : Structure
            Die Struktur.
        node_id : int
            ID des Knotens.

        Returns
        -------
        bool
            True wenn Zusammenhang, Lastpfade und Stabilität erhalten bleiben.
        """
        node = structure.nodes[node_id]
        assert node.active, f"Knoten {node_id} ist bereits inaktiv."

        if not StructureValidator.neighbors_stable_after_removal(structure, node_id):
            return False

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
