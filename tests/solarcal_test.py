# coding utf-8
import pytest

from ladybug_comfort.collection.solarcal import OutdoorSolarCal, IndoorSolarCal, \
    HorizontalSolarCal, HorizontalRefSolarCal
from ladybug_comfort.parameter.solarcal import SolarCalParameter

from ladybug_comfort.solarcal import outdoor_sky_heat_exch, indoor_sky_heat_exch, \
    shortwave_from_horiz_solar, mrt_delta_from_erf, erf_from_mrt_delta, \
    get_projection_factor, get_projection_factor_simple, \
    sharp_from_solar_and_body_azimuth, body_solar_flux_from_parts, \
    body_solar_flux_from_horiz_solar

from ladybug.location import Location
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.epw import EPW
from ladybug.wea import Wea
from ladybug.sunpath import Sunpath

from ladybug.datatype.energyflux import Irradiance

import math
import sys
if (sys.version_info > (3, 0)):
    xrange = range


def test_outdoor_sky_heat_exch():
    """Test the outdoor_sky_heat_exch function"""
    # Test typical daytime condition
    sky_exch = outdoor_sky_heat_exch(22, 380, 200, 380, 45)
    assert sky_exch['s_erf'] == pytest.approx(129.239, rel=1e-2)
    assert sky_exch['s_dmrt'] == pytest.approx(29.6508, rel=1e-2)
    assert sky_exch['l_erf'] == pytest.approx(-11.6208, rel=1e-2)
    assert sky_exch['l_dmrt'] == pytest.approx(-2.6661, rel=1e-2)
    assert sky_exch['mrt'] == pytest.approx(48.9847, rel=1e-2)

    # Test typical nighttime condition
    sky_exch = outdoor_sky_heat_exch(18, 330, 0, 0, 0)
    assert sky_exch['s_erf'] == pytest.approx(0, rel=1e-2)
    assert sky_exch['s_dmrt'] == pytest.approx(0, rel=1e-2)
    assert sky_exch['l_erf'] == pytest.approx(-24.792, rel=1e-2)
    assert sky_exch['l_dmrt'] == pytest.approx(-5.688, rel=1e-2)
    assert sky_exch['mrt'] == pytest.approx(12.3120, rel=1e-2)


def test_indoor_sky_heat_exch():
    """Test the indoor_sky_heat_exch function"""
    # Test typical daytime condition
    sky_exch = indoor_sky_heat_exch(22, 200, 380, 45, 0.5, 0.5)
    assert sky_exch['erf'] == pytest.approx(23.71407, rel=1e-2)
    assert sky_exch['dmrt'] == pytest.approx(5.66732, rel=1e-2)
    assert sky_exch['mrt'] == pytest.approx(27.6673, rel=1e-2)

    # Test typical nighttime condition
    sky_exch = indoor_sky_heat_exch(22, 0, 0, 0, 0.5, 0.5)
    assert sky_exch['erf'] == pytest.approx(0, rel=1e-2)
    assert sky_exch['dmrt'] == pytest.approx(0, rel=1e-2)
    assert sky_exch['mrt'] == pytest.approx(22, rel=1e-2)


def test_shortwave_from_horiz_solar():
    """Test the shortwave_from_horiz_solar function."""
    # Test typical daytime noon condition
    sky_exch = shortwave_from_horiz_solar(22, 144, 850, 72)
    assert sky_exch['erf'] == pytest.approx(168.7179, rel=1e-2)
    assert sky_exch['dmrt'] == pytest.approx(38.7083, rel=1e-2)
    assert sky_exch['mrt'] == pytest.approx(60.7083, rel=1e-2)

    # Test typical daytime condition
    sky_exch = shortwave_from_horiz_solar(22, 120, 500, 45)
    assert sky_exch['erf'] == pytest.approx(157.33914, rel=1e-2)
    assert sky_exch['dmrt'] == pytest.approx(36.09772, rel=1e-2)
    assert sky_exch['mrt'] == pytest.approx(58.09772, rel=1e-2)

    # Test typical daytime low angle condition
    sky_exch = shortwave_from_horiz_solar(22, 10, 55, 15)
    assert sky_exch['erf'] == pytest.approx(41.61606, rel=1e-2)
    assert sky_exch['dmrt'] == pytest.approx(9.547814, rel=1e-2)
    assert sky_exch['mrt'] == pytest.approx(31.547814, rel=1e-2)

    # Test typical nighttime condition
    sky_exch = shortwave_from_horiz_solar(18, 0, 0, -10, 0.5)
    assert sky_exch['erf'] == pytest.approx(0, rel=1e-2)
    assert sky_exch['dmrt'] == pytest.approx(0, rel=1e-2)
    assert sky_exch['mrt'] == pytest.approx(18, rel=1e-2)


