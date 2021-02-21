"""Test cli sql module."""
from click.testing import CliRunner
import json

from ladybug.datacollection import HourlyContinuousCollection
from ladybug_comfort.parameter.adaptive import AdaptiveParameter
from ladybug_comfort.cli.sql import pmv_by_room, adaptive_by_room


def test_pmv_by_room():
    runner = CliRunner()
    input_sql = './tests/sql/eplusout.sql'

    result = runner.invoke(pmv_by_room, [input_sql])
    assert result.exit_code == 0
    data_dicts = json.loads(result.output)
    pmv_data = [HourlyContinuousCollection.from_dict(dat) for dat in data_dicts]
    assert len(pmv_data) == 2
    assert len(pmv_data[0]) == 8760


def test_adaptive_by_room():
    runner = CliRunner()
    input_sql = './tests/sql/eplusout.sql'
    input_epw = './tests/epw/chicago.epw'

    result = runner.invoke(adaptive_by_room, [input_sql, input_epw, '-v', '0.65'])
    assert result.exit_code == 0
    data_dicts = json.loads(result.output)
    ad_data = [HourlyContinuousCollection.from_dict(dat) for dat in data_dicts]
    assert len(ad_data) == 2
    assert len(ad_data[0]) == 8760


def test_adaptive_by_room_custom():
    runner = CliRunner()
    input_sql = './tests/sql/eplusout.sql'
    input_epw = './tests/epw/chicago.epw'

    air_speed = [0.65] * 8760
    air_speed = json.dumps(air_speed)
    comf_par = AdaptiveParameter(False)
    comf_par.set_neutral_offset_from_comfort_class(1)

    result = runner.invoke(
        adaptive_by_room, [input_sql, input_epw, '-v', air_speed, '-cp', str(comf_par)])
    assert result.exit_code == 0
    data_dicts = json.loads(result.output)
    ad_data = [HourlyContinuousCollection.from_dict(dat) for dat in data_dicts]
    assert len(ad_data) == 2
    assert len(ad_data[0]) == 8760
