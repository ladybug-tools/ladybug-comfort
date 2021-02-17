# coding=utf-8
"""Objects for calculating solar-adjusted MRT from DataCollections."""
from __future__ import division

from ..solarcal import outdoor_sky_heat_exch, indoor_sky_heat_exch, \
    shortwave_from_horiz_solar, shortwave_from_horiz_components, \
    sharp_from_solar_and_body_azimuth
from ..parameter.solarcal import SolarCalParameter
from .base import ComfortCollection

from ladybug.location import Location
from ladybug.sunpath import Sunpath
from ladybug.datacollection import HourlyDiscontinuousCollection

from ladybug.datatype.temperature import Temperature, MeanRadiantTemperature
from ladybug.datatype.temperaturedelta import RadiantTemperatureDelta
from ladybug.datatype.energyflux import Irradiance, EffectiveRadiantField, \
    HorizontalInfraredRadiationIntensity, DiffuseHorizontalIrradiance, \
    DirectNormalIrradiance, DirectHorizontalIrradiance
from ladybug.datatype.energyintensity import Radiation
from ladybug.datatype.fraction import Fraction


class _SolarCalBase(ComfortCollection):
    """Base class used by all objects that use SolarCal with Data Collections."""
    __slots__ = ('_location', '_fract_exp', '_flr_ref', '_body_par', '_dmrt', '_mrt',
                 '_fract_exp_coll', '_flr_ref_coll', '_dmrt_coll', '_mrt_coll')

    def __init__(self, location, fraction_body_exposed=None, floor_reflectance=None,
                 solarcal_body_parameter=None):
        # set required inputs
        self._location_check(location)

        # check optional inputs
        self._fract_exp = self._fraction_input_check(
            fraction_body_exposed, 'fraction_body_exposed', 1)
        self._flr_ref = self._fraction_input_check(
            floor_reflectance, 'floor_reflectance', 0.25)

        # check comfort parameters
        self._body_par_check(solarcal_body_parameter)

        # setup lists to be filled
        self._dmrt = []
        self._mrt = []

    @property
    def location(self):
        """Ladybug Location object."""
        return self._location.duplicate()

    @property
    def fraction_body_exposed(self):
        """Data Collection of body fraction exposed to direct sun."""
        return self._get_coll('_fract_exp_coll', self._fract_exp,
                              Fraction('Fraction Body Exposed'), 'fraction')

    @property
    def floor_reflectance(self):
        """Data Collection of floor reflectance."""
        return self._get_coll('_flr_ref_coll', self._flr_ref,
                              Fraction('Floor Reflectance'), 'fraction')

    @property
    def solarcal_body_parameter(self):
        """SolarCal body parameters that are assigned to this object."""
        return self._body_par

    @property
    def mrt_delta(self):
        """Data Collection of total MRT delta in C."""
        return self._get_coll('_dmrt_coll', self._dmrt, RadiantTemperatureDelta, 'dC')

    @property
    def mean_radiant_temperature(self):
        """Data Collection of total mean radiant temperature in C."""
        return self._get_coll('_mrt_coll', self._mrt, MeanRadiantTemperature, 'C')

    def _location_check(self, location):
        assert isinstance(location, Location), 'location must be a Ladybug Location' \
            ' object. Got {}.'.format(type(location))
        self._location = location.duplicate()

    def _radiation_check(self, data_coll, name):
        assert isinstance(data_coll, HourlyDiscontinuousCollection), \
            '{} must be an hourly collection. Got {}.'.format(name, type(data_coll))
        if isinstance(data_coll.header.data_type, Radiation):
            self._check_datacoll(data_coll, Radiation, 'Wh/m2', name)
            timestep = data_coll.header.analysis_period.timestep
            assert timestep == 1, '{} timestep must be 1 when using Radiation as the ' \
                'data type. Got timestep of {}'.format(name, timestep)
        else:
            self._check_datacoll(data_coll, Irradiance, 'W/m2', name)

    def _fraction_input_check(self, data_coll, name, default):
        if data_coll is not None:
            return self._check_input(data_coll, Fraction, 'fraction', name)
        else:
            return [default] * self._calc_length

    def _body_par_check(self, body_par):
        if body_par is None:
            self._body_par = SolarCalParameter(posture='standing')
        else:
            assert isinstance(body_par, SolarCalParameter), \
                'solarcal_body_parameter must be a SolarCalParameter object. Got {}'\
                .format(type(body_par))
            self._body_par = body_par

    def _get_altitudes_and_sharps(self):
        """Get altitudes and sharps from solar position."""
        sp = Sunpath.from_location(self._location)
        _altitudes = []
        if self._body_par.body_azimuth is None:
            _sharps = [self._body_par.sharp] * self._calc_length
            for t_date in self._base_collection.datetimes:
                sun = sp.calculate_sun_from_date_time(t_date)
                _altitudes.append(sun.altitude)
        else:
            _sharps = []
            for t_date in self._base_collection.datetimes:
                sun = sp.calculate_sun_from_date_time(t_date)
                sharp = sharp_from_solar_and_body_azimuth(sun.azimuth,
                                                          self._body_par.body_azimuth)
                _sharps.append(sharp)
                _altitudes.append(sun.altitude)
        return _altitudes, _sharps


