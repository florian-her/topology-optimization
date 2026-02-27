import unittest
import numpy as np

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from model.structure import Structure
from solver.fem_solver import assemble_global_K, assemble_force_vector, get_fixed_dofs, solve_structure


class TestGlobalKAssembly(unittest.TestCase):
    """Testet die Assemblierung der globalen Steifigkeitsmatrix."""

    def setUp(self):
        # 2x2-Gitter (row-major):
        #   Node 0: (0,0)  DOFs [0,1]
        #   Node 1: (1,0)  DOFs [2,3]
        #   Node 2: (0,1)  DOFs [4,5]
        #   Node 3: (1,1)  DOFs [6,7]
        # 6 Federn: (0,1) horiz, (0,2) vert, (0,3) diag\, (1,3) vert, (1,2) diag/, (2,3) horiz
        self.s = Structure(2, 2)

    def test_shape(self):
        # Vorbedingung: 4 Knoten → 8 DOFs
        K_g = assemble_global_K(self.s)
        self.assertEqual(K_g.shape, (8, 8))

    def test_diagonal_values(self):
        # Hauptdiagonalelemente spiegeln die direkte Eigensteifigkeit des Freiheitsgrades wider (Superposition)
        # Jeder Eckknoten hat genau 1 horiz + 1 vert + 1 diag-Feder
        # Diagonalbeitrag: 1.0 (horiz/vert) + 1/(2*sqrt(2)) (diag) = 1.3536
        K_g = assemble_global_K(self.s)
        expected = 1.0 + 1.0 / (2.0 * np.sqrt(2.0))
        for i in range(8):
            self.assertTrue(
                np.isclose(K_g[i, i], expected, atol=1e-6),
                f"K_g[{i},{i}] = {K_g[i,i]:.6f}, erwartet {expected:.6f}"
            )

    def test_symmetry(self):
        # Verifikation des Satzes von Betti (Maxwellsche Reziprozität): 
        # Steifigkeitsmatrizen linear-elastischer, konservativer Systeme sind zwingend symmetrisch.
        # Nachbedingung: K_g muss symmetrisch sein
        K_g = assemble_global_K(self.s)
        self.assertTrue(np.allclose(K_g.toarray(), K_g.T.toarray()), "K_g ist nicht symmetrisch")

    def test_spring_count(self):
        # 2x2-Gitter: 2 horiz + 2 vert + 2 diag\ + 2 diag/ = ... wait
        # 1 Zelle → 4 Federn pro Zelle + Randfedern
        # Horizontal: 1 Zeile * 1 pro Zeile * 2 Zeilen = 2
        # Vertikal: 1 Spalte * 1 pro Spalte * 2 Spalten = 2 (wait, width=2, height=2)
        # Für width=2, height=2: horizontal = height*(width-1) = 2*1 = 2
        #                        vertikal  = width*(height-1) = 2*1 = 2
        #                        diagonal  = 2*(width-1)*(height-1) = 2*1*1 = 2
        # Gesamt = 6
        self.assertEqual(len(self.s.springs), 6)


class TestSolveCantilever2x2(unittest.TestCase):
    """Testet den FEM-Solver mit einem 2x2 Kragarm."""

    def setUp(self):
        # Testfall: Numerische Lösung eines wohlgestellten Randwertproblems (Kragträger/Cantilever)
        self.s = Structure(2, 2)
        # Kragarm: linke Knoten (0=(0,0) und 2=(0,1)) vollständig fixiert
        self.s.nodes[0].fix_x = 1
        self.s.nodes[0].fix_y = 1
        self.s.nodes[2].fix_x = 1
        self.s.nodes[2].fix_y = 1
        # Horizontale Kraft an Node 1 (1,0)
        self.s.nodes[1].force_x = 10.0

    def test_fixed_dofs_are_zero(self):
        # Einhaltung der Dirichlet-Randbedingungen (kinematische Zwangsbedingungen, Verschiebung u=0)
        # Vorbedingung: Lager korrekt gesetzt
        fixed = get_fixed_dofs(self.s)
        self.assertIn(0, fixed)  # node 0, x
        self.assertIn(1, fixed)  # node 0, y
        self.assertIn(4, fixed)  # node 2, x
        self.assertIn(5, fixed)  # node 2, y

        # Nachbedingung: fixierte DOFs sind 0
        u = solve_structure(self.s)
        self.assertIsNotNone(u)
        for d in fixed:
            self.assertAlmostEqual(u[d], 0.0, places=10,
                                   msg=f"u[{d}] = {u[d]:.2e} sollte 0 sein")

    def test_displacement_in_force_direction(self):
        # Prüfung auf physikalische Plausibilität (Positive Definitheit der Steifigkeitsmatrix):
        # Äußere Kraft leistet an der Struktur positive Verformungsarbeit (W = 1/2 * F^T * u > 0)
        # Kraft in x-Richtung an Node 1 → Verschiebung u[2] > 0
        u = solve_structure(self.s)
        self.assertIsNotNone(u)
        self.assertGreater(u[2], 0.0, "u[2] (Node 1, x) sollte positiv sein bei Fx=10")

    def test_force_vector(self):
        # Verifikation der korrekten Assemblierung des Neumann-Randvektors
        # Vorbedingung: Kraft nur an DOF 2 (node 1, x)
        F = assemble_force_vector(self.s)
        self.assertAlmostEqual(F[2], 10.0)
        # Alle anderen DOFs haben keine Kraft
        for i in [0, 1, 3, 4, 5, 6, 7]:
            self.assertAlmostEqual(F[i], 0.0, msg=f"F[{i}] sollte 0 sein")

    def test_solution_not_none(self):
        u = solve_structure(self.s)
        self.assertIsNotNone(u, "solve_structure darf nicht None zurückgeben")

    def test_solution_length(self):
        u = solve_structure(self.s)
        self.assertEqual(len(u), 8)


if __name__ == "__main__":
    unittest.main()