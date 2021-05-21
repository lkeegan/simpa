# The MIT License (MIT)
#
# Copyright (c) 2021 Computer Assisted Medical Interventions Group, DKFZ
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated simpa_documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# First load everything without internal dependencies
from .tags import Tags
from .libraries.literature_values import MorphologicalTissueProperties
from .libraries.literature_values import StandardProperties
from .libraries.literature_values import OpticalTissueProperties
from .constants import SaveFilePaths, SegmentationClasses

# Then load classes and methods with an <b>increasing</b> amount of internal dependencies.
# If there are import errors in the tests, it is probably due to an incorrect
# initialization order
from .libraries.spectra_library import AbsorptionSpectrumLibrary
from .libraries.spectra_library import Spectrum
from .libraries.spectra_library import SPECTRAL_LIBRARY
from .libraries.spectra_library import view_absorption_spectra

from .libraries.molecule_library import Molecule
from .libraries.molecule_library import MoleculeLibrary
from .libraries.molecule_library import MOLECULE_LIBRARY

from .libraries.tissue_library import TissueLibrary
from .libraries.tissue_library import TISSUE_LIBRARY
from .libraries.tissue_library import MolecularCompositionGenerator

from .calculate import calculate_oxygenation
from .calculate import calculate_gruneisen_parameter_from_temperature
from .calculate import randomize_uniform

from .deformation_manager import create_deformation_settings
from .deformation_manager import get_functional_from_deformation_settings

from .settings import Settings

from .dict_path_manager import generate_dict_path

from .constants import EPS

from .path_manager import PathManager

if __name__ == "__main__":
    view_absorption_spectra()