class OutdoorSolarCal(_SolarCalBase):
    """Outdoor SolarCal Collection object.

    Args:
        location: A Ladybug Location object.
        direct_normal_solar: Hourly Data Collection with the direct normal solar
            irradiance in W/m2.
        diffuse_horizontal_solar: Hourly Data Collection with the diffuse
            horizontal solar irradiance in W/m2.
        surface_temperatures: Hourly Data Collection with the temperature of surfaces
            around the person in degrees Celsius. This includes the ground and
            any other surfaces blocking the view to the sky. When the temperature
            of these individual surfaces are known, the input here should be the
            average temperature of the surfaces weighted by view-factor to the human.
            When such individual surface temperatures are unknown, the outdoor
            dry bulb temperature is typically used as a proxy.
        horizontal_infrared: Hourly Data Collection with the horizontal infrared
            radiation intensity from the sky in W/m2.
        fraction_body_exposed: A Data Collection or number between 0 and 1
            representing the fraction of the body exposed to direct sunlight.
            Note that this does not include the body’s self-shading; only the
            shading from surroundings.
            Default is 1 for a person standing in an open area.
        sky_exposure: A Data Collection or number between 0 and 1 representing the
            fraction of the sky vault in occupant’s view. Default is 1 for a person
            standing in an open area.
        floor_reflectance: A Data Collection or number between 0 and 1 that
            represents the reflectance of the floor. Default is for 0.25 which
            is characteristic of outdoor grass or dry bare soil.
        solarcal_body_parameter: Optional SolarCalParameter object to account for
            properties of the human geometry.

    Properties:
        * location
        * direct_normal_solar
        * diffuse_horizontal_solar
        * horizontal_infrared
        * surface_temperatures
        * fraction_body_exposed
        * sky_exposure
        * floor_reflectance
        * solarcal_body_parameter
        * shortwave_effective_radiant_field
        * longwave_effective_radiant_field
        * shortwave_mrt_delta
        * longwave_mrt_delta
        * mrt_delta
        * mean_radiant_temperature
    """
    _model = 'Outdoor SolarCal'
    __slots__ = ('_dir_norm', '_diff_horiz', '_horiz_ir', '_srf_temp', '_sky_exp',
                 '_s_erf', '_s_dmrt', '_l_erf', '_l_dmrt', '_dir_norm_coll',
                 '_diff_horiz_coll', '_horiz_ir_coll', '_srf_temp_coll', '_sky_exp_coll',
                 '_s_erf_coll', '_s_dmrt_coll', '_l_erf_coll', '_l_dmrt_coll')

    def __init__(self, location, direct_normal_solar, diffuse_horizontal_solar,
                 horizontal_infrared, surface_temperatures,
                 fraction_body_exposed=None, sky_exposure=None,
                 floor_reflectance=None, solarcal_body_parameter=None):
        """Initialize Outdoor SolarCal object.
        """
        # set up the object using radiation as a base
        self._radiation_check(direct_normal_solar, 'direct_normal_solar')
        self._radiation_check(diffuse_horizontal_solar, 'diffuse_horizontal_solar')
        self._input_collections = [direct_normal_solar, diffuse_horizontal_solar]
        self._calc_length = len(direct_normal_solar)
        self._base_collection = direct_normal_solar

        # check required inputs
        _SolarCalBase.__init__(self, location, fraction_body_exposed, floor_reflectance,
                               solarcal_body_parameter)
        self._dir_norm = direct_normal_solar.values
        self._diff_horiz = diffuse_horizontal_solar.values
        self._horiz_ir = self._check_input(
            horizontal_infrared, HorizontalInfraredRadiationIntensity, 'W/m2',
            'horizontal_infrared')
        self._srf_temp = self._check_input(
            surface_temperatures, Temperature, 'C', 'surface_temperatures')

        # check optional inputs
        self._sky_exp = self._fraction_input_check(sky_exposure, 'sky_exposure', 1)

        # check that all input data collections are aligned.
        HourlyDiscontinuousCollection.are_collections_aligned(self._input_collections)

        # compute SolarCal
        self._calculate_solarcal()

    def _calculate_solarcal(self):
        """Compute SolarCal for each step of the Data Collection."""
        # empty lists to be filled
        self._s_erf = []
        self._s_dmrt = []
        self._l_erf = []
        self._l_dmrt = []

        # get altitudes and sharps from solar position
        _altitudes, _sharps = self._get_altitudes_and_sharps()

        # calculate final erfs and mrt deltas
        for t_srfs, horiz_ir, diff, dir, alt, sharp, sky_e, fract_e, flr_ref in \
                zip(self._srf_temp, self._horiz_ir, self._diff_horiz, self._dir_norm,
                    _altitudes, _sharps, self._sky_exp, self._fract_exp, self._flr_ref):

            result = outdoor_sky_heat_exch(t_srfs, horiz_ir, diff, dir, alt, sky_e,
                                           fract_e, flr_ref, self._body_par.posture,
                                           sharp, self._body_par.body_absorptivity,
                                           self._body_par.body_emissivity)
            self._s_erf.append(result['s_erf'])
            self._s_dmrt.append(result['s_dmrt'])
            self._l_erf.append(result['l_erf'])
            self._l_dmrt.append(result['l_dmrt'])
            self._dmrt.append(result['s_dmrt'] + result['l_dmrt'])
            self._mrt.append(result['mrt'])

    @property
    def diffuse_horizontal_solar(self):
        """Data Collection of diffuse horizontal irradiance in W/m2."""
        return self._get_coll('_diff_horiz_coll', self._diff_horiz,
                              DiffuseHorizontalIrradiance, 'W/m2')

    @property
    def direct_normal_solar(self):
        """Data Collection of direct normal irradiance in W/m2."""
        return self._get_coll('_dir_norm_coll', self._dir_norm,
                              DirectNormalIrradiance, 'W/m2')

    @property
    def surface_temperatures(self):
        """Data Collection of surface temperature values in degrees C."""
        return self._get_coll('_srf_temp_coll', self._srf_temp,
                              Temperature('Surface Temperature'), 'C')

    @property
    def horizontal_infrared(self):
        """Data Collection of horizontal infrared radiation intensity in W/m2."""
        return self._get_coll('_horiz_ir_coll', self._horiz_ir,
                              HorizontalInfraredRadiationIntensity, 'W/m2')

    @property
    def sky_exposure(self):
        """Data Collection of sky view."""
        return self._get_coll('_sky_exp_coll', self._sky_exp,
                              Fraction('Sky Exposure'), 'fraction')

    @property
    def shortwave_effective_radiant_field(self):
        """Data Collection of shortwave effective radiant field in W/m2."""
        return self._get_coll('_s_erf_coll', self._s_erf,
                              EffectiveRadiantField, 'W/m2')

    @property
    def longwave_effective_radiant_field(self):
        """Data Collection of longwave effective radiant field in W/m2."""
        return self._get_coll('_l_erf_coll', self._l_erf,
                              EffectiveRadiantField, 'W/m2')

    @property
    def shortwave_mrt_delta(self):
        """Data Collection of shortwave MRT delta in C."""
        return self._get_coll('_s_dmrt_coll', self._s_dmrt,
                              RadiantTemperatureDelta, 'dC')

    @property
    def longwave_mrt_delta(self):
        """Data Collection of longwave MRT delta in C."""
        return self._get_coll('_l_dmrt_coll', self._l_dmrt,
                              RadiantTemperatureDelta, 'dC')


