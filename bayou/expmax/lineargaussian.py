# -*- coding: utf-8 -*-
import copy

import numpy as np
from scipy import linalg

from bayou.expmax.base import EM
from bayou.datastructures import Gaussian
from bayou.filters.lineargaussian import Kalman
from bayou.smoothers.lineargaussian import RTS
from bayou.utils.util import Utility


class LinearGaussian(EM):
    """ """

    @staticmethod
    def e_step(sequence, model):
        sequence = Kalman.filter_sequence(sequence, model)
        sequence = RTS.smooth_sequence(sequence, model)
        return sequence

    @staticmethod
    def m_step(dataset, model, initial_model,
               learn_H, learn_R, learn_A, learn_Q, learn_init_state,
               keep_Q_structure, diagonal_Q):

        N = len(dataset)

        data_cardinality = 0
        for n in range(N):
            data_cardinality += dataset[n].len

        H_terms = [0, 0]  # term_0 @ inv(term_1)
        R_terms = [0, 0, 0]  # 1/term_0 * (term_1 - H @ term_2)
        A_terms = [0, 0]  # term_0 @ inv(term_1)
        Q_terms = [0, 0, 0]  # 1/term_0 * (term_1 - A @ term_2)

        # M-Step
        for n in range(N):
            sequence = dataset[n]
            smoothed_x = np.array([state.mean for state in sequence.smoothed])
            smoothed_V = np.array([state.covar for state in sequence.smoothed])
            smooth_VVs = sequence.smooth_crossvar

            if learn_H or learn_R:
                term_0 = 0
                term_1 = 0
                for t in range(0, sequence.len):
                    term_0 += sequence.measurements[t] @ smoothed_x[t].T
                    term_1 += smoothed_V[t] + smoothed_x[t] @ smoothed_x[t].T
                H_terms[0] += term_0
                H_terms[1] += term_1

            if learn_R:
                term_0 = 0
                term_1 = 0
                term_2 = 0
                for t in range(0, sequence.len):
                    term_1 += sequence.measurements[t] @ sequence.measurements[t].T
                    term_2 += smoothed_x[t] @ sequence.measurements[t].T
                term_0 += sequence.len
                R_terms[0] += term_0
                R_terms[1] += term_1
                R_terms[2] += term_2

            if learn_A or learn_Q:
                term_0 = 0
                term_1 = 0
                for t in range(1, sequence.len):
                    term_0 += smooth_VVs[t] + smoothed_x[t] @ smoothed_x[t - 1].T
                    term_1 += smoothed_V[t - 1] + smoothed_x[t - 1] @ smoothed_x[t - 1].T
                A_terms[0] += term_0
                A_terms[1] += term_1

            if learn_Q:
                term_0 = 0
                term_1 = 0
                term_2 = 0
                for t in range(1, sequence.len):
                    term_1 += smoothed_V[t] + smoothed_x[t] @ smoothed_x[t].T
                    term_2 += smooth_VVs[t] + smoothed_x[t - 1] @ smoothed_x[t].T
                term_0 += sequence.len - 1
                Q_terms[0] += term_0
                Q_terms[1] += term_1
                Q_terms[2] += term_2

            if learn_init_state:
                initial_x = smoothed_x[0]
                initial_V = smoothed_V[0]
                sequence.initial_state = Gaussian(initial_x, initial_V)

        old_H = model.H
        old_R = model.R
        old_A = model.A
        old_Q = model.Q

        # Update Model
        if learn_H:
            new_H = H_terms[0] @ linalg.inv(H_terms[1])
            model.H = new_H

        if learn_R:
            new_R = (R_terms[1] - 2 * old_H @ R_terms[2] + old_H @ H_terms[1] @ old_H.T) / R_terms[0]
            model.R = new_R

        if learn_A:
            new_A = A_terms[0] @ linalg.inv(A_terms[1])
            model.A = new_A

        if learn_Q:
            numerator = Q_terms[1] - old_A @ Q_terms[2] - A_terms[0] @ old_A.T + old_A @ A_terms[1] @ old_A.T
            denominator = Q_terms[0]

            if keep_Q_structure:
                structure = initial_model.get_Q_structure()
                inv_struct = linalg.inv(structure)
                q = np.trace(inv_struct @ numerator) / denominator
                new_Q = structure * q
            else:
                new_Q = numerator / denominator

            if diagonal_Q:
                new_Q = np.diag(np.diag(new_Q))
            model.Q = new_Q

        return model

    @staticmethod
    def EM(dataset, initial_model, max_iters=20, threshold=0.0001,
           learn_H=True, learn_R=True, learn_A=True, learn_Q=True, learn_init_state=True,
           keep_Q_structure=False, diagonal_Q=False):
        """ Expectation-Maximization for a Linear Gaussian State-Space model.

        Parameters
        ----------
        dataset : list of GaussianSequence objects
            N iid sequences

        Returns
        -------
        LinearModel : LinearModel object
        dataset : list of sequences
        LLs : list of log likelihoods at each iteration
        """

        N = len(dataset)
        model = copy.deepcopy(initial_model)
        LLs = []

        for i in range(max_iters):

            # E-Step
            for n in range(N):
                dataset[n] = LinearGaussian.e_step(dataset[n], model)

            # Check convergence
            sequence_LLs = [np.sum(sequence.loglikelihood) for sequence in dataset]
            LLs.append(np.sum(sequence_LLs))
            if len(LLs) > 1:
                if Utility.check_lik_convergence(LLs[-1], LLs[-2], threshold):
                    print('iterations:', i)
                    return model, dataset, LLs

            # M-Step
            model = LinearGaussian.m_step(dataset, model, initial_model,
                                          learn_H, learn_R,
                                          learn_A, learn_Q, learn_init_state,
                                          keep_Q_structure, diagonal_Q)
            
            print("Estimated F: ")
            print(model.A)
            print("Estimated Q: ")
            print(model.Q)
            print("Estimated H: ")
            print(model.H)
            print("Estimated R: ")
            print(model.R)
            print("iteration %d ... LL %.5f" % (i, np.sum(sequence_LLs)))
            print("-----------------------------------------------------------------------")

        print('Converged. Iterations:', i)
        return model, dataset, LLs