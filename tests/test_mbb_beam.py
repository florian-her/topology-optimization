import unittest
import numpy as np

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from model.structure import Structure
from solver.fem_solver import solve_structure
from optimizer.topology_optimizer import TopologyOptimizer
from optimizer.validators import StructureValidator


def _create_mbb_beam(width: int = 12, height: int = 4) -> Structure:
    """Erstellt einen MBB-Beam: links Festlager, rechts Loslager (y), Kraft oben Mitte."""
    s = Structure(width, height)

    for y in range(height):
        nid = y * width
        s.nodes[nid].fix_x = 1
        s.nodes[nid].fix_y = 1

    for y in range(height):
        nid = y * width + (width - 1)
        s.nodes[nid].fix_y = 1

    mid_top = width // 2
    s.nodes[mid_top].force_y = -1.0

    return s


class TestMBBBeamSetup(unittest.TestCase):
    """Testet die korrekte Einrichtung des MBB-Beams."""

    def setUp(self):
        self.s = _create_mbb_beam(12, 4)

    def test_dimensions(self):
        self.assertEqual(self.s.width, 12)
        self.assertEqual(self.s.height, 4)
        self.assertEqual(len(self.s.nodes), 48)

    def test_left_supports_fixed(self):
        for y in range(4):
            nid = y * 12
            self.assertEqual(self.s.nodes[nid].fix_x, 1)
            self.assertEqual(self.s.nodes[nid].fix_y, 1)

    def test_right_supports_roller(self):
        for y in range(4):
            nid = y * 12 + 11
            self.assertEqual(self.s.nodes[nid].fix_y, 1)
            self.assertEqual(self.s.nodes[nid].fix_x, 0)

    def test_force_applied(self):
        self.assertAlmostEqual(self.s.nodes[6].force_y, -1.0)

    def test_structure_connected(self):
        self.assertTrue(StructureValidator.is_connected(self.s))

    def test_load_paths_exist(self):
        self.assertTrue(StructureValidator.has_load_paths(self.s))


class TestMBBBeamFEM(unittest.TestCase):
    """Testet die FEM-Lösung des MBB-Beams."""

    def setUp(self):
        self.s = _create_mbb_beam(12, 4)
        self.u = solve_structure(self.s)

    def test_solution_exists(self):
        self.assertIsNotNone(self.u)

    def test_solution_length(self):
        self.assertEqual(len(self.u), 2 * len(self.s.nodes))

    def test_fixed_dofs_zero(self):
        for y in range(4):
            nid_left = y * 12
            self.assertAlmostEqual(self.u[2 * nid_left], 0.0, places=10)
            self.assertAlmostEqual(self.u[2 * nid_left + 1], 0.0, places=10)

            nid_right = y * 12 + 11
            self.assertAlmostEqual(self.u[2 * nid_right + 1], 0.0, places=10)

    def test_force_node_deflects(self):
        self.assertNotAlmostEqual(self.u[2 * 6 + 1], 0.0, places=6,
                                  msg="Kraftknoten muss sich verformen")

    def test_free_nodes_displace(self):
        mid_nodes = [y * 12 + 6 for y in range(4)]
        for nid in mid_nodes:
            ux = abs(self.u[2 * nid])
            uy = abs(self.u[2 * nid + 1])
            displacement = max(ux, uy)
            self.assertGreater(displacement, 0.0,
                               f"Knoten {nid} sollte sich verformen")


class TestMBBBeamOptimization(unittest.TestCase):
    """Testet die Topologieoptimierung des MBB-Beams."""

    def setUp(self):
        self.s = _create_mbb_beam(12, 4)
        self.total_nodes = len(self.s.nodes)

    def test_optimization_reduces_nodes(self):
        energy_history = TopologyOptimizer.run(self.s, mass_fraction=0.5)
        active = self.s.active_node_count()
        target = max(2, int(self.total_nodes * 0.5))
        self.assertLessEqual(active, target + 3)
        self.assertGreater(len(energy_history), 0)

    def test_structure_stays_connected(self):
        TopologyOptimizer.run(self.s, mass_fraction=0.5)
        self.assertTrue(StructureValidator.is_connected(self.s))

    def test_load_paths_preserved(self):
        TopologyOptimizer.run(self.s, mass_fraction=0.5)
        self.assertTrue(StructureValidator.has_load_paths(self.s))

    def test_supports_not_removed(self):
        TopologyOptimizer.run(self.s, mass_fraction=0.5)
        for y in range(4):
            nid_left = y * 12
            self.assertTrue(self.s.nodes[nid_left].active,
                            f"Festlager-Knoten {nid_left} wurde entfernt")

    def test_force_node_not_removed(self):
        TopologyOptimizer.run(self.s, mass_fraction=0.5)
        self.assertTrue(self.s.nodes[6].active, "Kraftknoten wurde entfernt")

    def test_optimized_structure_solvable(self):
        TopologyOptimizer.run(self.s, mass_fraction=0.5)
        u = solve_structure(self.s)
        self.assertIsNotNone(u, "Optimierte Struktur muss lösbar sein")


if __name__ == "__main__":
    unittest.main()
