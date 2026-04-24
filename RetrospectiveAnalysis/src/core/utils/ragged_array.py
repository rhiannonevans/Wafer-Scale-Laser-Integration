from typing import Any

import numpy as np


class RaggedArray:
    def __init__(self, array: list[list[Any]]) -> None:
        self.__array = array
        self.__double_indices = np.array(
            [
                (row, col)
                for row, sublist in enumerate(array)
                for col, _ in enumerate(sublist)
            ]
        )

    def __getitem__(self, index: int | tuple[int, int]):
        if isinstance(index, int):
            row, col = self.get_double_index(index)
            return self.__array[row][col]
        elif isinstance(index, tuple):
            return self.__array[index[0]][index[1]]
        else:
            raise TypeError("Index must be int or tuple of ints")

    def get_double_index(self, index: int):
        return tuple(self.__double_indices[index])

    def get_single_index(self, row: int, col: int) -> int:
        return np.where(  # type: ignore
            (self.__double_indices[:, 0] == row) & (self.__double_indices[:, 1] == col)
        )[0][0]

    @property
    def array(self):
        return self.__array

    @property
    def double_indices(self):
        return self.__double_indices