class IndoorSolarCal(_SolarCalBase):
    """Indoor SolarCal Collection object.

    Args:
        location: A Ladybug Location object.
        direct_normal_solar: Hourly Data Collection with the direct normal solar
            irradiance in W/m2.
        diffuse_horizontal_solar: Hourly Data Collection with the diffuse
            horizontal solar irradiance in W/m2.
        longwave_mrt: Hourly Data Collection or individual value with the longwave
            mean radiant temperature (MRT) expereinced as a result of indoor
            surface temperatures in C.
        fraction_body_exposed: A Data Collection or number between 0 and 1
            representing the fraction of the body exposed to direct sunlight.
            Note that this does not include the body’s self-shading; only the
            shading from surroundings.
            Default is 1 for a person standing in an open area.
        sky_exposure: A Data Collection or number between 0 and 1 representing the
            fraction of the sky vault in occupant’s view. Default is 1 for a person
            standing in an open area.
        floor_reflectance: A Data Collection or number between 0 and 1 that
            represents the reflectance of the floor. Default is for 0.25 which
            is characteristic of outdoor grass or dry bare soil.
        window_transmittance: A Data Collection or number between 0 and 1 that
            represents the broadband solar transmittance of the window through which
            the sun is coming. Such values tend to be slightly less than the
            SHGC. Values might be as low as 0.2 and could be as high as 0.85
            for a single pane of glass. Default is 0.4 assuming a double pane
            window with a relatively mild low-e coating.
        solarcal_body_parameter: Optional SolarCalParameter object to account for
            properties of the human geometry.

    Properties:
        * location
        * direct_normal_solar
        * diffuse_horizontal_solar
        * longwave_mrt
        * fraction_body_exposed
        * sky_exposure
        * floor_reflectance
        * window_transmittance
        * solarcal_body_parameter
        * effective_radiant_field
        * mrt_delta
        * mean_radiant_temperature
    """
    _model = 'Indoor SolarCal'
    __slots__ = ('_dir_norm', '_diff_horiz', '_l_mrt', '_sky_exp', '_win_trans',
                 '_erf', '_dmrt', '_dir_norm_coll', '_diff_horiz_coll', '_l_mrt_coll',
                 '_sky_exp_coll', '_win_trans_coll', '_erf_coll', '_dmrt_coll')

    def __init__(self, location, direct_normal_solar, diffuse_horizontal_solar,
                 longwave_mrt, fraction_body_exposed=None, sky_exposure=None,
                 floor_reflectance=None, window_transmittance=None,
                 solarcal_body_parameter=None):
        """Initialize Indoor SolarCal object.
        """
        # set up the object using radiation as a base
        self._radiation_check(direct_normal_solar, 'direct_normal_solar')
        self._radiation_check(diffuse_horizontal_solar, 'diffuse_horizontal_solar')
        self._input_collections = [direct_normal_solar, diffuse_horizontal_solar]
        self._calc_length = len(direct_normal_solar)
        self._base_collection = direct_normal_solar

        # check required inputs
        _SolarCalBase.__init__(self, location, fraction_body_exposed, floor_reflectance,
                               solarcal_body_parameter)
        self._dir_norm = direct_normal_solar.values
        self._diff_horiz = diffuse_horizontal_solar.values
        self._l_mrt = self._check_input(longwave_mrt, Temperature, 'C', 'longwave_mrt')

        # check optional inputs
        self._sky_exp = self._fraction_input_check(
            sky_exposure, 'sky_exposure', 1)
        self._win_trans = self._fraction_input_check(
            window_transmittance, 'window_transmittance', 0.4)

        # check that all input data collections are aligned.
        HourlyDiscontinuousCollection.are_collections_aligned(self._input_collections)

        # compute SolarCal
        self._calculate_solarcal()

    def _calculate_solarcal(self):
        """Compute SolarCal for each step of the Data Collection."""
        # empty lists to be filled
        self._erf = []

        # get altitudes and sharps from solar position
        _altitudes, _sharps = self._get_altitudes_and_sharps()

        # calculate final erfs and mrt deltas
        for l_mrt, diff, dir, alt, sharp, sky_e, fract_e, flr_ref, w_trans in \
                zip(self._l_mrt, self._diff_horiz, self._dir_norm, _altitudes, _sharps,
                    self._sky_exp, self._fract_exp, self._flr_ref, self._win_trans):

            result = indoor_sky_heat_exch(l_mrt, diff, dir, alt, sky_e, fract_e,
                                          flr_ref, w_trans, self._body_par.posture,
                                          sharp, self._body_par.body_absorptivity,
                                          self._body_par.body_emissivity)
            self._erf.append(result['erf'])
            self._dmrt.append(result['dmrt'])
            self._mrt.append(result['mrt'])

    @property
    def diffuse_horizontal_solar(self):
        """Data Collection of diffuse horizontal irradiance in Wh/m2 or W/m2."""
        return self._get_coll('_diff_horiz_coll', self._diff_horiz,
                              DiffuseHorizontalIrradiance, 'W/m2')

    @property
    def direct_normal_solar(self):
        """Data Collection of direct normal irradiance in Wh/m2 or W/m2."""
        return self._get_coll('_dir_norm_coll', self._dir_norm,
                              DirectNormalIrradiance, 'W/m2')

    @property
    def longwave_mrt(self):
        """Data Collection of surface temperature values in degrees C."""
        return self._get_coll('_l_mrt_coll', self._l_mrt,
                              MeanRadiantTemperature, 'C')

    @property
    def sky_exposure(self):
        """Data Collection of sky view."""
        return self._get_coll('_sky_exp_coll', self._sky_exp,
                              Fraction('Sky Exposure'), 'fraction')

    @property
    def window_transmittance(self):
        """Data Collection of window transmittance."""
        return self._get_coll('_win_trans_coll', self._win_trans,
                              Fraction('Window Transmittance'), 'fraction')

    @property
    def effective_radiant_field(self):
        """Data Collection of shortwave effective radiant field in W/m2."""
        return self._get_coll('_erf_coll', self._erf, EffectiveRadiantField, 'W/m2')

    @property
    def mrt_delta(self):
        """Data Collection of shortwave MRT delta in C."""
        return self._get_coll('_dmrt_coll', self._dmrt, RadiantTemperatureDelta, 'dC')


