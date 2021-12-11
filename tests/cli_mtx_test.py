"""Test cli mtx module."""
from click.testing import CliRunner
import json
import os

from ladybug.futil import nukedir

from ladybug_comfort.cli.mtx import pmv_mtx, adaptive_mtx, utci_mtx


# global files object used by all of the tests
air_path = './tests/mtx/temperature.csv'
rh_path = './tests/mtx/rel_humidity.csv'
long_mrt_path = './tests/mtx/long_mrt.csv'
short_mrt_path = './tests/mtx/short_dmrt.csv'
prevailing_path = './tests/mtx/prevailing.csv'
air_speed_path = './tests/mtx/air_speed.json'


def test_pmv_mtx():
    runner = CliRunner()
    res_folder = './tests/mtx/pmv_mtx'

    base_cmd = [air_path, rh_path, '--air-speed-json', air_speed_path]
    base_cmd.extend(['-rm', long_mrt_path, '-dm', short_mrt_path])
    base_cmd.extend(['--folder', res_folder])

    result = runner.invoke(pmv_mtx, base_cmd)

    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert os.path.isfile(out_files['temperature'])
    assert os.path.isfile(out_files['condition'])
    assert os.path.isfile(out_files['condition_intensity'])

    nukedir(res_folder, True)


def test_adaptive_mtx():
    runner = CliRunner()
    res_folder = './tests/mtx/adaptive_mtx'

    base_cmd = [air_path, prevailing_path, '--air-speed-json', air_speed_path]
    base_cmd.extend(['-rm', long_mrt_path, '-dm', short_mrt_path])
    base_cmd.extend(['--folder', res_folder])

    result = runner.invoke(adaptive_mtx, base_cmd)

    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert os.path.isfile(out_files['temperature'])
    assert os.path.isfile(out_files['condition'])
    assert os.path.isfile(out_files['condition_intensity'])

    nukedir(res_folder, True)


def test_utci_mtx():
    runner = CliRunner()
    res_folder = './tests/mtx/utci_mtx'

    base_cmd = [air_path, rh_path, '--wind-speed-json', air_speed_path]
    base_cmd.extend(['-rm', long_mrt_path, '-dm', short_mrt_path])
    base_cmd.extend(['--folder', res_folder])

    result = runner.invoke(utci_mtx, base_cmd)

    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert os.path.isfile(out_files['temperature'])
    assert os.path.isfile(out_files['condition'])
    assert os.path.isfile(out_files['condition_intensity'])

    nukedir(res_folder, True)
