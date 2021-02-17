"""Test cli epw module."""
from click.testing import CliRunner
import json

from ladybug.datacollection import HourlyContinuousCollection
from ladybug_comfort.cli.epw import utci, set_


def test_utci():
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
    runner = CliRunner()
    input_epw = './tests/epw/chicago.epw'

    result = runner.invoke(
        set_, [input_epw, '--exclude-wind', '--exclude-sun', '--json'])
    assert result.exit_code == 0
    data_dict = json.loads(result.output)
    set_data = HourlyContinuousCollection.from_dict(data_dict)
    assert len(set_data) == 8760