class HorizontalSolarCal(_SolarCalBase):
    """SolarCal Collection object from horizontal solar components.

    This is particularly useful when trying to estimate solar MRT deltas from
    Radiance radiation simulation result.

    Args:
        location: A Ladybug Location object.
        direct_horizontal_solar: Hourly Data Collection with the direct horizontal
            solar irradiance in W/m2.
        diffuse_horizontal_solar: Hourly Data Collection with the diffuse
            horizontal solar irradiance in W/m2.
        longwave_mrt: Hourly Data Collection or individual value with the longwave
            mean radiant temperature (MRT) expereinced as a result of indoor
            surface temperatures in C.
        fraction_body_exposed: A Data Collection or number between 0 and 1
            representing the fraction of the body exposed to direct sunlight.
            Note that this does not include the body’s self-shading; only the
            shading from surroundings.
            Default is 1 for a person standing in an open area.
        floor_reflectance: A Data Collection or number between 0 and 1 that
            represents the reflectance of the floor. Default is for 0.25 which
            is characteristic of outdoor grass or dry bare soil.
        solarcal_body_parameter: Optional SolarCalParameter object to account for
            properties of the human geometry.

    Properties:
        * location
        * direct_horizontal_solar
        * diffuse_horizontal_solar
        * longwave_mrt
        * fraction_body_exposed
        * floor_reflectance
        * solarcal_body_parameter
        * effective_radiant_field
        * mrt_delta
        * mean_radiant_temperature
    """
    _model = 'Horizontal SolarCal'
    __slots__ = ('_dir_horiz', '_diff_horiz', '_l_mrt', '_erf', '_dmrt',
                 '_dir_horiz_coll', '_diff_horiz_coll', '_l_mrt_coll',
                 '_erf_coll', '_dmrt_coll')

    def __init__(self, location, direct_horizontal_solar, diffuse_horizontal_solar,
                 longwave_mrt, fraction_body_exposed=None,
                 floor_reflectance=None, solarcal_body_parameter=None):
        """Initialize Horizontal SolarCal object.
        """
        # set up the object using radiation as a base
        self._radiation_check(direct_horizontal_solar, 'direct_horizontal_solar')
        self._radiation_check(diffuse_horizontal_solar, 'diffuse_horizontal_solar')
        self._input_collections = [direct_horizontal_solar, diffuse_horizontal_solar]
        self._calc_length = len(direct_horizontal_solar)
        self._base_collection = direct_horizontal_solar

        # check required inputs
        _SolarCalBase.__init__(self, location, fraction_body_exposed, floor_reflectance,
                               solarcal_body_parameter)
        self._dir_horiz = direct_horizontal_solar.values
        self._diff_horiz = diffuse_horizontal_solar.values
        self._l_mrt = self._check_input(longwave_mrt, Temperature, 'C', 'longwave_mrt')

        # check that all input data collections are aligned.
        HourlyDiscontinuousCollection.are_collections_aligned(self._input_collections)

        # compute SolarCal
        self._calculate_solarcal()

    def _calculate_solarcal(self):
        """Compute SolarCal for each step of the Data Collection."""
        # empty lists to be filled
        self._erf = []

        # get altitudes and sharps from solar position
        _altitudes, _sharps = self._get_altitudes_and_sharps()

        # calculate final erfs and mrt deltas
        for l_mrt, diff, dir, alt, sharp, fract_e, flr_ref, in \
                zip(self._l_mrt, self._diff_horiz, self._dir_horiz, _altitudes, _sharps,
                    self._fract_exp, self._flr_ref):

            result = shortwave_from_horiz_solar(l_mrt, diff, dir, alt, fract_e,
                                                flr_ref, self._body_par.posture,
                                                sharp, self._body_par.body_absorptivity,
                                                self._body_par.body_emissivity)
            self._erf.append(result['erf'])
            self._dmrt.append(result['dmrt'])
            self._mrt.append(result['mrt'])

    @property
    def diffuse_horizontal_solar(self):
        """Data Collection of diffuse horizontal irradiance in Wh/m2 or W/m2."""
        return self._get_coll('_diff_horiz_coll', self._diff_horiz,
                              DiffuseHorizontalIrradiance, 'W/m2')

    @property
    def direct_horizontal_solar(self):
        """Data Collection of direct horizontal irradiance in Wh/m2 or W/m2."""
        return self._get_coll('_dir_horiz_coll', self._dir_horiz,
                              DirectHorizontalIrradiance, 'W/m2')

    @property
    def longwave_mrt(self):
        """Data Collection of surface temperature values in degrees C."""
        return self._get_coll('_l_mrt_coll', self._l_mrt, MeanRadiantTemperature, 'C')

    @property
    def effective_radiant_field(self):
        """Data Collection of shortwave effective radiant field in W/m2."""
        return self._get_coll('_erf_coll', self._erf, EffectiveRadiantField, 'W/m2')

    @property
    def mrt_delta(self):
        """Data Collection of shortwave MRT delta in C."""
        return self._get_coll('_dmrt_coll', self._dmrt, RadiantTemperatureDelta, 'dC')


