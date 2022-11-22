# coding utf-8
import pytest

from ladybug.datatype.temperature import Temperature
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.epw import EPW

from ladybug_comfort.pet import physiologic_equivalent_temperature
from ladybug_comfort.parameter.pet import PETParameter
from ladybug_comfort.collection.pet import PET


def test_pet():
    """Test the physiologic_equivalent_temperature function"""
    # sample input data for the PET model
    rh = 50  # relative humidity [%]
    vel = 1  # air velocity [m/s]
    met = 2.3  # metabolic rate [met]
    clo = 1  # clothing level [clo]

    result = physiologic_equivalent_temperature(-20, 10, vel, rh, met, clo)
    assert result['pet'] == pytest.approx(-16.9, rel=1e-2)
    assert result['t_core'] == pytest.approx(22.8, rel=1e-2)
    assert result['t_skin'] == pytest.approx(4.04, rel=1e-2)
    assert result['t_clo'] == pytest.approx(-7.78, rel=1e-2)

    result = physiologic_equivalent_temperature(20, 30, vel, rh, met, clo)
    assert result['pet'] == pytest.approx(22.3, rel=1e-2)
    assert result['t_core'] == pytest.approx(36.88, rel=1e-2)
    assert result['t_skin'] == pytest.approx(28.8, rel=1e-2)
    assert result['t_clo'] == pytest.approx(24.6, rel=1e-2)

    result = physiologic_equivalent_temperature(30, 60, vel, rh, met, clo)
    assert result['pet'] == pytest.approx(42.5, rel=1e-2)
    assert result['t_core'] == pytest.approx(39.28, rel=1e-2)
    assert result['t_skin'] == pytest.approx(38.18, rel=1e-2)
    assert result['t_clo'] == pytest.approx(40.29, rel=1e-2)


def test_pet_parameter():
    """Test PETParameter."""
    age = 36
    sex = 1
    height = 1.55
    body_mass = 45
    posture = 'standing'
    humid_acclimated = True

    pet_comf = PETParameter(
        age, sex, height, body_mass, posture, humid_acclimated)

    assert pet_comf.age == age
    assert pet_comf.sex == sex
    assert pet_comf.height == height
    assert pet_comf.body_mass == body_mass
    assert pet_comf.posture == posture
    assert pet_comf.humid_acclimated == humid_acclimated


def test_pet_parameter_invalid():
    """Test PETParameter for invalid inputs."""
    age = -2
    sex = 2
    height = 10
    body_mass = 1000
    posture = 'jazz hands'

    with pytest.raises(AssertionError):
        PETParameter(age=age)
    with pytest.raises(AssertionError):
        PETParameter(sex=sex)
    with pytest.raises(AssertionError):
        PETParameter(height=height)
    with pytest.raises(AssertionError):
        PETParameter(body_mass=body_mass)
    with pytest.raises(AssertionError):
        PETParameter(posture=posture)


def test_pet_parameter_to_from_dict():
    """Test PETParameter to/from dict."""
    age = 36
    sex = 1
    height = 1.55
    body_mass = 45
    posture = 'standing'
    humid_acclimated = True

    pet_comf = PETParameter(
        age, sex, height, body_mass, posture, humid_acclimated)
    pet_comf_dict = pet_comf.to_dict()
    new_pet_comf = PETParameter.from_dict(pet_comf_dict)

    assert new_pet_comf.to_dict() == pet_comf_dict
    assert new_pet_comf.age == age
    assert new_pet_comf.sex == sex
    assert new_pet_comf.height == height
    assert new_pet_comf.body_mass == body_mass
    assert new_pet_comf.posture == posture
    assert new_pet_comf.humid_acclimated == humid_acclimated


def test_pet_parameter_to_from_str():
    """Test PETParameter to/from str."""
    age = 36
    sex = 1
    height = 1.55
    body_mass = 45
    posture = 'standing'
    humid_acclimated = True

    pet_comf = PETParameter(
        age, sex, height, body_mass, posture, humid_acclimated)
    new_pet_comf = PETParameter.from_string(str(pet_comf))

    assert new_pet_comf.age == age
    assert new_pet_comf.sex == sex
    assert new_pet_comf.height == height
    assert new_pet_comf.body_mass == body_mass
    assert new_pet_comf.posture == posture
    assert new_pet_comf.humid_acclimated == humid_acclimated


