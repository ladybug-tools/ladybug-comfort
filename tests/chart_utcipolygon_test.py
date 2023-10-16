
from ladybug_comfort.chart.polygonutci import PolygonUTCI
from ladybug_comfort.parameter.utci import UTCIParameter

from ladybug.psychchart import PsychrometricChart
from ladybug.datacollection import HourlyContinuousCollection
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.polyline import Polyline2D


def test_polygon_utci_init():
    """Test the initialization of PolygonUTCI and basic properties."""
    path = './tests/epw/chicago.epw'
    psych_chart = PsychrometricChart.from_epw(path)
    poly_obj = PolygonUTCI(psych_chart, wind_speed=[1.0, 10.0])

    str(poly_obj)  # test the sting representation

    assert poly_obj.psychrometric_chart is psych_chart
    assert poly_obj.rad_temperature == (None, None)
    assert poly_obj.wind_speed == (1.0, 10.0)
    assert poly_obj.comfort_parameter.cold_thresh == 9
    assert poly_obj.comfort_parameter.heat_thresh == 26
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