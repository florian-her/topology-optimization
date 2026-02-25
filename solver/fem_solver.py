import numpy as np
import numpy.typing as npt
import scipy.sparse
import scipy.sparse.linalg

from model.structure import Structure


def assemble_global_K(structure: Structure) -> scipy.sparse.csr_matrix:
    """Baut die globale Steifigkeitsmatrix als Sparse-Matrix zusammen.

    Parameters
    ----------
    structure : Structure
        Die Struktur.

    Returns
    -------
    scipy.sparse.csr_matrix
        Steifigkeitsmatrix K_g mit Größe (2*N, 2*N).
    """
    n_dof = len(structure.nodes) * 2
    rows, cols, vals = [], [], []

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
                rows.append(dr)
                cols.append(dc)
                vals.append(Ko[r, c])

    if not rows:
        return scipy.sparse.csr_matrix((n_dof, n_dof))

    return scipy.sparse.csr_matrix((vals, (rows, cols)), shape=(n_dof, n_dof))


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
    K: scipy.sparse.csr_matrix,
    F: npt.NDArray[np.float64],
    u_fixed_idx: list[int],
    eps: float = 1e-9,
) -> npt.NDArray[np.float64] | None:
    """Löst K*u = F auf dem reduzierten System (freie DOFs).

    Statt Zeilen/Spalten zu nullen wird das System auf die freien
    Freiheitsgrade reduziert und mit dem Sparse-Solver gelöst.
    Das ist äquivalent, aber deutlich effizienter für große Matrizen.

    Parameters
    ----------
    K : scipy.sparse.csr_matrix
        Steifigkeitsmatrix (wird nicht verändert).
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
    n = F.shape[0]
    fixed = np.array(sorted(set(u_fixed_idx)), dtype=int)
    free = np.setdiff1d(np.arange(n), fixed)

    if len(free) == 0:
        return np.zeros(n)

    K_ff = K[free, :][:, free]
    F_f = F[free]

    try:
        u_free = scipy.sparse.linalg.spsolve(K_ff, F_f)
        if not np.all(np.isfinite(u_free)):
            raise ValueError("spsolve returned NaN/inf")
        u = np.zeros(n)
        u[free] = u_free
        return u

    except Exception:
        try:
            K_reg = K_ff + scipy.sparse.eye(len(free), format="csr") * eps
            u_free = scipy.sparse.linalg.spsolve(K_reg, F_f)
            if not np.all(np.isfinite(u_free)):
                return None
            u = np.zeros(n)
            u[free] = u_free
            return u
        except Exception:
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

    if u is not None:
        for node in structure.nodes:
            node.u_x = float(u[2 * node.id])
            node.u_y = float(u[2 * node.id + 1])

    return u


if __name__ == "__main__":
    print("=" * 60)
    print("FEM Solver Test: 2x2 Gitter")
    print("=" * 60)

    from model.structure import Structure

    s = Structure(2, 2)
    print(f"{s}")

    K_g = assemble_global_K(s)
    print(f"\nGlobale Steifigkeitsmatrix K_g (8x8, sparse):")
    print(np.round(K_g.toarray(), 3))

    expected_diag = 1.0 + 1.0 / (2 * np.sqrt(2))
    print(f"\nErwarteter Diagonalwert: {expected_diag:.4f}")
    print(f"Diagonale von K_g: {np.round(K_g.diagonal(), 4)}")
    print(f"Symmetrisch: {np.allclose(K_g.toarray(), K_g.T.toarray())}")

    s.nodes[0].fix_x = 1
    s.nodes[0].fix_y = 1
    s.nodes[2].fix_x = 1
    s.nodes[2].fix_y = 1
    s.nodes[1].force_x = 10.0

    u = solve_structure(s)
    print(f"\nVerschiebungsvektor u: {np.round(u, 4)}")
