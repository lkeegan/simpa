# SPDX-FileCopyrightText: 2021 Division of Intelligent Medical Systems, DKFZ
# SPDX-FileCopyrightText: 2021 Janek Groehl
# SPDX-License-Identifier: MIT

import atexit
from line_profiler import LineProfiler

profile = LineProfiler()
atexit.register(profile.print_stats)
