
from ladybug_comfort.chart.polygonpmv import PolygonPMV
from ladybug_comfort.parameter.pmv import PMVParameter

from ladybug.epw import EPW
from ladybug.psychchart import PsychrometricChart
from ladybug.datacollection import HourlyContinuousCollection
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.polyline import Polyline2D


def test_polygonpmv_init():
    """Test the initialization of PolygonPMV and basic properties."""
    path = './tests/epw/chicago.epw'
    psych_chart = PsychrometricChart.from_epw(path)
    poly_obj = PolygonPMV(psych_chart, clo_value=[0.5, 1.0])

    str(poly_obj)  # test the sting representation

    assert poly_obj.psychrometric_chart is psych_chart
    assert poly_obj.rad_temperature == (None, None)
    assert poly_obj.air_speed == (0.1, 0.1)
    assert poly_obj.met_rate == (1.1, 1.1)
    assert poly_obj.clo_value == (0.5, 1.0)
    assert poly_obj.external_work == (0, 0)
    assert poly_obj.comfort_parameter.ppd_comfort_thresh == 10
    assert poly_obj.comfort_parameter.humid_ratio_upper == 1
    assert poly_obj.comfort_parameter.humid_ratio_lower == 0
    assert poly_obj.polygon_count == 2
    assert len(poly_obj.left_comfort_lines) == 2
    assert all(isinstance(pline, Polyline2D) for pline in poly_obj.left_comfort_lines)
    assert len(poly_obj.right_comfort_lines) == 2
    assert all(isinstance(pline, Polyline2D) for pline in poly_obj.right_comfort_lines)
    assert isinstance(poly_obj.left_comfort_line, Polyline2D)
    assert isinstance(poly_obj.right_comfort_line, Polyline2D)
    assert len(poly_obj.comfort_polygons) == 2
    assert len(poly_obj.merged_comfort_polygon) == 4
    assert isinstance(poly_obj.merged_comfort_polygon[0], Polyline2D)
    assert isinstance(poly_obj.merged_comfort_polygon[1], LineSegment2D)
    assert isinstance(poly_obj.merged_comfort_polygon[2], Polyline2D)
    assert isinstance(poly_obj.merged_comfort_polygon[3], Polyline2D)
    assert len(poly_obj.comfort_values) == 2
    assert all(isinstance(dat, HourlyContinuousCollection)
               for dat in poly_obj.comfort_data)
    assert len(poly_obj.merged_comfort_values) == 8760
    assert isinstance(poly_obj.merged_comfort_data, HourlyContinuousCollection)
    assert not poly_obj.is_comfort_too_hot
    assert not poly_obj.is_comfort_too_cold


def test_evaporative_cooling_polygon():
    """Test the evaporative_cooling_polygon method."""
    # test the polygon with the default comfort settings
    psych_chart = PsychrometricChart(20, 50)
    poly_obj = PolygonPMV(psych_chart)
    evap_poly = poly_obj.evaporative_cooling_polygon()
    val_list = poly_obj.evaluate_polygon(evap_poly)
    assert val_list == [0]

    # test the polygon with custom comfort settings
    psych_chart = PsychrometricChart(35, 10)
    pmv_par = PMVParameter(humid_ratio_upper=0.008, humid_ratio_lower=0.005)
    poly_obj = PolygonPMV(psych_chart, comfort_parameter=pmv_par)
    evap_poly = poly_obj.evaporative_cooling_polygon()
    val_list = poly_obj.evaluate_polygon(evap_poly)
    assert val_list == [1]


def test_fan_use_polygon():
    """Test the fan_use_polygon method."""
    # test the polygon with the default comfort settings
    psych_chart = PsychrometricChart(20, 50)
    poly_obj = PolygonPMV(psych_chart)
    fan_poly = poly_obj.fan_use_polygon()
    val_list = poly_obj.evaluate_polygon(fan_poly)
    assert val_list == [0]

    # test the polygon with custom comfort settings
    psych_chart = PsychrometricChart(30, 30)
    pmv_par = PMVParameter(humid_ratio_upper=0.008, humid_ratio_lower=0.005)
    poly_obj = PolygonPMV(psych_chart, comfort_parameter=pmv_par)
    fan_poly = poly_obj.fan_use_polygon(1.5)
    val_list = poly_obj.evaluate_polygon(fan_poly)
    assert val_list == [1]