def test_solarcal_validation():
    """Test the SolarCal function against the reference table from ASHRAE-55 2017.
    """
    validation_csv_file_path = './tests/validation_tables/solarcal_validation.csv'
    with open(validation_csv_file_path) as csv_data_file:
        csv_data_file.readline()
        csv_data_file.readline()
        for row in csv_data_file:
            vals = []
            for val in row.split(','):
                try:
                    vals.append(float(val))
                except ValueError:
                    vals.append(str(val))
            i_diff = 0.17 * vals[3] * math.sin(math.radians(vals[0]))
            result = indoor_sky_heat_exch(20, i_diff, vals[3], vals[0], vals[5],
                                          vals[6], 0.6, vals[4], vals[2],
                                          vals[1], vals[7])
            # Values don't match perfectly because we use the original SolarCal splines
            assert result['erf'] == pytest.approx(vals[8], rel=1e-2)
            assert result['dmrt'] == pytest.approx(vals[9], rel=1e-1)


def test_body_dir_from_dir_normal():
    """Test body_solar_flux_from_parts gainst its horizontal counterpart."""
    wea_obj = Wea.from_epw_file('./tests/epw/chicago.epw')
    diff_hr = wea_obj.diffuse_horizontal_irradiance.values
    dir_nr = wea_obj.direct_normal_irradiance.values
    dir_hr = wea_obj.direct_horizontal_irradiance.values
    dts = wea_obj.datetimes
    sp = Sunpath.from_location(wea_obj.location)

    for i in xrange(8760):
        sun = sp.calculate_sun_from_date_time(dts[i])
        alt, az = sun.altitude, sun.azimuth
        sharp = sharp_from_solar_and_body_azimuth(az, 180)
        sflux1 = body_solar_flux_from_parts(diff_hr[i], dir_nr[i], alt, sharp)
        sflux2 = body_solar_flux_from_horiz_solar(diff_hr[i], dir_hr[i], alt, sharp)
        assert sflux1 == pytest.approx(sflux2, rel=1e-2)


def test_mrt_delta_from_erf():
    """Test the mrt_delta_from_erf function."""
    dmrt1 = mrt_delta_from_erf(100)
    dmrt2 = mrt_delta_from_erf(0)
    dmrt3 = mrt_delta_from_erf(-100)

    assert dmrt1 == abs(dmrt3) == pytest.approx(22.94262, rel=1e-2)
    assert dmrt2 == 0


def test_erf_from_mrt_delta():
    """Test the erf_from_mrt_delta function."""
    erf1 = erf_from_mrt_delta(22.94262050611421)
    erf2 = erf_from_mrt_delta(0)
    erf3 = erf_from_mrt_delta(-22.94262050611421)

    assert erf1 == abs(erf3) == pytest.approx(100, rel=1e-2)
    assert erf2 == 0


def test_sharp_from_solar_and_body_azimuth():
    """Test the sharp_from_solar_and_body_azimuth function."""
    assert sharp_from_solar_and_body_azimuth(0, 0) == 0
    assert sharp_from_solar_and_body_azimuth(180, 180) == 0
    assert sharp_from_solar_and_body_azimuth(0, 90) == 90
    assert sharp_from_solar_and_body_azimuth(360, 90) == 90
    assert sharp_from_solar_and_body_azimuth(270, 90) == 180
    assert sharp_from_solar_and_body_azimuth(360, 180) == 180
    assert sharp_from_solar_and_body_azimuth(360, 270) == 90
    assert sharp_from_solar_and_body_azimuth(0, 270) == 90
    assert sharp_from_solar_and_body_azimuth(90, 270) == 180


