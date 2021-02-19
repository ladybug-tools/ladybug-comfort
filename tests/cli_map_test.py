"""Test cli sql module."""
from click.testing import CliRunner
import json
import os

from ladybug.datacollection import HourlyContinuousCollection
from ladybug.futil import nukedir

from ladybug_comfort.cli.map import pmv, adaptive, utci

# global files object used by all of the tests
sql_path = './tests/sql/eplusout.sql'
enclosure_path = './tests/map/TestRoom_1_enclosure.json'
epw_path = './tests/epw/boston.epw'
sun_up_path = './tests/map/results/total/sun-up-hours.txt'
total_ill_path = './tests/map/results/total/TestRoom_1.ill'
direct_ill_path = './tests/map/results/direct/TestRoom_1.ill'
ref_ill_path = './tests/map/results/total/TestRoom_1_ref.ill'
enclosure_path = './tests/map/TestRoom_1_enclosure.json'
run_period_path = './tests/map/run_period.json'


def test_pmv_map():
    runner = CliRunner()
    res_folder = './tests/map/pmv_map_results'

    base_cmd = [sql_path, enclosure_path, epw_path]
    base_cmd.extend(['-tr', total_ill_path, '-dr', direct_ill_path, '-rr', ref_ill_path])
    base_cmd.extend(['-sh', sun_up_path])
    base_cmd.extend(['-rp', run_period_path])
    base_cmd.extend(['--folder', res_folder])

    result = runner.invoke(pmv, base_cmd)

    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert os.path.isfile(out_files['temperature'])
    assert os.path.isfile(out_files['condition'])
    assert os.path.isfile(out_files['condition_intensity'])

    nukedir(res_folder, True)


def test_adaptive_map():
    runner = CliRunner()
    res_folder = './tests/map/adaptive_map_results'

    base_cmd = [sql_path, enclosure_path, epw_path]
    base_cmd.extend(['-tr', total_ill_path, '-dr', direct_ill_path, '-rr', ref_ill_path])
    base_cmd.extend(['-sh', sun_up_path])
    base_cmd.extend(['--folder', res_folder])

    result = runner.invoke(adaptive, base_cmd)

    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert os.path.isfile(out_files['temperature'])
    assert os.path.isfile(out_files['condition'])
    assert os.path.isfile(out_files['condition_intensity'])

    nukedir(res_folder, True)


def test_utci_map():
    runner = CliRunner()
    res_folder = './tests/map/utci_map_results'

    base_cmd = [sql_path, enclosure_path, epw_path]
    base_cmd.extend(['-tr', total_ill_path, '-dr', direct_ill_path, '-rr', ref_ill_path])
    base_cmd.extend(['-sh', sun_up_path])
    base_cmd.extend(['--folder', res_folder])

    result = runner.invoke(utci, base_cmd)

    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert os.path.isfile(out_files['temperature'])
    assert os.path.isfile(out_files['condition'])
    assert os.path.isfile(out_files['condition_intensity'])

    nukedir(res_folder, True)
