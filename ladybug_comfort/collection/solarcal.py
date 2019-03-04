# coding=utf-8
"""Object for calculating SolarCal MRT from DataCollections."""
from __future__ import division

from ..solarcal import outdoor_sky_heat_exch, indoor_sky_heat_exch, \
    shortwave_from_horiz_solar, sharp_from_solar_and_body_azimuth
from ..parameter.solarcal import SolarCalParameter
from ._base import ComfortDataCollection

from ladybug._datacollectionbase import BaseCollection

from ladybug.datatype.temperature import Temperature, MeanRadiantTemperature
from ladybug.datatype.temperaturedelta import RadiantTemperatureDelta
from ladybug.datatype.energyflux import Irradiance, EffectiveRadiantField, \
    HorizontalInfraredRadiationIntensity
from ladybug.datatype.energyintensity import Radiation


class OutdoorSolarCal(ComfortDataCollection):
    """SolarCal DataCollection object.

    Properties:
        location
        surface_temperatures
        horizontal_infrared
        diffuse_horizontal_solar
        direct_normal_solar
        solarcal_body_parameter
        sky_exposure
        fraction_body_exposed
        floor_reflectance

        shortwave_effective_radiant_field
        longwave_effective_radiant_field
        shortwave_mrt_delta
        longwave_mrt_delta
        mrt_delta
        mean_radiant_temperature
    """
    _model = 'Outdoor SolarCal'

    def __init__(self, location, surface_temperatures, horizontal_infrared,
                 diffuse_horizontal_solar, direct_normal_solar,
                 solarcal_body_parameter=None, sky_exposure=None,
                 fraction_body_exposed=None, floor_reflectance=None):
        """Perform a full outdoor sky radiant heat exchange using Data Collections.

        Args:
            location: A Ladybug Location object.
            surface_temperatures: Data Collection with the temperature of surfaces
                around the person in degrees Celcius. This includes the ground and
                any other surfaces blocking the view to the sky. Typically, outdoor
                dry bulb temperature is used when such surface temperatures are unknown.
            horizontal_infrared: Data Collection with the horizontal infrared radiation
                intensity from the sky in W/m2.
            diff_horiz_solar: Data Collection with the diffuse horizontal solar
                irradiance in W/m2.
            dir_normal_solar: Data Collection with the direct normal solar
                irradiance in W/m2.
            solarcal_body_parameter: Optional SolarCalParameter object to account for
                properties of the human geometry.
            sky_exposure: A number between 0 and 1 representing the fraction of the
                sky vault in occupant’s view. Default is 1 for outdoors in an
                open field.
            fract_exposed: A number between 0 and 1 representing the fraction of
                the body exposed to direct sunlight. Note that this does not include the
                body’s self-shading; only the shading from surroundings.
                Default is 1 for a person standing in an open area.
            floor_reflectance: A number between 0 and 1 the represents the
                reflectance of the floor. Default is for 0.25 which is characteristic
                of outdoor grass or dry bare soil.
        """
        pass