def test_projection_factors():
    """Test the projection factor functions against one another."""
    for posture in ('standing', 'seated', 'supine'):
        for alt in list(xrange(1, 90, 10)) + [90]:
            for sharp in xrange(0, 190, 10):
                pf1 = get_projection_factor(alt, sharp, posture)
                pf2 = get_projection_factor_simple(alt, sharp, posture)
                assert pf1 == pytest.approx(pf2, rel=0.1)


def test_projection_factors_incorrect():
    """Test the projection factor functions with incorrect inputs."""
    with pytest.raises(Exception):
        get_projection_factor(25, 0, 'Standing')  # incorrect capitalization
    with pytest.raises(Exception):
        get_projection_factor(100, 0, 'standing')  # incorrect altitude
    with pytest.raises(Exception):
        get_projection_factor_simple(25, 0, 'Standing')  # incorrect capitalization
    with pytest.raises(Exception):
        get_projection_factor_simple(100, 0, 'standing')  # incorrect altitude


def test_solarcal_parameter_init():
    """Test the initialization of the SolarCalParameter object."""
    posture = 'seated'
    sharp = 180
    absorptivity = 0.8
    emissivity = 0.97
    solarcal_par = SolarCalParameter(posture=posture,
                                     sharp=sharp,
                                     body_absorptivity=absorptivity,
                                     body_emissivity=emissivity)
    assert solarcal_par.posture == posture
    assert solarcal_par.sharp == sharp
    assert solarcal_par.body_azimuth is None
    assert solarcal_par.body_absorptivity == absorptivity
    assert solarcal_par.body_emissivity == emissivity


def test_solarcal_parameter_default():
    """Test the default SolarCalParameter properties."""
    solarcal_par = SolarCalParameter()
    str(solarcal_par)  # test casting the parameters to a string
    assert solarcal_par.posture == 'standing'
    assert solarcal_par.sharp == 135
    assert solarcal_par.body_azimuth is None
    assert solarcal_par.body_absorptivity == 0.7
    assert solarcal_par.body_emissivity == 0.95
    solarcal_par.POSTURES  # test that the acceptable postures are there


def test_solarcal_parameter_incorrect():
    """Test incorrect SolarCalParameter properties."""
    with pytest.raises(Exception):
        SolarCalParameter(posture='seated',
                          sharp=180,
                          body_azimuth=135,  # both sharp and azimuth
                          body_absorptivity=0.8,
                          body_emissivity=0.97)
    with pytest.raises(Exception):
        SolarCalParameter(posture='disco pose')  # incorrect posture
    with pytest.raises(Exception):
        SolarCalParameter(sharp=270)  # incorrect sharp
    with pytest.raises(Exception):
        SolarCalParameter(body_absorptivity=60)  # incorrect body_absorptivity
    with pytest.raises(Exception):
        SolarCalParameter(body_emissivity=97)  # incorrect body_emissivity


def test_solarcal_parameter_to_from_dict():
    """Test the to/from dict methods of the SolarCalParameter object."""
    posture = 'seated'
    sharp = 180
    absorptivity = 0.8
    emissivity = 0.97

    solarcal_par = SolarCalParameter(posture=posture,
                                     sharp=sharp,
                                     body_absorptivity=absorptivity,
                                     body_emissivity=emissivity)
    solarcal_par_dict = solarcal_par.to_dict()
    new_solarcal_par = SolarCalParameter.from_dict(solarcal_par_dict)

    assert new_solarcal_par.posture == posture
    assert new_solarcal_par.sharp == sharp
    assert new_solarcal_par.body_azimuth is None
    assert new_solarcal_par.body_absorptivity == absorptivity
    assert new_solarcal_par.body_emissivity == emissivity


def test_solarcal_parameter_to_from_str():
    """Test the to/from string methods of the SolarCalParameter object."""
    posture = 'seated'
    sharp = 180
    absorptivity = 0.8
    emissivity = 0.97

    solarcal_par = SolarCalParameter(posture=posture,
                                     sharp=sharp,
                                     body_absorptivity=absorptivity,
                                     body_emissivity=emissivity)
    new_solarcal_par = SolarCalParameter.from_string(str(solarcal_par))

    assert new_solarcal_par.posture == posture
    assert new_solarcal_par.sharp == sharp
    assert new_solarcal_par.body_azimuth is None
    assert new_solarcal_par.body_absorptivity == absorptivity
    assert new_solarcal_par.body_emissivity == emissivity


