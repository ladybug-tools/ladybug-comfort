"""Test cli map module."""
from click.testing import CliRunner
import json
import os

from ladybug.futil import nukedir
from ladybug.header import Header
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.datatype.temperature import OperativeTemperature, \
    StandardEffectiveTemperature, UniversalThermalClimateIndex
from ladybug.datatype.thermalcondition import PredictedMeanVote, \
    ThermalCondition, ThermalConditionElevenPoint
from ladybug.datatype.temperaturedelta import OperativeTemperatureDelta

from ladybug_comfort.cli.map import pmv, adaptive, utci, map_result_info, tcp, \
    shortwave_mrt, longwave_mrt, air_temperature

# global files object used by all of the tests
sql_path = './tests/sql/eplusout.sql'
sql_path2 = './tests/sql/eplusout2.sql'
enclosure_path = './tests/map/TestRoom_1_enclosure.json'
enclosure_path2 = './tests/map/TestRoom_1_enclosure2.json'
modifiers_path = './tests/map/scene.mod'
view_factors_path = './tests/map/view_factor.csv'
epw_path = './tests/epw/boston.epw'
sun_up_path = './tests/map/results/total/sun-up-hours.txt'
total_ill_path = './tests/map/results/total/TestRoom_1.ill'
direct_ill_path = './tests/map/results/direct/TestRoom_1.ill'
ref_ill_path = './tests/map/results/total/TestRoom_1_ref.ill'


def test_pmv_map():
    runner = CliRunner()
    res_folder = './tests/map/pmv_map_results'
    run_period = AnalysisPeriod(1, 2, 0, 1, 2, 23)

    base_cmd = [sql_path, enclosure_path, epw_path]
    base_cmd.extend(['-tr', total_ill_path, '-dr', direct_ill_path, '-rr', ref_ill_path])
    base_cmd.extend(['-sh', sun_up_path])
    base_cmd.extend(['-rp', str(run_period)])
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


def test_shortwave_mrt_map():
    runner = CliRunner()
    res_file = './tests/map/shortwave.csv'

    base_cmd = [epw_path, total_ill_path, direct_ill_path, ref_ill_path, sun_up_path]
    base_cmd.extend(['--output-file', res_file])

    result = runner.invoke(shortwave_mrt, base_cmd)

    assert result.exit_code == 0
    assert os.path.isfile(res_file)
    os.remove(res_file)


def test_longwave_mrt_map():
    runner = CliRunner()
    res_file = './tests/map/longwave.csv'

    base_cmd = [sql_path2, view_factors_path, modifiers_path, enclosure_path2, epw_path]
    base_cmd.extend(['--run-period', '7/6 to 7/12 between 0 and 23 @1'])
    base_cmd.extend(['--output-file', res_file])

    result = runner.invoke(longwave_mrt, base_cmd)

    assert result.exit_code == 0
    assert os.path.isfile(res_file)
    os.remove(res_file)


def test_air_map():
    runner = CliRunner()
    res_file = './tests/map/air.csv'

    base_cmd = [sql_path2, enclosure_path2, epw_path]
    base_cmd.extend(['--run-period', '7/6 to 7/12 between 0 and 23 @1'])
    base_cmd.extend(['--output-file', res_file])

    result = runner.invoke(air_temperature, base_cmd)

    assert result.exit_code == 0
    assert os.path.isfile(res_file)
    os.remove(res_file)


def test_map_result_info():
    runner = CliRunner()
    a_per = AnalysisPeriod()
    a_per_sub = AnalysisPeriod(6, 21, 0, 9, 21, 23)

    cmd = ['pmv', '--run-period', '', '--qualifier', 'write-op-map']
    result = runner.invoke(map_result_info, cmd)
    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert out_files['temperature'] == \
        Header(OperativeTemperature(), 'C', a_per).to_dict()
    assert out_files['condition'] == \
        Header(ThermalCondition(), 'condition', a_per).to_dict()
    assert out_files['condition_intensity'] == \
        Header(PredictedMeanVote(), 'PMV', a_per).to_dict()

    cmd = ['pmv', '--run-period', str(a_per_sub), '--qualifier', 'write-set-map']
    result = runner.invoke(map_result_info, cmd)
    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert out_files['temperature'] == \
        Header(StandardEffectiveTemperature(), 'C', a_per_sub).to_dict()

    cmd = ['pmv']
    result = runner.invoke(map_result_info, cmd)
    assert result.exit_code == 0

    cmd = ['adaptive', '--run-period', '', '--qualifier', '']
    result = runner.invoke(map_result_info, cmd)
    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert out_files['temperature'] == \
        Header(OperativeTemperature(), 'C', a_per).to_dict()
    assert out_files['condition_intensity'] == \
        Header(OperativeTemperatureDelta(), 'dC', a_per).to_dict()

    cmd = ['utci']
    result = runner.invoke(map_result_info, cmd)
    assert result.exit_code == 0
    out_files = json.loads(result.output)
    assert out_files['temperature'] == \
        Header(UniversalThermalClimateIndex(), 'C', a_per).to_dict()
    assert out_files['condition_intensity'] == \
        Header(ThermalConditionElevenPoint(), 'condition', a_per).to_dict()


def test_tcp():
    runner = CliRunner()
    condition_path = './tests/map/map_results/condition.csv'
    occ_sch_path = './tests/map/occ_schedules.json'
    res_folder = './tests/map/metrics'

    base_cmd = [condition_path, enclosure_path, '--occ-schedule-json', occ_sch_path]
    base_cmd.extend(['--folder', res_folder])
    result = runner.invoke(tcp, base_cmd)

    assert result.exit_code == 0
    out_files = json.loads(result.output)
    for fp in out_files:
        assert os.path.isfile(fp)
    nukedir(res_folder, True)

    cmds = [condition_path, enclosure_path, '--folder', res_folder]
    result = runner.invoke(tcp, cmds)

    assert result.exit_code == 0
    out_files = json.loads(result.output)
    for fp in out_files:
        assert os.path.isfile(fp)
    nukedir(res_folder, True)
