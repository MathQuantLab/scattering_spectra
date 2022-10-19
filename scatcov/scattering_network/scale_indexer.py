""" A class that implements the scale paths used in the scattering transform. """
from typing import *
from itertools import product, chain
from collections import OrderedDict
from functools import cmp_to_key
import numpy as np
import torch
import pandas as pd


""" Notations
- sc_path or path: a scale path, tuple (j1, j2, ... jr)
- sc_idx or idx: paths are numbered by their scale path
- J: number of octaves
- Q1: number of wavelets per octave on first wavelet layer
- Q2: number of wavelets per octave on second wavelet layer
"""


class ScatteringShape:
    def __init__(self,
                 N: int,
                 n_scales: int,
                 A: int,
                 T: int) -> None:
        self.N = N
        self.n_scales = n_scales
        self.A = A
        self.T = T


class ScaleIndexer:
    """ Implements the scale paths used in the scattering transform. """
    def __init__(self,
                 J: int,
                 Qs: List[int],
                 r_max: int) -> None:
        self.J, self.Qs, self.r_max = J, Qs, r_max

        self.sc_paths = self.create_sc_paths()  # list[order] array
        self.p_coding, self.p_decoding = self.construct_path_coding_dicts()
        self.sc_idces = self.create_sc_idces()  # # list[order] array

        self.low_pass_mask = self.compute_low_pass_mask()  # list[order] array

        self.checks()

    def checks(self):
        """ Check if the construction is broken. """
        # path and idx are in same order
        argsort = np.argsort(np.array(list(self.p_coding.values())))
        paths = list(self.p_coding.keys())
        def compare(t1, t2): return (len(t1) == len(t2) and t1 < t2) or (len(t1) < len(t2))  # order on tuples
        assert sorted(paths, key=cmp_to_key(compare)) == [paths[i] for i in argsort]

        if all([Q == 1 for Q in self.Qs]):
            for r in ([2] if self.r_max >= 2 else []):
                # when p_idx[r] is collapsed we obtain p_idx[r-1] without low_pass
                collapsed = np.unique(self.sc_paths[r - 1][:, :-1], axis=0)
                previous_order = self.sc_paths[r - 2][~self.low_pass_mask[r - 2], :]
                assert np.all(collapsed == previous_order)

    def JQ(self, r: int) -> int:
        """ Return the number of wavelet at a certain order. """
        return self.J * self.Qs[r-1]

    def condition(self, path: List[int]) -> bool:
        """ Tells if path j1, j2 ... j{r-1} jr is admissible. """
        return (len(path) <= self.r_max) and \
               all(i // self.Qs[order] < j // self.Qs[order+1] for order, (i, j) in enumerate(zip(path[:-1], path[1:])))

    def create_sc_paths(self) -> List[np.ndarray]:
        """ The tables j1, j2 ... j{r-1} jr for every order r. """
        sc_paths_l = []
        for r in range(1, self.r_max + 1):
            sc_paths_r = np.array([p for p in product(*[range(self.JQ(o+1)+1) for o in range(r)]) if self.condition(p)])
            sc_paths_l.append(sc_paths_r)
        return sc_paths_l

    def create_sc_idces(self) -> List[np.ndarray]:
        """ The scale idces numerating scale paths. """
        sc_idces_l = []
        for r in range(1, self.r_max + 1):
            sc_idces_r = np.array([self.path_to_idx(p) for p in self.sc_paths[r-1]])
            sc_idces_l.append(sc_idces_r)
        return sc_idces_l

    def construct_path_coding_dicts(self) -> Tuple[Dict[Tuple, int], Dict[int, Tuple]]:
        """ Construct the enumeration idx -> path. """
        coding = OrderedDict({(): 0})
        coding = OrderedDict(coding, **{tuple(path): i for i, path in enumerate(list(chain.from_iterable(self.sc_paths)))})
        decoding = OrderedDict({v: k for k, v in coding.items()})

        return coding, decoding

    def get_all_paths(self) -> List[Tuple]:
        return list(self.p_coding.keys())

    def get_all_idces(self) -> List[int]:
        return list(self.p_decoding.keys())

    def path_to_idx(self, path: Union[Tuple, List, np.ndarray]) -> int:
        """ Return scale index i corresponding to path. """
        path = np.array(path)
        if len(path) > 0 and path[-1] == -1:
            i0 = np.argmax(path == -1)
            path = path[:i0]
        return self.p_coding[tuple(path)]

    def idx_to_path(self, idx: int, squeeze: Optional[bool] = True) -> Tuple[int]:
        """ Return scale path j1, j2 ... j{r-1} jr corresponding to scale index i. """
        if idx == -1:
            return tuple()
        if squeeze:
            return self.p_decoding[idx]
        return self.p_decoding[idx] + (pd.NA, ) * (self.r_max - len(self.p_decoding[idx]))

    def is_low_pass(self, idx: int) -> bool:
        """ Determines if the path indexed by idx is ending with a low-pass. """
        return self.idx_to_path(idx)[-1] >= self.JQ(self.r(idx))

    def r(self, idx: int) -> int:
        """ The scattering order of the path indexed by idx. """
        return len(self.idx_to_path(idx))

    def compute_low_pass_mask(self) -> List[torch.Tensor]:
        """ Compute the low pass mask telling at each order which are the paths ending with a low pass filter. """
        return [torch.LongTensor(paths[:, -1]) == self.JQ(order+1)
                for order, paths in enumerate(self.sc_paths[:3])]