class HorizontalRefSolarCal(_SolarCalBase):
    """SolarCal Collection object from all horizontal components (including reflection).

    This is particularly useful when trying to estimate solar MRT deltas from
    Radiance radiation simulation result.

    Args:
        location: A Ladybug Location object.
        direct_horizontal_solar: Hourly Data Collection with the direct horizontal
            solar irradiance in W/m2.
        diffuse_horizontal_solar: Hourly Data Collection with the diffuse
            horizontal solar irradiance in W/m2.
        reflected_horizontal_solar: Hourly Data Collection with the ground-reflected
            horizontal solar irradiance in W/m2.
        longwave_mrt: Hourly Data Collection or individual value with the longwave
            mean radiant temperature (MRT) expereinced as a result of indoor
            surface temperatures in C.
        fraction_body_exposed: A Data Collection or number between 0 and 1
            representing the fraction of the body exposed to direct sunlight.
            Note that this does not include the body’s self-shading; only the
            shading from surroundings.
            Default is 1 for a person standing in an open area.
        solarcal_body_parameter: Optional SolarCalParameter object to account for
            properties of the human geometry.

    Properties:
        * location
        * direct_horizontal_solar
        * diffuse_horizontal_solar
        * reflected_horizontal_solar
        * longwave_mrt
        * fraction_body_exposed
        * solarcal_body_parameter
        * effective_radiant_field
        * mrt_delta
        * mean_radiant_temperature
    """
    _model = 'Horizontal Reflected SolarCal'
    __slots__ = ('_dir_horiz', '_diff_horiz', '_ref_horiz', '_l_mrt', '_erf', '_dmrt',
                 '_dir_horiz_coll', '_diff_horiz_coll', '_ref_horiz_coll', '_l_mrt_coll',
                 '_erf_coll', '_dmrt_coll')

    def __init__(self, location, direct_horizontal_solar, diffuse_horizontal_solar,
                 reflected_horizontal_solar, longwave_mrt, fraction_body_exposed=None,
                 solarcal_body_parameter=None):
        """Initialize Horizontal SolarCal object.
        """
        # set up the object using radiation as a base
        self._radiation_check(direct_horizontal_solar, 'direct_horizontal_solar')
        self._radiation_check(diffuse_horizontal_solar, 'diffuse_horizontal_solar')
        self._radiation_check(reflected_horizontal_solar, 'reflected_horizontal_solar')
        self._input_collections = [direct_horizontal_solar, diffuse_horizontal_solar,
                                   reflected_horizontal_solar]
        self._calc_length = len(direct_horizontal_solar)
        self._base_collection = direct_horizontal_solar

        # check required inputs
        _SolarCalBase.__init__(self, location, fraction_body_exposed, None,
                               solarcal_body_parameter)
        self._dir_horiz = direct_horizontal_solar.values
        self._diff_horiz = diffuse_horizontal_solar.values
        self._ref_horiz = reflected_horizontal_solar.values
        self._l_mrt = self._check_input(longwave_mrt, Temperature, 'C', 'longwave_mrt')

        # check that all input data collections are aligned.
        HourlyDiscontinuousCollection.are_collections_aligned(self._input_collections)

        # compute SolarCal
        self._calculate_solarcal()

    def _calculate_solarcal(self):
        """Compute SolarCal for each step of the Data Collection."""
        # empty lists to be filled
        self._erf = []

        # get altitudes and sharps from solar position
        _altitudes, _sharps = self._get_altitudes_and_sharps()

        # calculate final erfs and mrt deltas
        for l_mrt, diff, dir, ref, alt, sharp, fract_e, in \
                zip(self._l_mrt, self._diff_horiz, self._dir_horiz, self._ref_horiz,
                    _altitudes, _sharps, self._fract_exp):

            result = shortwave_from_horiz_components(
                l_mrt, diff, dir, ref, alt, fract_e, self._body_par.posture,
                sharp, self._body_par.body_absorptivity, self._body_par.body_emissivity)
            self._erf.append(result['erf'])
            self._dmrt.append(result['dmrt'])
            self._mrt.append(result['mrt'])

    @property
    def diffuse_horizontal_solar(self):
        """Data Collection of diffuse horizontal irradiance in Wh/m2 or W/m2."""
        return self._get_coll('_diff_horiz_coll', self._diff_horiz,
                              DiffuseHorizontalIrradiance, 'W/m2')

    @property
    def direct_horizontal_solar(self):
        """Data Collection of direct horizontal irradiance in Wh/m2 or W/m2."""
        return self._get_coll('_dir_horiz_coll', self._dir_horiz,
                              DirectHorizontalIrradiance, 'W/m2')

    @property
    def reflected_horizontal_solar(self):
        """Data Collection of direct horizontal irradiance in Wh/m2 or W/m2."""
        return self._get_coll('_ref_horiz_coll', self._ref_horiz, Irradiance, 'W/m2')

    @property
    def longwave_mrt(self):
        """Data Collection of surface temperature values in degrees C."""
        return self._get_coll('_l_mrt_coll', self._l_mrt, MeanRadiantTemperature, 'C')

    @property
    def effective_radiant_field(self):
        """Data Collection of shortwave effective radiant field in W/m2."""
        return self._get_coll('_erf_coll', self._erf, EffectiveRadiantField, 'W/m2')

    @property
    def mrt_delta(self):
        """Data Collection of shortwave MRT delta in C."""
        return self._get_coll('_dmrt_coll', self._dmrt, RadiantTemperatureDelta, 'dC')


