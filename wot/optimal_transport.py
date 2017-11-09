# -*- coding: utf-8 -*-

import numpy as np
import scipy.stats


def get_file_basename_and_extension(name):
    dot_index = name.rfind('.')
    ext = ''
    basename = name
    if dot_index != -1:
        ext = name[dot_index:]
        if ext == '.gz':
            return get_file_basename_and_extension(name[0:dot_index])

    if dot_index != -1:
        basename = name[0:dot_index]
    return {'basename': basename, 'ext': ext};


def transport_stable(p, q, C, lambda1, lambda2, epsilon, scaling_iter, g):
    """
    Compute the optimal transport with stabilized numerics.
    Args:
        p: uniform distribution on input cells
        q: uniform distribution on output cells
        C: cost matrix to transport cell i to cell j
        lambda1: regularization parameter for marginal constraint for p.
        lambda2: regularization parameter for marginal constraint for q.
        epsilon: entropy parameter
        scaling_iter: number of scaling iterations
        g: growth value for input cells
    """
    u = np.zeros(len(p))
    v = np.zeros(len(q))
    b = np.ones(len(q))
    p = p * g
    q = q * np.average(g)
    K0 = np.exp(-C / epsilon)
    K = np.copy(K0)
    alpha1 = lambda1 / (lambda1 + epsilon)
    alpha2 = lambda2 / (lambda2 + epsilon)
    for i in range(scaling_iter):
        # scaling iteration
        a = (p / (K.dot(b))) ** alpha1 * np.exp(-u / (lambda1 + epsilon))
        b = (q / (K.T.dot(a))) ** alpha2 * np.exp(-v / (lambda2 + epsilon))
        # stabilization
        if (max(max(abs(a)), max(abs(b))) > 1e100):
            u = u + epsilon * np.log(a)
            v = v + epsilon * np.log(b)  # absorb
            K = (K0.T * np.exp(u / epsilon)).T * np.exp(v / epsilon)
            a = np.ones(len(p))
            b = np.ones(len(q))
    return (K.T * a).T * b


def optimal_transport(cost_matrix, growth_rate, p=None, q=None,
                      growth_ratio=2.5, delta_days=1, epsilon=0.1, lambda1=1.,
                      lambda2=1., min_transport_fraction=0.05,
                      max_transport_fraction=0.4, min_growth_fit=0.9,
                      l0_max=100, scaling_iter=250):
    """
    Compute the optimal transport.

    Args:
        cost_matrix (ndarray): A 2D matrix that indicates the cost of
        transporting cell i to cell j.
                               Can be generated by
                               sklearn.metrics.pairwise.pairwise_distances
                               for example.
        growth_rate (ndarray): A 1D matrix that indicates the growth rate of
        cells.
        growth_ratio (float): Over 1 day, a cell in the more proliferative
        group is expected to produce growth_ratio
                              times as many offspring as a cell in the
                              non-proliferative group
        delta_days (float): Elapsed time in days between time points
        epsilon (float): Controls the entropy of the transport map. An
        extremely large entropy parameter will give a
                         maximally entropic transport map, and an extremely
                         small entropy parameter will give a nearly
                         deterministic transport map (but could also lead to
                         numerical instability in the algorithm)
        lambda1 (float): Regularization parameter that controls the fidelity
        of the constraints on p.
                        As lamda1 gets larger, the constraints become more
                        stringent
        lambda2 (float): Regularization parameter that controls the fidelity
        of the constraints on q.
                        As lamda2 gets larger, the constraints become more
                        stringent
        min_transport_fraction (float): The minimum fraction of cells at time
        t that are transported to time t + 1.
        max_transport_fraction (float): The maximum fraction of cells at time
        t that are transported to time t + 1.
        min_growth_fit (float):
        l0_max (float):
        scaling_iter (int): Number of scaling iterations

    Returns:
        ndarray: A dictionary with transport (the transport map), epsilon,
        lambda1, and lambda2
    """

    if p is None:
        p = np.ones(cost_matrix.shape[0]) / cost_matrix.shape[0]
    if q is None:
        q = np.ones(cost_matrix.shape[1]) / cost_matrix.shape[1]
    lb = 0.5
    ub = lb * growth_ratio
    inflection = 0.22
    scale = 10

    g = (ub - lb) / (1 + np.exp(-scale * (growth_rate - inflection))) + lb
    g = g ** delta_days
    l0 = 1.
    e0 = 1.
    while True:
        transport = transport_stable(p, q, cost_matrix, lambda1 * l0,
                                     lambda2 * l0, epsilon * e0, scaling_iter,
                                     g)
        avg_transport = np.average(
            [np.exp(scipy.stats.entropy(trans)) for trans in transport])
        growth_fit = 1 - np.linalg.norm(
            transport.sum(1) - g / cost_matrix.shape[0]) ** 2 / np.linalg.norm(
            g / cost_matrix.shape[0]) ** 2
        if avg_transport == 0:
            while avg_transport == 0:
                e0 *= 1.1
                transport = transport_stable(p, q, cost_matrix, lambda1 * l0,
                                             lambda2 * l0, epsilon * e0,
                                             scaling_iter, g)
                avg_transport = np.average(
                    [np.exp(scipy.stats.entropy(trans)) for trans in transport])
            break
        elif (growth_fit < min_growth_fit) and (l0 < l0_max):
            l0 *= 1.5
        elif avg_transport < transport.shape[1] * min_transport_fraction:
            e0 *= 1.1
        elif avg_transport < transport.shape[1] * max_transport_fraction:
            break
        else:
            e0 /= 1.1
    return {'transport': transport, 'lambda1': lambda1 * l0,
            'lambda2': lambda2 * l0, 'epsilon': epsilon * e0}
