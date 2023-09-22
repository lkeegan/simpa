# SPDX-FileCopyrightText: 2021 Division of Intelligent Medical Systems, DKFZ
# SPDX-FileCopyrightText: 2021 Janek Groehl
# SPDX-License-Identifier: MIT

from pytorch_memlab import profile
from torch.cuda import memory_summary
import atexit


@atexit.register
def print_memory_summary():
    print(memory_summary())
