# coding utf-8
from ladybug_comfort.map.mrt import shortwave_mrt_map
from ladybug_comfort.map._enclosure import _parse_enclosure_info

from ladybug.datacollection import HourlyContinuousCollection
from ladybug.sql import SQLiteResult
from ladybug.epw import EPW


# global files object used by all of the tests
sun_up_path = './tests/map/results/total/sun-up-hours.txt'
total_ill_path = './tests/map/results/total/TestRoom_1.ill'
direct_ill_path = './tests/map/results/direct/TestRoom_1.ill'
ref_ill_path = './tests/map/results/total/TestRoom_1_ref.ill'
enclosure_path = './tests/map/TestRoom_1_enclosure.json'
sql_path = './tests/sql/eplusout.sql'
sql = SQLiteResult(sql_path)
epw_path = './tests/epw/boston.epw'
epw = EPW(epw_path)


def test_shortwave_mrt_map():
    """Test the shortwave_mrt_map method."""
    location = epw.location
    l_mrt_data = sql.data_collections_by_output_name('Zone Mean Radiant Temperature')
    l_mrt_data = [l_mrt_data[0]] * 4

    mrt_map_data = shortwave_mrt_map(
        location, l_mrt_data, sun_up_path, total_ill_path, direct_ill_path, ref_ill_path)

    assert len(mrt_map_data) == 4
    for mrt_dat in mrt_map_data:
        assert isinstance(mrt_dat, HourlyContinuousCollection)
        assert len(mrt_dat) == 8760


def test_parse_enclosure_info():
    """Test the _parse_enclosure_info method."""
    pt_air_temps, pt_rad_temps, pt_humids, pt_speeds, a_period = _parse_enclosure_info(
        enclosure_path, sql_path, epw, include_humidity=True)

    assert len(pt_air_temps) == 4
    for air_dat in pt_air_temps:
        assert isinstance(air_dat, HourlyContinuousCollection)
        assert len(air_dat) == 8760
    assert len(pt_rad_temps) == 4
    for mrt_dat in pt_rad_temps:
        assert isinstance(mrt_dat, HourlyContinuousCollection)
        assert len(mrt_dat) == 8760
    assert len(pt_humids) == 4
    for hum_dat in pt_humids:
        assert isinstance(hum_dat, HourlyContinuousCollection)
        assert len(hum_dat) == 8760
    assert len(pt_speeds) == 4