def test_init_outdoor_solarcal_collection():
    """Test the initialization of the OutdoorSolarCal collection."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [500] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [200] * calc_length)
    solarcal_obj = OutdoorSolarCal(Location(), dir_norm, diff_horiz, 350, 24)

    assert solarcal_obj.comfort_model == 'Outdoor SolarCal'
    assert solarcal_obj.calc_length == calc_length
    str(solarcal_obj)  # test that the string representaiton is ok

    assert isinstance(solarcal_obj.direct_normal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.direct_normal_solar.values) == calc_length
    assert solarcal_obj.direct_normal_solar[12] == 500
    assert isinstance(solarcal_obj.diffuse_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.diffuse_horizontal_solar.values) == calc_length
    assert solarcal_obj.diffuse_horizontal_solar[12] == 200

    assert isinstance(solarcal_obj.shortwave_effective_radiant_field, HourlyContinuousCollection)
    assert len(solarcal_obj.shortwave_effective_radiant_field.values) == calc_length
    assert solarcal_obj.shortwave_effective_radiant_field[12] == pytest.approx(137.30710, rel=1e-3)
    assert isinstance(solarcal_obj.longwave_effective_radiant_field, HourlyContinuousCollection)
    assert len(solarcal_obj.longwave_effective_radiant_field.values) == calc_length
    assert solarcal_obj.longwave_effective_radiant_field[12] == pytest.approx(-28.8326, rel=1e-3)
    assert isinstance(solarcal_obj.shortwave_mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.shortwave_mrt_delta.values) == calc_length
    assert solarcal_obj.shortwave_mrt_delta[12] == pytest.approx(31.50184, rel=1e-3)
    assert isinstance(solarcal_obj.longwave_mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.longwave_mrt_delta.values) == calc_length
    assert solarcal_obj.longwave_mrt_delta[12] == pytest.approx(-6.614966, rel=1e-3)
    assert isinstance(solarcal_obj.mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.mrt_delta.values) == calc_length
    assert solarcal_obj.mrt_delta[12] == pytest.approx(24.886886, rel=1e-3)
    assert isinstance(solarcal_obj.mean_radiant_temperature, HourlyContinuousCollection)
    assert len(solarcal_obj.mean_radiant_temperature.values) == calc_length
    assert solarcal_obj.mean_radiant_temperature[12] == pytest.approx(48.88688, rel=1e-3)


def test_outdoor_solarcal_collection_defaults():
    """Test the default inputs assigned to the OutdoorSolarCal collection."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [500] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [200] * calc_length)
    solarcal_obj = OutdoorSolarCal(Location(), dir_norm, diff_horiz, 350, 24)

    assert isinstance(solarcal_obj.fraction_body_exposed, HourlyContinuousCollection)
    assert len(solarcal_obj.fraction_body_exposed.values) == calc_length
    assert solarcal_obj.fraction_body_exposed[12] == 1

    assert isinstance(solarcal_obj.sky_exposure, HourlyContinuousCollection)
    assert len(solarcal_obj.sky_exposure.values) == calc_length
    assert solarcal_obj.sky_exposure[12] == 1

    assert isinstance(solarcal_obj.floor_reflectance, HourlyContinuousCollection)
    assert len(solarcal_obj.floor_reflectance.values) == calc_length
    assert solarcal_obj.floor_reflectance[12] == 0.25

    assert isinstance(solarcal_obj.solarcal_body_parameter, SolarCalParameter)
    default_par = SolarCalParameter()
    assert solarcal_obj.solarcal_body_parameter.posture == default_par.posture
    assert solarcal_obj.solarcal_body_parameter.sharp == default_par.sharp
    assert solarcal_obj.solarcal_body_parameter.body_azimuth == default_par.body_azimuth
    assert solarcal_obj.solarcal_body_parameter.body_absorptivity == default_par.body_absorptivity
    assert solarcal_obj.solarcal_body_parameter.body_emissivity == default_par.body_emissivity


