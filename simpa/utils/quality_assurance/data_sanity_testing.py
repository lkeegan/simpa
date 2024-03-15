# SPDX-FileCopyrightText: 2021 Division of Intelligent Medical Systems, DKFZ
# SPDX-FileCopyrightText: 2021 Janek Groehl
# SPDX-License-Identifier: MIT

import numpy as np
import torch
import inspect
from typing import Union


def assert_equal_shapes(numpy_arrays: list):
    """
    This method takes a list of n-dimensional numpy arrays and raises an AssertionError if the sizes of all arrays do
    not match.

    :param numpy_arrays: a list of np.ndarray
    :raises AssertionError: if there is a mismatch between any of the volume dimensions.
    """

    if len(numpy_arrays) < 2:
        return

    shapes = np.asarray([np.shape(_arr) for _arr in numpy_arrays]).astype(float)
    mean = np.mean(shapes, axis=0)
    for i in range(len(shapes)):
        shapes[i, :] = shapes[i, :] - mean

    if not np.sum(np.abs(shapes)) <= 1e-5:
        raise AssertionError("The given volumes did not all have the same"
                             " dimensions. Please double check the simulation"
                             f" parameters. Called from {inspect.stack()[1].function}")


def assert_array_well_defined(array: Union[np.ndarray, torch.Tensor], assume_non_negativity: bool = False,
                              assume_positivity=False, array_name: str = None):
    """
    This method tests if all entries of the given array or tensor are well-defined (i.e. not np.inf, np.nan, or None).
    The method can be parametrised to be more strict.

    :param array: The input np.ndarray or torch.Tensor
    :param assume_non_negativity: bool (default: False). If true, all values must be greater than or equal to 0.
    :param assume_positivity: bool (default: False). If true, all values must be greater than 0.
    :param array_name: a string that gives more information in case of an error.
    :raises AssertionError: if there are any unexpected values in the given array.
    """

    error_message = None
    if isinstance(array, np.ndarray) and any(stride < 0 for stride in array.strides):
        # torch does not support tensors with negative strides so we need to make a copy of the array
        array_as_tensor = torch.as_tensor(array.copy())
    else:
        array_as_tensor = torch.as_tensor(array)
    if not torch.all(torch.isfinite(array_as_tensor)):
        error_message = "nan, inf or -inf"
    if assume_positivity and torch.any(array_as_tensor <= 0):
        error_message = "not positive"
    if assume_non_negativity and torch.any(array_as_tensor < 0):
        error_message = "negative"
    if error_message:
        if array_name is None:
            array_name = "'Not specified'"
        caller = inspect.stack()[1]
        stack_string = f" \n\tArray Name: {array_name} \n\tCaller: {caller.filename}" \
                       f" \n\tline: {caller.lineno} \n\tcode: {caller.code_context}"
        raise AssertionError(f"The given array contained values that were {error_message}."
                             f" Info: {stack_string}.")
