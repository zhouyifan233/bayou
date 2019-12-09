# -*- coding: utf-8 -*-
import numpy as np

from bayou.datastructures import Gaussian, GMM, GMMSequence
from bayou.models import LinearModel, ConstantVelocity
from bayou.expmax.skf import SKF


def test_em_skf_1():
    F = np.asarray([
        [1, 0, 1, 0],
        [0, 1, 0, 1],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])
    H = np.asanyarray([
        [1, 0, 0, 0],
        [0, 1, 0, 0]
    ])
    """ 
        
    """
    g1 = Gaussian(np.zeros([4, 1]), np.eye(4))
    g2 = Gaussian(np.zeros([4, 1]), np.eye(4))
    initial_gmm_state = GMM([g1, g2])

    # measurements = 5 * np.random.randn(200, 2, 1) + 1

    measurements = np.loadtxt(r'data/measurement1.csv', delimiter=',')
    measurements = np.expand_dims(measurements, axis=-1)

    gmmsequence = GMMSequence(measurements, initial_gmm_state)

    m1 = LinearModel(F, 10.0*np.eye(4), H, 10.0*np.eye(2))
    m2 = LinearModel(F, 8.0*np.eye(4), H, 8.0*np.eye(2))
    initial_models = [m1, m2]

    Z = np.ones([2, 2]) / 2

    dataset = [gmmsequence]

    new_models, Z, dataset, LL = SKF.EM(dataset, initial_models, Z,
                                        max_iters=100, threshold=0.00001, learn_H=True, learn_R=True,
                                        learn_A=True, learn_Q=True, learn_init_state=True, learn_Z=True,
                                        keep_Q_structure=False, diagonal_Q=False, wishart_prior=False)

    print(LL)
    print(Z)
    print(new_models[0].R)

    return new_models

def test_em_skf_2():
    F = np.asarray([
        [1, 0, 1, 0],
        [0, 1, 0, 1],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])
    H = np.asanyarray([
        [1, 0, 0, 0],
        [0, 1, 0, 0]
    ])

    g1 = Gaussian(np.zeros([4, 1]), 10*np.eye(4))
    g2 = Gaussian(np.zeros([2, 1]), 10*np.eye(2))
    initial_gmm_state = GMM([g1, g2])

    # measurements = 5 * np.random.randn(200, 2, 1) + 1

    measurements = np.loadtxt(r'data/measurements.csv', delimiter=',')
    measurements = np.expand_dims(measurements, axis=-1)

    gmmsequence = GMMSequence(measurements, initial_gmm_state)

    m1 = LinearModel(F, 1*np.eye(4), H, 1*np.eye(2))
    m2 = LinearModel(np.eye(2), 1*np.eye(2), np.eye(2), 1*np.eye(2))
    initial_models = [m1, m2]

    Z = np.ones([2, 2]) / 2

    dataset = [gmmsequence]

    new_models, Z, dataset, LL = SKF.EM(dataset, initial_models, Z,
                                        max_iters=100, threshold=0.0001, learn_H=True, learn_R=True,
                                        learn_A=True, learn_Q=True, learn_init_state=True, learn_Z=True,
                                        keep_Q_structure=False, diagonal_Q=False, wishart_prior=False)

    print(LL)
    print(Z)
    print(new_models[0].R)

    return new_models

new_models = test_em_skf_2()

