from ladybug_geometry.geometry2d import Point2D, LineSegment2D, Polyline2D, \
    Polygon2D, Mesh2D

from ladybug.legend import Legend, LegendParameters
from ladybug.graphic import GraphicContainer
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.epw import EPW
from ladybug.sql import SQLiteResult

from ladybug_comfort.parameter.adaptive import AdaptiveParameter
from ladybug_comfort.chart.adaptive import AdaptiveChart


def test_adaptive_chart_init():
    """Test the initialization of AdaptiveChart and basic properties."""
    path = './tests/epw/boston.epw'
    input_sql = './tests/sql/eplusout.sql'
    epw_obj = EPW(path)
    sql_obj = SQLiteResult(input_sql)
    op_temps = sql_obj.data_collections_by_output_name('Zone Operative Temperature')

    adapt_chart = AdaptiveChart(
        epw_obj.dry_bulb_temperature, op_temps[0], 1.2,
        AdaptiveParameter(avg_month_or_running_mean=False, cold_prevail_temp_limit=15))

    str(adapt_chart)  # test the string representation
    assert isinstance(adapt_chart.prevailing_outdoor_temperature, HourlyContinuousCollection)
    assert isinstance(adapt_chart.operative_temperature, HourlyContinuousCollection)
    assert isinstance(adapt_chart.legend_parameters, LegendParameters)
    assert adapt_chart.base_point == Point2D(0, 0)
    assert adapt_chart.x_dim == 1
    assert adapt_chart.y_dim == 1
    assert adapt_chart.min_prevailing == 10
    assert adapt_chart.max_prevailing == 33
    assert adapt_chart.min_operative == 14
    assert adapt_chart.max_operative == 40
    assert not adapt_chart.use_ip

    mesh = adapt_chart.colored_mesh
    assert isinstance(mesh, Mesh2D)
    assert len(mesh.faces) > 1
    data_points = adapt_chart.data_points
    assert all(isinstance(pt, Point2D) for pt in data_points)
    hour_values = adapt_chart.hour_values
    assert all(isinstance(pt, (float, int)) for pt in hour_values)
    time_matrix = adapt_chart.time_matrix
    assert all(isinstance(pt, tuple) for pt in time_matrix)

    border = adapt_chart.chart_border
    assert isinstance(border, Polygon2D)
    assert len(border.segments) == 4
    assert isinstance(adapt_chart.neutral_polyline, (LineSegment2D, Polyline2D))
    assert isinstance(adapt_chart.comfort_polygon, Polygon2D)
    assert len(adapt_chart.comfort_polygon) == 7

    temp_txt = adapt_chart.prevailing_labels
    assert all(isinstance(txt, str) for txt in temp_txt)
    temp_lines = adapt_chart.prevailing_lines
    temp_pts = adapt_chart.prevailing_label_points
    assert len(temp_lines) == len(temp_txt) == len(temp_pts)
    assert all(isinstance(line, LineSegment2D) for line in temp_lines)
    assert all(isinstance(pt, Point2D) for pt in temp_pts)

    operative_txt = adapt_chart.operative_labels
    assert all(isinstance(txt, str) for txt in operative_txt)
    operative_lines = adapt_chart.operative_lines
    operative_pts = adapt_chart.operative_label_points
    assert len(operative_txt) == len(operative_pts)
    assert all(isinstance(line, LineSegment2D) for line in operative_lines)
    assert all(isinstance(pt, Point2D) for pt in operative_pts)

    assert isinstance(adapt_chart.legend, Legend)
    assert isinstance(adapt_chart.container, GraphicContainer)

    assert isinstance(adapt_chart.title_text, str)
    assert isinstance(adapt_chart.y_axis_text, str)
    assert isinstance(adapt_chart.x_axis_text, str)
    assert isinstance(adapt_chart.title_location, Point2D)
    assert isinstance(adapt_chart.x_axis_location, Point2D)
    assert isinstance(adapt_chart.y_axis_location, Point2D)