def test_night_flush_polygon():
    """Test the night_flush_polygon method."""
    # test the polygon with the default comfort settings
    path = './tests/epw/chicago.epw'
    epw = EPW(path)
    psych_chart = PsychrometricChart(epw.dry_bulb_temperature, epw.relative_humidity)
    poly_obj = PolygonPMV(psych_chart)
    nf_poly = poly_obj.night_flush_polygon()
    val_list = poly_obj.evaluate_night_flush_polygon(nf_poly, epw.dry_bulb_temperature)
    assert 0 < sum(val_list) < 8760

    # test the polygon with custom comfort settings
    psych_chart = PsychrometricChart(30, 30, max_temperature=40)
    pmv_par = PMVParameter(humid_ratio_upper=0.008, humid_ratio_lower=0.005)
    poly_obj = PolygonPMV(psych_chart, comfort_parameter=pmv_par)
    nf_poly = poly_obj.night_flush_polygon(16)
    val_list = poly_obj.evaluate_night_flush_polygon(nf_poly, [20])
    assert val_list == [1]


def test_internal_heat_polygon():
    """Test the internal_heat_polygon method."""
    # test the polygon with the default comfort settings
    psych_chart = PsychrometricChart(25, 50)
    poly_obj = PolygonPMV(psych_chart)
    inht_poly = poly_obj.internal_heat_polygon()
    val_list = poly_obj.evaluate_polygon(inht_poly)
    assert val_list == [0]

    # test the polygon with custom comfort settings
    psych_chart = PsychrometricChart(15, 50)
    pmv_par = PMVParameter(humid_ratio_upper=0.008, humid_ratio_lower=0.005)
    poly_obj = PolygonPMV(psych_chart, comfort_parameter=pmv_par)
    inht_poly = poly_obj.internal_heat_polygon()
    val_list = poly_obj.evaluate_polygon(inht_poly)
    assert val_list == [1]


def test_passive_solar_polygon():
    """Test the passive_solar_polygon method."""
    # test the polygon with the default comfort settings
    path = './tests/epw/chicago.epw'
    epw = EPW(path)
    psych_chart = PsychrometricChart(epw.dry_bulb_temperature, epw.relative_humidity)
    poly_obj = PolygonPMV(psych_chart)
    sol_vals, delta = poly_obj.evaluate_passive_solar(epw.global_horizontal_radiation)
    sol_poly = poly_obj.passive_solar_polygon(delta)
    sol_poly = poly_obj.passive_solar_polygon(delta)
    assert len(sol_poly) == 4
    assert 0 < sum(sol_vals) < 8760

    # test the polygon with custom comfort settings
    psych_chart = PsychrometricChart(15, 30, max_temperature=40)
    pmv_par = PMVParameter(humid_ratio_upper=0.008, humid_ratio_lower=0.005)
    poly_obj = PolygonPMV(psych_chart, comfort_parameter=pmv_par)
    sol_vals, delta = poly_obj.evaluate_passive_solar([200])
    sol_poly = poly_obj.passive_solar_polygon(delta)
    assert sol_vals == [1]

    # test the polygon with custom comfort settings
    psych_chart = PsychrometricChart(10, 30, max_temperature=40)
    pmv_par = PMVParameter(humid_ratio_upper=0.014, humid_ratio_lower=0.005)
    poly_obj = PolygonPMV(psych_chart, comfort_parameter=pmv_par)
    bal = 12.8
    sol_vals, delta = poly_obj.evaluate_passive_solar([200], balance_temperature=bal)
    sol_poly = poly_obj.passive_solar_polygon(delta, bal)
    assert sol_vals == [1]