def test_outdoor_solarcal_collection_full_input():
    """Test the initialization of the OutdoorSolarCal collection will all inputs."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [500] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [200] * calc_length)
    custom_par = SolarCalParameter('seated', None, 45, 0.65, 0.97)
    solarcal_obj = OutdoorSolarCal(Location(), dir_norm, diff_horiz, 350, 24,
                                   0.6, 0.4, 0.35, custom_par)

    assert solarcal_obj.fraction_body_exposed[12] == 0.6
    assert solarcal_obj.sky_exposure[12] == 0.4
    assert solarcal_obj.floor_reflectance[0] == 0.35
    assert solarcal_obj.solarcal_body_parameter.posture == 'seated'
    assert solarcal_obj.solarcal_body_parameter.sharp is None
    assert solarcal_obj.solarcal_body_parameter.body_azimuth == 45
    assert solarcal_obj.solarcal_body_parameter.body_absorptivity == 0.65
    assert solarcal_obj.solarcal_body_parameter.body_emissivity == 0.97


def test_init_outdoor_solarcal_collection_epw():
    """Test the initialization of the OutdoorSolarCal collection with EPW input."""
    calc_length = 8760
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    solarcal_obj = OutdoorSolarCal(epw.location, epw.direct_normal_radiation,
                                   epw.diffuse_horizontal_radiation,
                                   epw.horizontal_infrared_radiation_intensity,
                                   epw.dry_bulb_temperature)

    assert isinstance(solarcal_obj.direct_normal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.direct_normal_solar.values) == calc_length
    assert solarcal_obj.direct_normal_solar[12] == pytest.approx(151, rel=1e-3)
    assert isinstance(solarcal_obj.diffuse_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.diffuse_horizontal_solar.values) == calc_length
    assert solarcal_obj.diffuse_horizontal_solar[12] == pytest.approx(168, rel=1e-3)

    assert isinstance(solarcal_obj.shortwave_effective_radiant_field, HourlyContinuousCollection)
    assert len(solarcal_obj.shortwave_effective_radiant_field.values) == calc_length
    assert solarcal_obj.shortwave_effective_radiant_field[12] == pytest.approx(83.29130, rel=1e-3)
    assert isinstance(solarcal_obj.longwave_effective_radiant_field, HourlyContinuousCollection)
    assert len(solarcal_obj.longwave_effective_radiant_field.values) == calc_length
    assert solarcal_obj.longwave_effective_radiant_field[12] == pytest.approx(-27.39307, rel=1e-3)
    assert isinstance(solarcal_obj.shortwave_mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.shortwave_mrt_delta.values) == calc_length
    assert solarcal_obj.shortwave_mrt_delta[12] == pytest.approx(19.109207, rel=1e-3)
    assert isinstance(solarcal_obj.longwave_mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.longwave_mrt_delta.values) == calc_length
    assert solarcal_obj.longwave_mrt_delta[12] == pytest.approx(-6.284688, rel=1e-3)
    assert isinstance(solarcal_obj.mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.mrt_delta.values) == calc_length
    assert solarcal_obj.mrt_delta[12] == pytest.approx(12.8245189, rel=1e-3)
    assert isinstance(solarcal_obj.mean_radiant_temperature, HourlyContinuousCollection)
    assert len(solarcal_obj.mean_radiant_temperature.values) == calc_length
    assert solarcal_obj.mean_radiant_temperature[12] == pytest.approx(9.524518, rel=1e-3)


def test_init_indoor_solarcal_collection():
    """Test the initialization of the IndoorSolarCal collection."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [500] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [200] * calc_length)
    solarcal_obj = IndoorSolarCal(Location(), dir_norm, diff_horiz, 24)

    assert solarcal_obj.comfort_model == 'Indoor SolarCal'
    assert solarcal_obj.calc_length == calc_length
    str(solarcal_obj)  # test that the string representaiton is ok

    assert isinstance(solarcal_obj.direct_normal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.direct_normal_solar.values) == calc_length
    assert solarcal_obj.direct_normal_solar[12] == 500
    assert isinstance(solarcal_obj.diffuse_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.diffuse_horizontal_solar.values) == calc_length
    assert solarcal_obj.diffuse_horizontal_solar[12] == 200

    assert isinstance(solarcal_obj.effective_radiant_field, HourlyContinuousCollection)
    assert len(solarcal_obj.effective_radiant_field.values) == calc_length
    assert solarcal_obj.effective_radiant_field[12] == pytest.approx(54.9228, rel=1e-3)
    assert isinstance(solarcal_obj.mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.mrt_delta.values) == calc_length
    assert solarcal_obj.mrt_delta[12] == pytest.approx(12.600738, rel=1e-3)
    assert isinstance(solarcal_obj.mean_radiant_temperature, HourlyContinuousCollection)
    assert len(solarcal_obj.mean_radiant_temperature.values) == calc_length
    assert solarcal_obj.mean_radiant_temperature[12] == pytest.approx(36.600738, rel=1e-3)


