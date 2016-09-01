import numpy as np
import scipy
from difflocal import diff_local, norm
#from control.matlab import lyap
from scipy.linalg import solve_sylvester

# https://docs.scipy.org/doc/numpy-dev/user/numpy-for-matlab-users.html
# http://stackoverflow.com/a/1001716
def mrdivide(a, b):
    # Problem: C = A/B
    #       -> CB = A
    # If B is square:
    #       -> C = A*inv(B)
    # Otherwise:
    #       -> C*(B*B') = A*B'
    #       -> C = A*B'*inv(B*B')
    A = np.asmatrix(a)
    B = np.asmatrix(b)
    dims = B.shape
    if dims[0] == dims[1]:
        return A * B.I
    else:
        return (A * B.T) * (B * B.T).I


def mldivide(a, b):
    dimensions = a.shape
    if dimensions[0] == dimensions[1]:
        return scipy.linalg.solve(a, b)
    else:
        return scipy.linalg.lstsq(a, b)[0]


def g2s(x, y, zx, zy, N=3):
    """
    % Purpose : Computes the Global Least Squares reconstruction of a surface
    %   from its gradient field.
    %
    % Use (syntax):
    %   Z = g2s( Zx, Zy, x, y )
    %   Z = g2s( Zx, Zy, x, y, N )
    %
    % Input Parameters :
    %   Zx, Zy := Components of the discrete gradient field
    %   x, y := support vectors of nodes of the domain of the gradient
    %   N := number of points for derivative formulas (default=3)
    %
    % Return Parameters :
    %   Z := The reconstructed surface
    %
    % Description and algorithms:
    %   The algorithm solves the normal equations of the Least Squares cost
    %   function, formulated by matrix algebra:
    %   e(Z) = || D_y * Z - Zy ||_F^2 + || Z * Dx' - Zx ||_F^2
    %   The normal equations are a rank deficient Sylvester equation which is
    %   solved by means of Householder reflections and the Bartels-Stewart
    %   algorithm.
    """

    if zx.shape != zy.shape:
        raise ValueError("Gradient components must be the same size")

    if np.asmatrix(zx).shape[1] != len(x) or np.asmatrix(zx).shape[0] != len(y):
        raise ValueError("Support vectors must have the same size as the gradient")

    m, n = zx.shape

    dx = diff_local(x, N, N)
    dy = diff_local(y, N, N)

    z = g2sSylvester(dy, dx, zy, zx, np.ones((m,1)), np.ones((n,1)))
    return z


def g2sSylvester(A, B, F, G, u, v):
    """
    % Purpose : Solves the semi-definite Sylvester Equation of the form
    %   A'*A * Phi + Phi * B'*B - A'*F - G*B = 0,
    %   Where the null vectors of A and B are known to be
    %   A * u = 0
    %   B * v = 0
    %
    % Use (syntax):
    %   Phi = g2sSylvester( A, B, F, G, u, v )
    %
    % Input Parameters :
    %   A, B, F, G := Coefficient matrices of the Sylvester Equation
    %   u, v := Respective null vectors of A and B
    %
    % Return Parameters :
    %   Phi := The minimal norm solution to the Sylvester Equation
    %
    % Description and algorithms:
    %   The rank deficient Sylvester equation is solved by means of Householder
    %   reflections and the Bartels-Stewart algorithm.  It uses the MATLAB
    %   function "lyap", in reference to Lyapunov Equations, a special case of
    %   the Sylvester Equation.
    """

    # Household vectors (???)
    m, n = len(u), len(v)

    u[0] += norm(u)
    u *= np.sqrt(2) / norm(u)

    v[0] += norm(v)
    v *= np.sqrt(2) / norm(v)

    # Apply householder updates
    A -= np.dot(np.dot(A, u), u.T)
    B -= np.dot(np.dot(B, v), v.T)
    F -= np.dot(np.dot(F, v), v.T)
    G -= np.dot(u, (np.dot(u.T, G)))

    # Solve the system of equations
    phi = np.zeros((m, n))
    phi[0, 1:] = mrdivide(G[0, :], B[:, 1:].T)
    phi[1:, 0] = mldivide(A[:, 1:], F[:, 0].T)
    phi[1:, 1:] = solve_sylvester(np.dot(A[:, 1:].T, A[:, 1:]),
                                  np.dot(B[:, 1:].T, B[:, 1:]),
                                  -np.dot(-A[:, 1:].T, F[:, 1:]) + np.dot(G[1:, :], B[:, 1:]))

    # Invert the householder updates
    phi -= np.dot(u, (np.dot(u.T, phi)))
    phi -= np.dot(np.dot(phi, v), v.T)
    return phi