def test_init_pet_collection():
    """Test the initialization of the PET collection and basic outputs."""
    calc_length = 24
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
    pet_obj = PET(air_temp, 50)

    assert pet_obj.comfort_model == 'Physiological Equivalent Temperature'
    assert pet_obj.calc_length == calc_length
    str(pet_obj)  # test that the string representation is ok

    assert isinstance(pet_obj.air_temperature, HourlyContinuousCollection)
    assert len(pet_obj.air_temperature.values) == calc_length
    assert pet_obj.air_temperature[0] == 24
    assert isinstance(pet_obj.rel_humidity, HourlyContinuousCollection)
    assert len(pet_obj.rel_humidity.values) == calc_length
    assert pet_obj.rel_humidity[0] == 50

    assert isinstance(
        pet_obj.physiologic_equivalent_temperature, HourlyContinuousCollection)
    assert len(pet_obj.physiologic_equivalent_temperature.values) == calc_length

    assert isinstance(pet_obj.core_body_temperature, HourlyContinuousCollection)
    assert len(pet_obj.core_body_temperature.values) == calc_length

    assert isinstance(pet_obj.skin_temperature, HourlyContinuousCollection)
    assert len(pet_obj.skin_temperature.values) == calc_length

    assert isinstance(pet_obj.clothing_temperature, HourlyContinuousCollection)
    assert len(pet_obj.clothing_temperature.values) == calc_length

    assert isinstance(pet_obj.operative_temperature, HourlyContinuousCollection)
    assert len(pet_obj.operative_temperature.values) == calc_length


def test_pet_collection_defaults():
    """Test the default inputs assigned to the PET collection."""
    calc_length = 24
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
    pet_obj = PET(air_temp, 50)

    assert isinstance(pet_obj.rad_temperature, HourlyContinuousCollection)
    assert len(pet_obj.rad_temperature.values) == calc_length
    assert pet_obj.rad_temperature[0] == pet_obj.air_temperature[0]

    assert isinstance(pet_obj.air_speed, HourlyContinuousCollection)
    assert len(pet_obj.air_speed.values) == calc_length
    assert pet_obj.air_speed[0] == 0.1

    assert isinstance(pet_obj.met_rate, HourlyContinuousCollection)
    assert len(pet_obj.met_rate.values) == calc_length
    assert pet_obj.met_rate[0] == 2.4

    assert isinstance(pet_obj.clo_value, HourlyContinuousCollection)
    assert len(pet_obj.clo_value.values) == calc_length
    assert pet_obj.clo_value[0] == 0.7

    assert isinstance(pet_obj.barometric_pressure, HourlyContinuousCollection)
    assert len(pet_obj.barometric_pressure.values) == calc_length
    assert pet_obj.barometric_pressure[0] == 101325

    assert isinstance(pet_obj.body_parameter, PETParameter)
    default_par = PETParameter()
    assert pet_obj.body_parameter.age == default_par.age
    assert pet_obj.body_parameter.sex == default_par.sex
    assert pet_obj.body_parameter.height == default_par.height
    assert pet_obj.body_parameter.body_mass == default_par.body_mass
    assert pet_obj.body_parameter.posture == default_par.posture


def test_pet_collection_comfort_outputs():
    """Test the is_comfortable and thermal_condition outputs of the PET collection."""
    calc_length = 24
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, range(12, 12 + calc_length))
    pet_obj = PET(air_temp, 50)

    assert isinstance(pet_obj.is_comfortable, HourlyContinuousCollection)
    assert len(pet_obj.is_comfortable.values) == calc_length
    assert pet_obj.is_comfortable[0] == 0
    assert pet_obj.is_comfortable[5] == 1
    assert pet_obj.is_comfortable[10] == 0

    assert isinstance(pet_obj.thermal_condition, HourlyContinuousCollection)
    assert len(pet_obj.thermal_condition.values) == calc_length
    assert pet_obj.thermal_condition[0] == -1
    assert pet_obj.thermal_condition[5] == 0
    assert pet_obj.thermal_condition[10] == 1

    assert isinstance(pet_obj.pet_category, HourlyContinuousCollection)
    assert len(pet_obj.pet_category.values) == calc_length
    assert pet_obj.pet_category[0] < 0
    assert pet_obj.pet_category[5] == 0
    assert pet_obj.pet_category[10] > 0

    assert isinstance(pet_obj.core_temperature_category, HourlyContinuousCollection)
    assert len(pet_obj.core_temperature_category.values) == calc_length
    assert pet_obj.core_temperature_category[0] == 0
    assert pet_obj.core_temperature_category[-1] == 2


def test_pet_collection_comfort_percent_outputs():
    """Test the percent outputs of the PET collection."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    pet_obj = PET(epw.dry_bulb_temperature, epw.relative_humidity,
                  met_rate=2.4, clo_value=1)

    print(pet_obj.percent_neutral)
    print(pet_obj.percent_hot)
    print(pet_obj.percent_cold)

    assert 11 < pet_obj.percent_neutral < 13
    assert 26 < pet_obj.percent_hot < 28
    assert 60 < pet_obj.percent_cold < 62
