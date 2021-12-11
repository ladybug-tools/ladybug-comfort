"""Test cli epw module."""
from click.testing import CliRunner
import json

from ladybug.datacollection import HourlyContinuousCollection
from ladybug_comfort.cli.epw import utci, set_, prevailing, air_speed_json


def test_utci():
    """Test the epw utci command."""
    runner = CliRunner()
    input_epw = './tests/epw/chicago.epw'

    result = runner.invoke(
        utci, [input_epw, '--exclude-wind', '--exclude-sun', '--csv'])
    assert result.exit_code == 0

    result = runner.invoke(
        utci, [input_epw, '--exclude-wind', '--exclude-sun', '--json'])
    assert result.exit_code == 0
    data_dict = json.loads(result.output)
    utci_data = HourlyContinuousCollection.from_dict(data_dict)
    assert len(utci_data) == 8760


def test_set():
    """Test the epw set command."""
    runner = CliRunner()
    input_epw = './tests/epw/chicago.epw'

    result = runner.invoke(
        set_, [input_epw, '--exclude-wind', '--exclude-sun', '--json'])
    assert result.exit_code == 0
    data_dict = json.loads(result.output)
    set_data = HourlyContinuousCollection.from_dict(data_dict)
    assert len(set_data) == 8760


def test_prevailing():
    """Test the epw prevailing command."""
    runner = CliRunner()
    input_epw = './tests/epw/chicago.epw'

    cmds = [input_epw, '--columns']
    cmds.extend(['--run-period', '7/6 to 7/6 between 0 and 23 @1'])

    result = runner.invoke(prevailing, cmds)
    assert result.exit_code == 0
    data_row = result.output.split(',')
    assert len(data_row) == 24


def test_air_speed_json():
    """Test the air-speed-json command."""
    runner = CliRunner()
    input_epw = './tests/epw/chicago.epw'
    input_enclosure = './tests/map/TestRoom_1_enclosure2.json'

    cmds = [input_epw, input_enclosure]
    cmds.extend(['--run-period', '7/6 to 7/6 between 0 and 23 @1'])

    result = runner.invoke(air_speed_json, cmds)
    assert result.exit_code == 0