def test_indoor_solarcal_collection_defaults():
    """Test the default inputs assigned to the IndoorSolarCal collection."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [500] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [200] * calc_length)
    solarcal_obj = IndoorSolarCal(Location(), dir_norm, diff_horiz, 24)

    assert isinstance(solarcal_obj.fraction_body_exposed, HourlyContinuousCollection)
    assert len(solarcal_obj.fraction_body_exposed.values) == calc_length
    assert solarcal_obj.fraction_body_exposed[12] == 1

    assert isinstance(solarcal_obj.sky_exposure, HourlyContinuousCollection)
    assert len(solarcal_obj.sky_exposure.values) == calc_length
    assert solarcal_obj.sky_exposure[12] == 1

    assert isinstance(solarcal_obj.floor_reflectance, HourlyContinuousCollection)
    assert len(solarcal_obj.floor_reflectance.values) == calc_length
    assert solarcal_obj.floor_reflectance[12] == 0.25

    assert isinstance(solarcal_obj.window_transmittance, HourlyContinuousCollection)
    assert len(solarcal_obj.window_transmittance.values) == calc_length
    assert solarcal_obj.window_transmittance[12] == 0.4

    assert isinstance(solarcal_obj.solarcal_body_parameter, SolarCalParameter)
    default_par = SolarCalParameter()
    assert solarcal_obj.solarcal_body_parameter.posture == default_par.posture
    assert solarcal_obj.solarcal_body_parameter.sharp == default_par.sharp
    assert solarcal_obj.solarcal_body_parameter.body_azimuth == default_par.body_azimuth
    assert solarcal_obj.solarcal_body_parameter.body_absorptivity == default_par.body_absorptivity
    assert solarcal_obj.solarcal_body_parameter.body_emissivity == default_par.body_emissivity


def test_indoor_solarcal_collection_full_input():
    """Test the initialization of the IndoorSolarCal collection will all inputs."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [500] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [200] * calc_length)
    custom_par = SolarCalParameter('seated', None, 45, 0.65, 0.97)
    solarcal_obj = IndoorSolarCal(Location(), dir_norm, diff_horiz, 24,
                                  0.6, 0.4, 0.35, 0.7, custom_par)

    assert solarcal_obj.fraction_body_exposed[12] == 0.6
    assert solarcal_obj.sky_exposure[12] == 0.4
    assert solarcal_obj.floor_reflectance[0] == 0.35
    assert solarcal_obj.window_transmittance[0] == 0.7
    assert solarcal_obj.solarcal_body_parameter.posture == 'seated'
    assert solarcal_obj.solarcal_body_parameter.sharp is None
    assert solarcal_obj.solarcal_body_parameter.body_azimuth == 45
    assert solarcal_obj.solarcal_body_parameter.body_absorptivity == 0.65
    assert solarcal_obj.solarcal_body_parameter.body_emissivity == 0.97


def test_init_indoor_solarcal_collection_epw():
    """Test the initialization of the IndoorSolarCal collection with EPW input."""
    calc_length = 8760
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    solarcal_obj = IndoorSolarCal(epw.location, epw.direct_normal_radiation,
                                  epw.diffuse_horizontal_radiation, 24)

    assert isinstance(solarcal_obj.direct_normal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.direct_normal_solar.values) == calc_length
    assert solarcal_obj.direct_normal_solar[12] == pytest.approx(151, rel=1e-3)
    assert isinstance(solarcal_obj.diffuse_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.diffuse_horizontal_solar.values) == calc_length
    assert solarcal_obj.diffuse_horizontal_solar[12] == pytest.approx(168, rel=1e-3)

    assert isinstance(solarcal_obj.effective_radiant_field, HourlyContinuousCollection)
    assert len(solarcal_obj.effective_radiant_field.values) == calc_length
    assert solarcal_obj.effective_radiant_field[12] == pytest.approx(33.31652, rel=1e-3)
    assert isinstance(solarcal_obj.mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.mrt_delta.values) == calc_length
    assert solarcal_obj.mrt_delta[12] == pytest.approx(7.6436828, rel=1e-3)
    assert isinstance(solarcal_obj.mean_radiant_temperature, HourlyContinuousCollection)
    assert len(solarcal_obj.mean_radiant_temperature.values) == calc_length
    assert solarcal_obj.mean_radiant_temperature[12] == pytest.approx(31.6436828, rel=1e-3)