class _HorizontalSolarCalMap(HorizontalSolarCal):
    """Special version of HorizontalSolarCal used in thermal mapping.

    This class exists purely for performance reasons so that solar positions do not
    need to be recalculated for every point within a thermal map.
    """
    __slots__ = ('_altitudes', '_sharps')

    def __init__(self, altitudes, sharps, direct_horizontal_solar,
                 diffuse_horizontal_solar, longwave_mrt, fraction_body_exposed=None,
                 floor_reflectance=None, solarcal_body_parameter=None):
        self._altitudes = altitudes
        self._sharps = sharps
        HorizontalSolarCal.__init__(
            self, None, direct_horizontal_solar, diffuse_horizontal_solar, longwave_mrt,
            fraction_body_exposed, floor_reflectance, solarcal_body_parameter)

    def _location_check(self, location):
        self._location = None

    def _get_altitudes_and_sharps(self):
        return self._altitudes, self._sharps



class _HorizontalRefSolarCalMap(HorizontalRefSolarCal):
    """Special version of HorizontalRefSolarCal used in thermal mapping.

    This class exists purely for performance reasons so that solar positions do not
    need to be recalculated for every point within a thermal map.
    """
    __slots__ = ('_altitudes', '_sharps')

    def __init__(self, altitudes, sharps, direct_horizontal_solar,
                 diffuse_horizontal_solar, reflected_horizontal_solar, longwave_mrt,
                 fraction_body_exposed=None, solarcal_body_parameter=None):
        self._altitudes = altitudes
        self._sharps = sharps
        HorizontalRefSolarCal.__init__(
            self, None, direct_horizontal_solar, diffuse_horizontal_solar,
            reflected_horizontal_solar, longwave_mrt, fraction_body_exposed,
            solarcal_body_parameter)

    def _location_check(self, location):
        self._location = None

    def _get_altitudes_and_sharps(self):
        return self._altitudes, self._sharps
