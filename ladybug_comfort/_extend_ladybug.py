# coding=utf-8
"""Collection of methods that extends current objects in ladybug core library.

This module is imported in __init__.py and applies the changes on runtime.
"""

from ladybug.epw import EPW

from .collection.utci import UTCI
from .collection.pmv import PMV
from .collection.solarcal import OutdoorSolarCal


def get_universal_thermal_climate_index(self, include_wind=False, include_sun=False,
                                        comfort_parameter=None):
    """Get a UTCI comfort object from the conditions within the EPW file.

    Args:
        include_wind: Set to True to include the epw wind speed in the calculation.
            Default is False assuming a condition that is shielded from wind.
        include_sun: Set to True to include the mean radiant temperature (MRT) delta
            from both shortwave solar falling directly on people and long wave radiant
            exchange with the sky. Default is False assuming a shaded condition.
            Note that, when set to True, this calculation will assume no surrounding
            context, standing human geometry, and a solar horizontal angle relative to
            front of person (SHARP) of 135 degrees. A SHARP of 135 essentially assumes
            that a person typically faces their side or back to the sun to avoid glare.
        comfort_parameter: Optional UTCIParameter object to specify parameters under
            which conditions are considered acceptable. If None, default will
            assume comfort thresholds consistent with those used by meterologists
            to categorize outdoor conditions.

    Returns:
        utci_obj: An object with data collections of the UTCI results as properties.
            Properties include (but are not limited to) the following:
                utci
                is_comfortable
                thermal_condition
                thermal_condition_five_point
                thermal_condition_seven_point
                thermal_condition_nine_point
                thermal_condition_eleven_point
                original_utci_category
    """
    # Get wind and mrt inputs
    wind_speed = self.wind_speed if include_wind is True else 0.1
    if include_sun is True:
        solarcal_obj = OutdoorSolarCal(self.location, self.direct_normal_radiation,
                                       self.diffuse_horizontal_radiation,
                                       self.horizontal_infrared_radiation_intensity,
                                       self.dry_bulb_temperature)
        mrt = solarcal_obj.mean_radiant_temperature
    else:
        mrt = self.dry_bulb_temperature

    utci_obj = UTCI(self.dry_bulb_temperature, self.relative_humidity, mrt, wind_speed,
                    comfort_parameter)
    return utci_obj


def get_standard_effective_temperature(self, include_wind=False, include_sun=False,
                                       met_rate=None, clo_value=None, external_work=None,
                                       comfort_parameter=None):
    """Get a SET comfort object from the conditions within the EPW file.

    Args:
        include_wind: Set to True to include the epw wind speed in the calculation.
            Note that, if set to True, an automatic conversion will be done from
            the meteorological wind speed at 10 meters to human height at ~1 meter.
            Specifcally, meteorological wind speeds will be multiplied by 2/3, which
            is also the underlying assumption of the universal thermal climate
            index model. Default is False assuming a condition that is shielded
            from wind.
        include_sun: Set to True to include the mean radiant temperature (MRT) delta
            from both shortwave solar falling directly on people and long wave radiant
            exchange with the sky. Default is False assuming a shaded condition.
            Note that, when set to True, this calculation will assume no surrounding
            context, standing human geometry, and a solar horizontal angle relative to
            front of person (SHARP) of 135 degrees. A SHARP of 135 essentially assumes
            that a person typically faces their side or back to the sun to avoid glare.
        met_rate: Data Collection of metabolic rate in met or a single
            metabolic rate value to be used for the whole analysis. If None,
            default is set to 1.1 met (for seated, typing).
        clo_value: Data Collection of clothing values rate in clo or a single
            clothing value to be used for the whole analysis. If None, default is
            set to 0.7 clo (for long sleeve shirt and pants).
        external_work: Data Collection of external work in met or a single
            external work value to be used for the whole analysis. If None,
            default is set to 0 met.
        comfort_parameter: Optional PMVParameter object to specify parameters under
            which conditions are considered acceptable. If None, default will
            assume a PPD threshold of 10%, no absolute humidity constraints
            and a still air threshold of 0.1 m/s.

    Returns:
        set_obj: An object with data collections of the SET results as properties.
            Properties include (but are not limited to) the following:
                standard_effective_temperature
                pmv
                ppd
                is_comfortable
                thermal_condition
    """
    # Get wind and mrt inputs
    wind_speed = self.wind_speed if include_wind is True else 0.1
    if include_sun is True:
        solarcal_obj = OutdoorSolarCal(self.location, self.direct_normal_radiation,
                                       self.diffuse_horizontal_radiation,
                                       self.horizontal_infrared_radiation_intensity,
                                       self.dry_bulb_temperature)
        mrt = solarcal_obj.mean_radiant_temperature
    else:
        mrt = self.dry_bulb_temperature

    set_obj = PMV(self.dry_bulb_temperature, self.relative_humidity, mrt, wind_speed,
                  met_rate, clo_value, external_work, comfort_parameter)
    return set_obj


EPW.get_universal_thermal_climate_index = get_universal_thermal_climate_index
EPW.get_standard_effective_temperature = get_standard_effective_temperature
