import warnings
import numpy as np
from numpy.linalg import matrix_rank

def norm(x):
    return np.sqrt(np.sum(x**2))

def dop(m, n=None):
    """
    Generate a set of discrete orthonormal polynomials and their derivatives.

    Parameters
    ----------
    m : array or int
        If an integer, the number of evenly spaced points in the support. If a vector,
        the (arbitrarily spaced) points in the support.

    n : int
        The number of basis functions (i.e. the order of the polynomial). Default is
        the size of `m`.

    Returns
    -------
    P : m x n array
        The discrete polynomials

    dP : m x n array
        The derivatives

    rC : tuple
        (alpha,beta) coefficients for the three term recurrence relationship
    

    Notes
    -----
    Directly transcribed from MATLAB code: DOPbox v1.0:
    Cite this as :
    
        @article{DBLP:journals/tim/OLearyH12,
         author    = {Paul O'Leary and
                      Matthew Harker},
         title     = {A Framework for the Evaluation of Inclinometer Data in the
                      Measurement of Structures},
         journal   = {IEEE T. Instrumentation and Measurement},
         volume    = {61},
         number    = {5},
         year      = {2012},
         pages     = {1237-1251},
        }

        @inproceedings{
        olearyHarker2008B,
          Author = {O'Leary, Paul and Harker, Matthew},
          Title = {An Algebraic Framework for Discrete Basis Functions in Computer Vision},
          BookTitle = {IEEE Indian Conference on Computer Vision, Graphics and Image Processing},
          Address= {Bhubaneswar, Dec},
          Year = {2008} }

        Author : Matthew Harker
        Date : Nov. 29, 2011
        Version : 1.0
        --------------------------------------------------------------------------
        (c) 2011, Harker, O'Leary, University of Leoben, Leoben, Austria
        email: automation@unileoben.ac.at, url: automation.unileoben.ac.at
        --------------------------------------------------------------------------
    """
    u = len(m)

    if u == 1:
        x = np.arange(-1, 2 / (m - 1))
    else:
        x = m
        m = len(x)

    if n is None:
        n = m

    # ==============================
    # Generate the Basis
    # ==============================
    # Generate the first two polynomials :
    p0 = np.ones(m) / np.sqrt(m)
    meanX = np.mean(x)
    p1 = x - meanX
    np1 = norm(p1)
    p1 /= np1

    # Compute the derivatives of the degree-1 polynomial :
    hm = np.sum(np.diff(x))
    h = np.sum(np.diff(p1))
    dp1 = (h / hm) * np.ones(m)

    # Initialize the basis function matrices :
    P = np.zeros((m, n))
    P[:, 0] = p0
    P[:, 1] = p1

    dP = np.zeros((m, n))
    dP[:, 1] = dp1

    # Setup storage for the coefficients of the three term relationship
    alphas = np.zeros(n)
    alphas[0] = 1 / np.sqrt(m)
    alphas[1] = 1 / np1

    betas = np.zeros(n)
    betas[1] = meanX

    for k in range(2, n):
        # Augment previous polynomial :
        pt = P[:, k - 1] * p1

        # 3-term recurrence
        beta0 = np.dot(P[:, k - 2],pt)
        pt -= P[:, k - 2] * beta0
        betas[2] = beta0

        # Complete reorthogonalization :
        beta = np.dot(P[:, :k].T, pt)
        pt -= np.dot(P[:, :k],beta)

        # Apply coefficients to recurrence formulas :
        alpha = 1 / np.sqrt(np.dot(pt,pt))
        alphas[k] = alpha
        P[:, k] = np.dot(alpha,pt)
        dP[:, k] = alpha * (dP[:, k - 1] * p1 + P[:, k - 1] * dp1 - dP[:, k - 2] * beta0 - np.dot(dP[:, :k],beta))

    recurrenceCoeffs = (alphas, betas)
    return P, dP, recurrenceCoeffs


def diff_local(x, ls, noBfs):
    """
    Generates a global matrix operator which implements the computation of local differentials.

    Parameters
    ----------
    x : 1d-array
        A vector of co-ordinates at which to evaluate the differentials.
        Can be irregularly spaced.

    ls : int
        Support length. Should be an odd number. There is an exception up to ls = 20 and ls = noPoints.
        In this case a full differentiating matrix is computed.

    noBfs : int
        Number of basis functions to use.


    Returns
    -------
    S : square array
        The local differential matrix, each dimension is len(x).

    Notes
    -----
    Local discrete orthogonal polynomials are used to generate the local approximations for the dreivatives.
    Transcribed from MATLAB code: DOPbox: dopDiffLocal.m, v1.0:

        Author :  Matthew Harker and Paul O'Leary
        Date :    17. January 2012
        Version : 1.0

        (c) 2013 Matthew Harker and Paul O'Leary,
        Chair of Automation, University of Leoben, Leoben, Austria
        email: office@harkeroleary.org,
        url: www.harkeroleary.org
    """

    # -----------------------------------------
    noPts = len(x)

    # ----------------------------------------------------------------
    # Test the input paramaters
    # ----------------------------------------------------------------
    # if option != "full":
    #     genSparse = True
    # else:
    #     genSparse = False

    # if mt > 1:
    #     raise ValueError('A column vector is expected for x')

    # Test the degree and support length for campatability
    if noBfs > ls:
        raise ValueError('The number of basis functions must be <= ls')

    if ls > 13:
        warnings.warn('With a support length greater than 13 there may be problems with the Runge phenomena.')

    # ----------------------------------------------------------------
    # Compute a full matrix
    # ----------------------------------------------------------------
    if ls == noPts:
        Gt, dGt, _ = dop(x, noBfs)
        S = np.dot(dGt, Gt.T)
        rS = matrix_rank(S)
        if rS < noPts - 1:
            warnings.warn('The rank of S is ' + str(rS) + ' while x has n = ' + str(noPts) + ' points.')
        return S

    # Test if the support length is compatible with the number of points requested.
    if noPts < ls:
        raise ValueError('The number of nodes n must be greater that the support length ls')

    if ls % 2 == 0:
        raise ValueError('this function is only implemented for odd values of ls.')

    # ------------------------------------------------------------------------
    vals = np.zeros((noPts, noPts))  # I think?

    # Determine the half length of ls this determine the upper ane lower positions of Si.
    ls2 = np.round((ls + 1) / 2)

    # generate the top of Si
    Gt, dGt, _ = dop(x[np.arange(ls)], noBfs)
    Dt = np.dot(dGt, Gt.T)
    vals[:ls2, :ls] = Dt[:ls2, :]

    # Compute the strip diagonal entries
    noOnDiag = noPts - 2 * ls2
    for k in range(noOnDiag):
        Gt, dGt, _ = dop(x[range(k+1, k + ls+1)], noBfs)
        tdGt = dGt[ls2-1, :]
        dt = np.dot(tdGt, Gt.T)
        vals[k + ls2,k+1:k+1+ls] = dt

    # generate the bottom part of Si
    Gt, dGt, _ = dop(x[-ls:], noBfs)
    Dt = np.dot(dGt, Gt.T)
    vals[-ls2:, -ls:] = Dt[-ls2:, :]

    rS = matrix_rank(vals);

    if rS < noPts - 1:
        warnings.warn('The rank of S is ' + str(rS) + ' while x has n = ' + str(noPts) + ' points.')

    return vals
