import numpy as np
import numpy.typing as npt

from model.structure import Structure


def assemble_global_K(structure: Structure) -> npt.NDArray[np.float64]:
    """Baut die globale Steifigkeitsmatrix aus allen aktiven Federn zusammen.

    Parameters
    ----------
    structure : Structure
        Die Struktur.

    Returns
    -------
    npt.NDArray[np.float64]
        Steifigkeitsmatrix K_g mit Größe (2*N, 2*N).
    """
    n_dof = len(structure.nodes) * 2
    K_g = np.zeros((n_dof, n_dof))

    for spring in structure.springs:
        if not spring.active:
            continue

        i = spring.node_a.id
        j = spring.node_b.id
        dofs = [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]

        E_factor = structure.material.E / 210.0
        Ko = spring.get_stiffness_matrix() * E_factor

        for r, dr in enumerate(dofs):
            for c, dc in enumerate(dofs):
                K_g[dr, dc] += Ko[r, c]

    return K_g


def assemble_force_vector(structure: Structure) -> npt.NDArray[np.float64]:
    """Baut den Kraftvektor aus den Knotenkräften zusammen.

    Parameters
    ----------
    structure : Structure
        Die Struktur.

    Returns
    -------
    npt.NDArray[np.float64]
        Kraftvektor F der Länge 2*N.
    """
    n_dof = len(structure.nodes) * 2
    F = np.zeros(n_dof)

    for node in structure.nodes:
        F[2 * node.id] = node.force_x
        F[2 * node.id + 1] = -node.force_y

    return F


def get_fixed_dofs(structure: Structure) -> list[int]:
    """Sammelt die Indizes aller fixierten Freiheitsgrade.

    Parameters
    ----------
    structure : Structure
        Die Struktur.

    Returns
    -------
    list[int]
        Indizes der fixierten DOFs.
    """
    fixed = []
    for node in structure.nodes:
        if not node.active:
            fixed.append(2 * node.id)
            fixed.append(2 * node.id + 1)
        else:
            if node.fix_x:
                fixed.append(2 * node.id)
            if node.fix_y:
                fixed.append(2 * node.id + 1)
    return fixed


def solve(
    K: npt.NDArray[np.float64],
    F: npt.NDArray[np.float64],
    u_fixed_idx: list[int],
    eps: float = 1e-9,
) -> npt.NDArray[np.float64] | None:
    """Löst K*u = F mit fixierten Freiheitsgraden.

    Parameters
    ----------
    K : npt.NDArray[np.float64]
        Steifigkeitsmatrix (wird verändert).
    F : npt.NDArray[np.float64]
        Kraftvektor.
    u_fixed_idx : list[int]
        Fixierte Freiheitsgrade (u=0).
    eps : float, optional
        Regularisierung bei singulärer Matrix.

    Returns
    -------
    npt.NDArray[np.float64] | None
        Verschiebungsvektor u, oder None bei Fehler.
    """
    assert K.shape[0] == K.shape[1], "Steifigkeitsmatrix K muss quadratisch sein."
    assert K.shape[0] == F.shape[0], "Kraftvektor F muss dieselbe Größe wie K haben."

    # Dirichlet-Randbedingungen: Zeile/Spalte nullen, Diagonale auf 1
    for d in u_fixed_idx:
        K[d, :] = 0.0
        K[:, d] = 0.0
        K[d, d] = 1.0

    try:
        u = np.linalg.solve(K, F)
        u[u_fixed_idx] = 0.0
        return u

    except np.linalg.LinAlgError:
        K += np.eye(K.shape[0]) * eps
        try:
            u = np.linalg.solve(K, F)
            u[u_fixed_idx] = 0.0
            return u
        except np.linalg.LinAlgError:
            return None


def solve_structure(structure: Structure) -> npt.NDArray[np.float64] | None:
    """Löst die FEM-Analyse für die Struktur und speichert Verschiebungen in den Knoten.

    Parameters
    ----------
    structure : Structure
        Die Struktur mit Lagern und Kräften.

    Returns
    -------
    npt.NDArray[np.float64] | None
        Verschiebungsvektor u, oder None bei Fehler.
    """
    K_g = assemble_global_K(structure)
    F = assemble_force_vector(structure)
    fixed_dofs = get_fixed_dofs(structure)

    assert len(fixed_dofs) > 0, "Keine Lager definiert — Struktur ist nicht gelagert."

    u = solve(K_g, F, fixed_dofs)

    # Verschiebungen in Knoten zurückschreiben (für Verformungsplot)
    if u is not None:
        for node in structure.nodes:
            node.u_x = float(u[2 * node.id])
            node.u_y = float(u[2 * node.id + 1])

    return u


if __name__ == "__main__":
    from model.node import Node
    from model.spring import Spring

    print("=" * 60)
    print("FEM Solver Test: 2x2 Gitter")
    print("=" * 60)

    from model.structure import Structure

    # 2x2-Gitter: Node 0=(0,0), 1=(1,0), 2=(0,1), 3=(1,1)
    s = Structure(2, 2)
    print(f"{s}")

    K_g = assemble_global_K(s)
    print(f"\nGlobale Steifigkeitsmatrix K_g (8x8):")
    print(np.round(K_g, 3))

    expected_diag = 1.0 + 1.0 / (2 * np.sqrt(2))
    print(f"\nErwarteter Diagonalwert: {expected_diag:.4f}")
    print(f"Diagonale von K_g: {np.round(np.diag(K_g), 4)}")
    print(f"Symmetrisch: {np.allclose(K_g, K_g.T)}")

    # Kragarm: linke Knoten (0 und 2) fixiert, Kraft rechts an Node 1
    s.nodes[0].fix_x = 1
    s.nodes[0].fix_y = 1
    s.nodes[2].fix_x = 1
    s.nodes[2].fix_y = 1
    s.nodes[1].force_x = 10.0

    u = solve_structure(s)
    print(f"\nVerschiebungsvektor u: {np.round(u, 4)}")
    print(f"u[0..3] (node 0, fix): {np.round(u[:4], 4)}")