def test_init_horizontal_solarcal_collection():
    """Test the initialization of the HorizontalSolarCal collection."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [300] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [100] * calc_length)
    solarcal_obj = HorizontalSolarCal(Location(), dir_norm, diff_horiz, 24)

    assert solarcal_obj.comfort_model == 'Horizontal SolarCal'
    assert solarcal_obj.calc_length == calc_length
    str(solarcal_obj)  # test that the string representation is ok

    assert isinstance(solarcal_obj.direct_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.direct_horizontal_solar.values) == calc_length
    assert solarcal_obj.direct_horizontal_solar[12] == 300
    assert isinstance(solarcal_obj.diffuse_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.diffuse_horizontal_solar.values) == calc_length
    assert solarcal_obj.diffuse_horizontal_solar[12] == 100

    assert isinstance(solarcal_obj.effective_radiant_field, HourlyContinuousCollection)
    assert len(solarcal_obj.effective_radiant_field.values) == calc_length
    assert solarcal_obj.effective_radiant_field[12] == pytest.approx(79.35027, rel=1e-3)
    assert isinstance(solarcal_obj.mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.mrt_delta.values) == calc_length
    assert solarcal_obj.mrt_delta[12] == pytest.approx(18.20503, rel=1e-3)
    assert isinstance(solarcal_obj.mean_radiant_temperature, HourlyContinuousCollection)
    assert len(solarcal_obj.mean_radiant_temperature.values) == calc_length
    assert solarcal_obj.mean_radiant_temperature[12] == pytest.approx(42.20503, rel=1e-3)


def test_horizontal_solarcal_collection_defaults():
    """Test the default inputs assigned to the HorizontalSolarCal collection."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [500] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [200] * calc_length)
    solarcal_obj = HorizontalSolarCal(Location(), dir_norm, diff_horiz, 24)

    assert isinstance(solarcal_obj.fraction_body_exposed, HourlyContinuousCollection)
    assert len(solarcal_obj.fraction_body_exposed.values) == calc_length
    assert solarcal_obj.fraction_body_exposed[12] == 1

    assert isinstance(solarcal_obj.floor_reflectance, HourlyContinuousCollection)
    assert len(solarcal_obj.floor_reflectance.values) == calc_length
    assert solarcal_obj.floor_reflectance[12] == 0.25

    assert isinstance(solarcal_obj.solarcal_body_parameter, SolarCalParameter)
    default_par = SolarCalParameter()
    assert solarcal_obj.solarcal_body_parameter.posture == default_par.posture
    assert solarcal_obj.solarcal_body_parameter.sharp == default_par.sharp
    assert solarcal_obj.solarcal_body_parameter.body_azimuth == default_par.body_azimuth
    assert solarcal_obj.solarcal_body_parameter.body_absorptivity == default_par.body_absorptivity
    assert solarcal_obj.solarcal_body_parameter.body_emissivity == default_par.body_emissivity


