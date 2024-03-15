# SPDX-FileCopyrightText: 2021 Division of Intelligent Medical Systems, DKFZ
# SPDX-FileCopyrightText: 2021 Janek Groehl
# SPDX-License-Identifier: MIT

import numpy as np
import pmcx
from simpa.utils import Tags, Settings
from simpa.core.simulation_modules.optical_simulation_module import OpticalForwardModuleBase
from simpa.core.device_digital_twins.illumination_geometries.illumination_geometry_base import IlluminationGeometryBase
from typing import Dict, Tuple


class MCXAdapter(OpticalForwardModuleBase):
    """
    This class implements a bridge to the mcx framework using pmcx to integrate mcx into SIMPA.
    This adapter only allows for computation of fluence, for computations of diffuse reflectance,
    take a look at `simpa.ReflectanceMcxAdapter`

    .. note::
        MCX is a GPU-enabled Monte-Carlo model simulation of photon transport in tissue:
        Fang, Qianqian, and David A. Boas. "Monte Carlo simulation of photon migration in 3D
        turbid media accelerated by graphics processing units."
        Optics express 17.22 (2009): 20178-20190.

    """

    def __init__(self, global_settings: Settings):
        """
        initializes MCX-specific configuration and clean-up instances

        :param global_settings: global settings used during simulations
        """
        super(MCXAdapter, self).__init__(global_settings=global_settings)
        self.frames = None

    def forward_model(self,
                      absorption_cm: np.ndarray,
                      scattering_cm: np.ndarray,
                      anisotropy: np.ndarray,
                      refractive_index: np.ndarray,
                      illumination_geometry: IlluminationGeometryBase) -> Dict:
        """
        runs the MCX simulations.
        The set of flags parsed to MCX is built based on the Tags declared in `self.component_settings`, the results
        from MCX are used to populate an instance of Dict and returned.

        :param absorption_cm: array containing the absorption of the tissue in `cm` units
        :param scattering_cm: array containing the scattering of the tissue in `cm` units
        :param anisotropy: array containing the anisotropy of the volume defined by `absorption_cm` and `scattering_cm`
        :param refractive_index: array containing the refractive index of the volume defined by `absorption_cm` and `scattering_cm`
        :param illumination_geometry: and instance of `IlluminationGeometryBase` defining the illumination geometry
        :return: `Dict` containing the results of optical simulations, the keys in this dictionary-like object
            depend on the Tags defined in `self.component_settings`
        """
        config = self.get_mcx_config(illumination_geometry=illumination_geometry,
                                     absorption_cm=absorption_cm,
                                     scattering_cm=scattering_cm,
                                     anisotropy=anisotropy,
                                     refractive_index=refractive_index)

        pmcx_results = pmcx.run(config)

        return self.parse_pmcx_results(pmcx_results)

    def parse_pmcx_results(self, pmcx_results: Dict) -> Dict:
        fluence = pmcx_results["flux"]
        fluence *= 100  # Convert from J/mm^2 to J/cm^2
        if np.shape(fluence)[3] == 1:
            fluence = np.squeeze(fluence, 3)
        fluence = self.post_process_volumes(**{'arrays': (fluence,)})[0]
        results = dict()
        results[Tags.DATA_FIELD_FLUENCE] = fluence
        return results

    def get_mcx_config(self,
                       illumination_geometry: IlluminationGeometryBase,
                       absorption_cm: np.ndarray,
                       scattering_cm: np.ndarray,
                       anisotropy: np.ndarray,
                       refractive_index: np.ndarray,
                       **kwargs) -> Dict:
        """
        generates a pcmx config for simulations based on Tags in `self.global_settings` and
        `self.component_settings`. Among others, it defines the volume array.

        :param illumination_geometry: and instance of `IlluminationGeometryBase` defining the illumination geometry
        :param absorption_cm: Absorption in units of per centimeter
        :param scattering_cm: Scattering in units of per centimeter
        :param anisotropy: Dimensionless scattering anisotropy
        :param assumed_anisotropy:
        :param kwargs: dummy, used for class inheritance
        :return: dictionary with settings to be used by MCX
        """
        absorption_mm, scattering_mm, anisotropy, refractive_index = self.pre_process_volumes(**{'absorption_cm': absorption_cm,
                                                                                                 'scattering_cm': scattering_cm,
                                                                                                 'anisotropy': anisotropy,
                                                                                                 'refractive_index': refractive_index})
        # stack arrays to give array with shape (nx,ny,nz,4) - where the 4 floats correspond to mua/mus/g/n
        vol = np.stack([absorption_mm, scattering_mm, anisotropy, refractive_index], dtype=np.float32)
        [_, self.nx, self.ny, self.nz] = np.shape(vol)
        source = illumination_geometry.get_mcx_illuminator_definition(self.global_settings)
        prop = np.array([[0, 0, 1, 1]], dtype=np.float32)
        if Tags.TIME_STEP and Tags.TOTAL_TIME in self.component_settings:
            dt = self.component_settings[Tags.TIME_STEP]
            time = self.component_settings[Tags.TOTAL_TIME]
        else:
            time = 5e-09
            dt = 5e-09
        self.frames = int(time / dt)
        config = {
            "nphoton": self.component_settings[Tags.OPTICAL_MODEL_NUMBER_PHOTONS],
            "vol": vol,
            "tstart": 0,
            "tend": time,
            "tstep": dt,
            "prop": prop,
            "unitinmm": self.global_settings[Tags.SPACING_MM],
            "srctype": source["Type"],
            "srcpos": source["Pos"],
            "srcdir": source["Dir"],
            "srcparam1": source["Param1"],
            "srcparam2": source["Param2"],
            "isreflect": 1,
            "autopilot": 1,
            "outputtype": "fluence",
        }

        if Tags.MCX_SEED not in self.component_settings:
            if Tags.RANDOM_SEED in self.global_settings:
                config["seed"] = self.global_settings[Tags.RANDOM_SEED]
        else:
            config["seed"] = self.component_settings[Tags.MCX_SEED]

        return config

    def pre_process_volumes(self, **kwargs) -> Tuple:
        """
        pre-process volumes before running simulations with MCX. The volumes are transformed to `mm` units

        :param kwargs: dictionary containing at least the keys `scattering_cm, absorption_cm, anisotropy, refractive_index` and
            `assumed_anisotropy`
        :return: `Tuple` of volumes after transformation
        """
        return self.volumes_to_mm(**kwargs)

    @staticmethod
    def volumes_to_mm(**kwargs) -> Tuple:
        """
        transforms volumes into `mm` units

        :param kwargs: dictionary containing at least the keys `scattering_cm, absorption_cm, anisotropy, refractive_index` and
            `assumed_anisotropy`
        :return: `Tuple` of volumes after transformation
        """
        scattering_cm = kwargs.get('scattering_cm')
        absorption_cm = kwargs.get('absorption_cm')
        anisotropy = kwargs.get('anisotropy')
        refractive_index = kwargs.get('refractive_index')
        absorption_mm = absorption_cm / 10
        scattering_mm = scattering_cm / 10
        return absorption_mm, scattering_mm, anisotropy, refractive_index

    @staticmethod
    def post_process_volumes(**kwargs) -> Tuple:
        """
        post-processes volumes after MCX simulations. Dummy function implemented for compatibility with inherited
        classes

        :param kwargs: dictionary containing at least the key `volumes` to be transformed
        :return:
        """
        arrays = kwargs.get('arrays')
        return tuple(a for a in arrays)
