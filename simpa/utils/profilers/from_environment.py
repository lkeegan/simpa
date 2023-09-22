# SPDX-FileCopyrightText: 2021 Division of Intelligent Medical Systems, DKFZ
# SPDX-FileCopyrightText: 2021 Janek Groehl
# SPDX-License-Identifier: MIT

import sys
import os

if "profile" in sys.modules:
    print("!!!!!!!!!!!!!!!!profile already imported")
    profile = sys.modules["profile"]
else:
    profile_type = os.getenv("SIMPA_PROFILE")
    if profile_type is None:
        from .null import profile
    elif profile_type == "TIME":
        from .time import profile
    elif profile_type == "MEMORY":
        from .memory import profile
    elif profile_type == "GPU_MEMORY":
        from .gpu_memory import profile
    else:
        raise RuntimeError("SIMPA_PROFILE env var is defined but invalid: valid values are TIME, MEMORY, or GPU_MEMORY")