def test_horizontal_solarcal_collection_full_input():
    """Test the initialization of the HorizontalSolarCal collection will all inputs."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [500] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [200] * calc_length)
    custom_par = SolarCalParameter('seated', None, 45, 0.65, 0.97)
    solarcal_obj = HorizontalSolarCal(Location(), dir_norm, diff_horiz, 24,
                                      0.6, 0.35, custom_par)

    assert solarcal_obj.fraction_body_exposed[12] == 0.6
    assert solarcal_obj.floor_reflectance[0] == 0.35
    assert solarcal_obj.solarcal_body_parameter.posture == 'seated'
    assert solarcal_obj.solarcal_body_parameter.sharp is None
    assert solarcal_obj.solarcal_body_parameter.body_azimuth == 45
    assert solarcal_obj.solarcal_body_parameter.body_absorptivity == 0.65
    assert solarcal_obj.solarcal_body_parameter.body_emissivity == 0.97


def test_init_horizontal_solarcal_collection_epw():
    """Test the initialization of the HorizontalSolarCal collection with EPW input."""
    calc_length = 8760
    wea_obj = Wea.from_epw_file('./tests/epw/chicago.epw')
    diff_hr = wea_obj.diffuse_horizontal_irradiance
    dir_hr = wea_obj.direct_horizontal_irradiance
    solarcal_obj = HorizontalSolarCal(wea_obj.location, dir_hr, diff_hr, 24)

    assert isinstance(solarcal_obj.direct_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.direct_horizontal_solar.values) == calc_length
    assert solarcal_obj.direct_horizontal_solar[12] == pytest.approx(62.9354, rel=1e-3)
    assert isinstance(solarcal_obj.diffuse_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.diffuse_horizontal_solar.values) == calc_length
    assert solarcal_obj.diffuse_horizontal_solar[12] == pytest.approx(168, rel=1e-3)

    assert isinstance(solarcal_obj.effective_radiant_field, HourlyContinuousCollection)
    assert len(solarcal_obj.effective_radiant_field.values) == calc_length
    assert solarcal_obj.effective_radiant_field[12] == pytest.approx(82.80573, rel=1e-3)
    assert isinstance(solarcal_obj.mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.mrt_delta.values) == calc_length
    assert solarcal_obj.mrt_delta[12] == pytest.approx(18.997806, rel=1e-3)
    assert isinstance(solarcal_obj.mean_radiant_temperature, HourlyContinuousCollection)
    assert len(solarcal_obj.mean_radiant_temperature.values) == calc_length
    assert solarcal_obj.mean_radiant_temperature[12] == pytest.approx(42.997806, rel=1e-3)


def test_init_horizontal_ref_solarcal_collection():
    """Test the initialization of the HorizontalRefSolarCal collection."""
    calc_length = 24
    irr_header = Header(Irradiance(), 'W/m2', AnalysisPeriod(end_month=1, end_day=1))
    dir_norm = HourlyContinuousCollection(irr_header, [300] * calc_length)
    diff_horiz = HourlyContinuousCollection(irr_header, [100] * calc_length)
    ref_horiz = HourlyContinuousCollection(irr_header, [100] * calc_length)
    solarcal_obj = HorizontalRefSolarCal(Location(), dir_norm, diff_horiz, ref_horiz, 24)

    assert solarcal_obj.comfort_model == 'Horizontal Reflected SolarCal'
    assert solarcal_obj.calc_length == calc_length
    str(solarcal_obj)  # test that the string representation is ok

    assert isinstance(solarcal_obj.direct_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.direct_horizontal_solar.values) == calc_length
    assert solarcal_obj.direct_horizontal_solar[12] == 300
    assert isinstance(solarcal_obj.diffuse_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.diffuse_horizontal_solar.values) == calc_length
    assert solarcal_obj.diffuse_horizontal_solar[12] == 100
    assert isinstance(solarcal_obj.reflected_horizontal_solar, HourlyContinuousCollection)
    assert len(solarcal_obj.reflected_horizontal_solar.values) == calc_length
    assert solarcal_obj.reflected_horizontal_solar[12] == 100

    assert isinstance(solarcal_obj.effective_radiant_field, HourlyContinuousCollection)
    assert len(solarcal_obj.effective_radiant_field.values) == calc_length
    assert solarcal_obj.effective_radiant_field[12] == pytest.approx(79.35027, rel=1e-3)
    assert isinstance(solarcal_obj.mrt_delta, HourlyContinuousCollection)
    assert len(solarcal_obj.mrt_delta.values) == calc_length
    assert solarcal_obj.mrt_delta[12] == pytest.approx(18.20503, rel=1e-3)
    assert isinstance(solarcal_obj.mean_radiant_temperature, HourlyContinuousCollection)
    assert len(solarcal_obj.mean_radiant_temperature.values) == calc_length
    assert solarcal_obj.mean_radiant_temperature[12] == pytest.approx(42.20503, rel=1e-3)
