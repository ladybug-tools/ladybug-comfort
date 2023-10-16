# coding=utf-8
"""Object for plotting an UTCI comfort polygon on a Psychrometric Chart."""
from __future__ import division

from ladybug_geometry.geometry2d.pointvector import Point2D, Vector2D
from ladybug_geometry.geometry2d.ray import Ray2D
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.polyline import Polyline2D

from ladybug.psychchart import PsychrometricChart
from ladybug.psychrometrics import humid_ratio_from_db_rh
from ladybug._datacollectionbase import BaseCollection
from ladybug.datacollection import HourlyContinuousCollection, \
    HourlyDiscontinuousCollection
from ladybug.datatype.temperature import Temperature
from ladybug.datatype.temperaturedelta import TemperatureDelta
from ladybug.datatype.thermalcondition import ThermalComfort
from ladybug.datatype.generic import GenericType

from ..utci import calc_missing_utci_input
from ..parameter.utci import UTCIParameter


class PolygonUTCI(object):
    """Object to plot an UTCI comfort polygon on a Psychrometric Chart.

    Args:
        psychrometric_chart: A ladybug-core PsychrometricChart object on which the
            UTCI comfort polygon will be plot.
        rad_temperature: A list of numbers for the mean radiant temperature in Celsius.
            If None, a polygon for operative temperature will be plot, assuming that
            radiant temperature and air temperature are the same. (Default: None).
        wind_speed: A list of numbers for the meteorological wind speed values in m/s
            (measured 10 m above the ground). If None, this will default to a low
            wind speed of 0.5 m/s, which is the lowest input speed that is
            recommended for the UTCI model.
        comfort_parameter: Optional UTCIParameter object to specify parameters under
            which conditions are considered acceptable. If None, default will
            assume comfort thresholds consistent with those used by meteorologists
            to categorize outdoor conditions.

    Properties:
        * psychrometric_chart
        * rad_temperature
        * wind_speed
        * comfort_parameter
        * polygon_count
        * left_comfort_lines
        * right_comfort_lines
        * left_comfort_line
        * right_comfort_line
        * comfort_polygons
        * merged_comfort_polygon
        * comfort_values
        * comfort_data
        * merged_comfort_values
        * merged_comfort_data
        * is_comfort_too_hot
        * is_comfort_too_cold
        * very_strong_cold_polygon
        * strong_cold_polygon
        * moderate_cold_polygon
        * moderate_heat_polygon
        * strong_heat_polygon
        * very_strong_heat_polygon
    """
    TEMP_TYPE = Temperature()
    DELTA_TEMP_TYPE = TemperatureDelta()
    POLYGON_INCLUSION_TYPE = GenericType(
        'Polygon Inclusion', 'status', 0, 1, unit_descr={0: 'Outside', 1: 'Inside'})

    def __init__(self, psychrometric_chart, rad_temperature=None, wind_speed=None,
                 comfort_parameter=None):
        """Initialize a UTCI comfort polygon."""
        # check the psychrometric_chart input
        assert isinstance(psychrometric_chart, PsychrometricChart), 'PolygonUTCI ' \
            'psychrometric_chart must be a ladybug PsychrometricChart. ' \
            'Got {}.'.format(type(psychrometric_chart))
        self._psychrometric_chart = psychrometric_chart

        # determine the number of comfort polygons to be drawn
        all_data = (rad_temperature, wind_speed)
        param_lens = [len(arr) for arr in all_data if arr is not None]
        self._polygon_count = max(param_lens) if len(param_lens) != 0 else 0
        self._polygon_count = 1 if self._polygon_count == 0 else self._polygon_count

        # check parameters with defaults
        self._rad_temperature = self._check_input(
            rad_temperature, 'rad_temperature', None)
        self._wind_speed = self._check_input(wind_speed, 'wind_speed', 0.5, True)

        # check comfort parameters
        if comfort_parameter is None:
            self._comfort_par = UTCIParameter()
        else:
            assert isinstance(comfort_parameter, UTCIParameter), 'comfort_parameter '\
                'must be a UTCIParameter object. Got {}'.format(type(comfort_parameter))
            self._comfort_par = comfort_parameter

        # create the left and right polylines
        _left, _right = [], []
        for p in range(self._polygon_count):
            min_poly, max_poly = self.comfort_polylines(p)
            _left.append(min_poly)
            _right.append(max_poly)
        self._left_comfort_lines, self._right_comfort_lines = tuple(_left), tuple(_right)

        # set parameters to None, which will be computed on demand
        self._left_comfort_line = None
        self._right_comfort_line = None
        self._comfort_polygons = None
        self._merged_comfort_polygons = None
        self._comfort_values = None
        self._comfort_data = None
        self._merged_comfort_values = None
        self._merged_comfort_data = None

    @property
    def psychrometric_chart(self):
        """The ladybug PsychrometricChart object on which the polygons are plot."""
        return self._psychrometric_chart

    @property
    def rad_temperature(self):
        """Tuple of mean radiant temperature (MRT) values in degrees C.

        None indicates that the radiant temperature is the same as the air temperature.
        """
        return self._rad_temperature

    @property
    def wind_speed(self):
        """Tuple of meteorological wind speed values in m/s."""
        return self._wind_speed

    @property
    def comfort_parameter(self):
        """UTCI comfort parameters that are assigned to this object."""
        return self._comfort_par

    @property
    def polygon_count(self):
        """Integer for the number of comfort polygons contained on the object."""
        return self._polygon_count

    @property
    def left_comfort_lines(self):
        """Tuple of Polyline2D for the left of the comfort polygons."""
        return self._left_comfort_lines

    @property
    def right_comfort_lines(self):
        """Tuple of Polyline2D for the right of the comfort polygons."""
        return self._right_comfort_lines

    @property
    def left_comfort_line(self):
        """A single Polyline2D for the left of the merged comfort polygons."""
        if self._left_comfort_line is None:
            li = self._left_comfort_lines
            self._left_comfort_line = li[0] if len(li) == 1 else self._min_polylines(li)
        return self._left_comfort_line

    @property
    def right_comfort_line(self):
        """A single Polyline2D for the right of the merged comfort polygons."""
        if self._right_comfort_line is None:
            li = self._right_comfort_lines
            self._right_comfort_line = li[0] if len(li) == 1 else self._max_polylines(li)
        return self._right_comfort_line

    @property
    def comfort_polygons(self):
        """A tuple of tuples where each sub-tuple defines one comfort polygon.

        Sub-tuple comfort polygons consist of four or five Polyline2D or LineSegment2D
        that are ordered as follows (left, bottom, right, top).
        """
        if self._comfort_polygons is None:
            self._comfort_polygons = []
            ll, rl = self.left_comfort_lines, self.right_comfort_lines
            for lt, rt in zip(ll, rl):
                self._comfort_polygons.append(self._build_comfort_polygon(lt, rt))
        return tuple(self._comfort_polygons)

    @property
    def merged_comfort_polygon(self):
        """A tuple of Polyline2D or LineSegment2D that define the merged comfort polygon.

        Comfort polygon consists of four or five Polyline2D or LineSegment2D that
        are ordered as follows (left, bottom, right, top).
        """
        if self._merged_comfort_polygons is None:
            lt, rt = self.left_comfort_line, self.right_comfort_line
            self._merged_comfort_polygons = self._build_comfort_polygon(lt, rt)
        return self._merged_comfort_polygons

    @property
    def comfort_values(self):
        """A tuple of tuples with each sub-tuple representing one of comfort polygons.

        Each sub-tuple contains 0/1 values for whether the point is inside the
        comfort polygon or not.
        """
        if self._comfort_values is None:
            self._comfort_values = []
            for poly in self.comfort_polygons:
                self._comfort_values.append(self._evaluate_comfort(poly[0], poly[2]))
        return tuple(self._comfort_values)

    @property
    def comfort_data(self):
        """A tuple of data collections or 0/1 values for each of the comfort polygons."""
        if self._comfort_data is None:
            self._comfort_data = []
            for i, dat in enumerate(self.comfort_values):
                if len(dat) == 1:
                    self._comfort_data.append(dat[0])
                else:
                    name = 'Comfort {}'.format(i + 1)
                    self._comfort_data.append(self.create_collection(dat, name))
        return tuple(self._comfort_data)

    @property
    def merged_comfort_values(self):
        """A tuple of 0/1 for whether each point is in the merged comfort polygon or not.
        """
        if self._merged_comfort_values is None:
            poly = self.merged_comfort_polygon
            self._merged_comfort_values = self._evaluate_comfort(poly[0], poly[2])
        return self._merged_comfort_values

    @property
    def merged_comfort_data(self):
        """A data collection or 0/1 for whether the data is in merged comfort polygon.
        """
        if self._merged_comfort_data is None:
            if len(self.merged_comfort_values) == 1:
                self._merged_comfort_data = self.merged_comfort_values[0]
            else:
                self._merged_comfort_data = \
                    self.create_collection(self.merged_comfort_values, 'Comfort')
        return self._merged_comfort_data

    @property
    def is_comfort_too_hot(self):
        """Boolean to note whether comfort polygons are off the chart on the hot side."""
        psy = self.psychrometric_chart
        return self.merged_comfort_polygon[2][0].x >= psy.base_point.x + \
            (psy._max_temperature - psy._min_temperature) * psy._x_dim

    @property
    def is_comfort_too_cold(self):
        """Boolean to note whether comfort polygons are off the chart on the cold side.
        """
        psy = self.psychrometric_chart
        return self.merged_comfort_polygon[0][0].x <= psy.base_point.x

    @property
    def very_strong_cold_polygon(self):
        """A tuple of Polyline2D or LineSegment2D for the very strong cold polygon."""
        left_line = self.stress_polyline(self._comfort_par.very_strong_cold_thresh)
        right_line = self.stress_polyline(self._comfort_par.strong_cold_thresh)
        return self._build_comfort_polygon(left_line, right_line)
    
    @property
    def strong_cold_polygon(self):
        """A tuple of Polyline2D or LineSegment2D for the strong cold polygon."""
        left_line = self.stress_polyline(self._comfort_par.strong_cold_thresh)
        right_line = self.stress_polyline(self._comfort_par.moderate_cold_thresh)
        return self._build_comfort_polygon(left_line, right_line)

    @property
    def moderate_cold_polygon(self):
        """A tuple of Polyline2D or LineSegment2D for the moderate cold polygon."""
        left_line = self.stress_polyline(self._comfort_par.moderate_cold_thresh)
        right_line = self.left_comfort_line
        return self._build_comfort_polygon(left_line, right_line)
    
    @property
    def moderate_heat_polygon(self):
        """A tuple of Polyline2D or LineSegment2D for the moderate heat polygon."""
        left_line = self.right_comfort_line
        right_line = self.stress_polyline(self._comfort_par.moderate_heat_thresh)
        return self._build_comfort_polygon(left_line, right_line)

    @property
    def strong_heat_polygon(self):
        """A tuple of Polyline2D or LineSegment2D for the strong heat polygon."""
        left_line = self.stress_polyline(self._comfort_par.moderate_heat_thresh)
        right_line = self.stress_polyline(self._comfort_par.strong_heat_thresh)
        return self._build_comfort_polygon(left_line, right_line)
    
    @property
    def very_strong_heat_polygon(self):
        """A tuple of Polyline2D or LineSegment2D for the very strong heat polygon."""
        left_line = self.stress_polyline(self._comfort_par.strong_heat_thresh)
        right_line = self.stress_polyline(self._comfort_par.very_strong_heat_thresh)
        return self._build_comfort_polygon(left_line, right_line)

    def comfort_polylines(self, polygon_index):
        """Get the left and right Polyline2D that define a UTCI polygon comfort range.

        Args:
            polygon_index: Integer for the comfort polygon for which min and max
                temperature will be computed.

        Returns:
            The left and right Polyline2D that define the comfort range.
        """
        # get the air temperature and humidity rations
        rel_humids = (0, 20, 40, 60, 80, 100)
        pres = self.psychrometric_chart.average_pressure
        air_temps = self.max_min_air_temperatures(polygon_index, rel_humids)
        humid_ratios = []
        for i, temp in enumerate(air_temps):
            hr_min = humid_ratio_from_db_rh(temp[0], rel_humids[i], pres)
            hr_max = humid_ratio_from_db_rh(temp[1], rel_humids[i], pres)
            humid_ratios.append((hr_min, hr_max))

        # create the points from the temperature and humidity ratios
        psy, left_pts, right_pts = self.psychrometric_chart, [], []
        for hr, ta in zip(humid_ratios, air_temps):
            ta1, ta2 = ta if not psy.use_ip else self.TEMP_TYPE.to_unit(ta, 'F', 'C')
            left_pts.append(Point2D(psy.t_x_value(ta1), psy.hr_y_value(hr[0])))
            right_pts.append(Point2D(psy.t_x_value(ta2), psy.hr_y_value(hr[1])))
        return Polyline2D(left_pts, interpolated=True), \
            Polyline2D(right_pts, interpolated=True)

    def stress_polyline(self, stress_temperature):
        """Get a Polyline2D that defines a specific UTCI value,.
        
        Used to construct stress polygons.

        Args:
            stress_temperature: Number in degrees Celsius for the UTCI value of the
                given stress threshold line to be computed.

        Returns:
            A Polyline2D that define the comfort range.
        """
        # determine which comfort polygon conditions to use
        if len(self.left_comfort_lines) == 1:
            polygon_index = 0
        elif stress_temperature < self._comfort_par.cold_thresh:
            polygon_index = self._min_index(self.left_comfort_lines)
        elif stress_temperature > self._comfort_par.heat_thresh:
            polygon_index = self._max_index(self.right_comfort_lines)
        else:
            polygon_index = 0

        # get the air temperature and humidity rations
        rel_humids = (0, 20, 40, 60, 80, 100)
        pres = self.psychrometric_chart.average_pressure
        utci_dict = self._utci_dict(polygon_index)
        air_temps = []
        for rh in rel_humids:
            utci_dict['rh'] = rh
            t_dict = calc_missing_utci_input(stress_temperature, utci_dict)
            air_temps.append(t_dict['ta'])
        humid_ratios = []
        for i, temp in enumerate(air_temps):
            hr_val = humid_ratio_from_db_rh(temp, rel_humids[i], pres)
            humid_ratios.append(hr_val)

        # create the points from the temperature and humidity ratios
        psy, stress_pts = self.psychrometric_chart, []
        for hr, ta in zip(humid_ratios, air_temps):
            if psy.use_ip:
                ta = self.TEMP_TYPE.to_unit([ta], 'F', 'C')[0]
            stress_pts.append(Point2D(psy.t_x_value(ta), psy.hr_y_value(hr)))
        return Polyline2D(stress_pts, interpolated=True)

    def max_min_air_temperatures(self, polygon_index, rel_humid):
        """Get the max and min air temperature for a comfort polygon at a relative humid.

        Args:
            polygon_index: Integer for the comfort polygon for which min and max
                temperature will be computed.
            rel_humid: A list of relative humidity values for which air temperature
                will be computed.

        Returns:
            A list of tuples where each tuple contains two air temperature values in
            Celsius. The first air temperature is the minimum temperature that meets
            the PPD threshold. The second is the maximum that meets the PPD
            threshold
        """
        # get the UTCI thresholds and UTCI dict
        utci_min = self._comfort_par.cold_thresh
        utci_max = self._comfort_par.heat_thresh
        utci_dict = self._utci_dict(polygon_index)

        # compute the min and max air temperatures of relative humidity
        air_temperatures = []
        for rh in rel_humid:
            utci_dict['rh'] = rh
            min_dict = calc_missing_utci_input(utci_min, utci_dict)
            max_dict = calc_missing_utci_input(utci_max, utci_dict)
            air_temperatures.append((min_dict['ta'], max_dict['ta']))
        return air_temperatures

    def evaluate_inside(self, left, right, polygon_name=None):
        """Get a data collection for polygon inclusion from left and right polylines.

        This will be a single 0 or 1 if there is only one value plotted on the chart.
        
        Args:
            left: A Polyline2D for the left of the polygon.
            right: A Polyline2D for the right of the polygon.
            polygon_name: An optional name to be used to create to the data
                collection metadata.
        """
        value_list = []
        vec = Vector2D(1, 0)
        for pt in self._psychrometric_chart.data_points:
            ray = Ray2D(pt, vec)
            if len(right.intersect_line_ray(ray)) != 0:
                if len(left.intersect_line_ray(ray)) == 0:
                    value_list.append(1)
                else:
                    value_list.append(0)
            else:
                value_list.append(0)
        psy = self.psychrometric_chart
        base = psy.temperature if isinstance(psy.temperature, BaseCollection) \
            else psy.relative_humidity
        if isinstance(base, (float, int)):
            return value_list[0]
        coll = base.get_aligned_collection(
            value_list, self.POLYGON_INCLUSION_TYPE, 'status')
        if polygon_name:
            coll.header.metadata = {'polygon': polygon_name}
        return coll

    def create_collection(self, value_list, polygon_name=None):
        """Create a data collection of comfort data values from a list of values.

        Args:
            value_list: A list of data that align with the number of points in the
                underlying psychrometric chart
            polygon_name: An optional name to be used to create to the data
                collection metadata.
        """
        psy = self.psychrometric_chart
        base = psy.temperature if isinstance(psy.temperature, BaseCollection) \
            else psy.relative_humidity
        coll = base.get_aligned_collection(value_list, ThermalComfort(), 'condition')
        if polygon_name:
            coll.header.metadata = {'polygon': polygon_name}
        return coll

    def _build_comfort_polygon(self, left, right):
        """Build a comfort polygon from left and right polylines."""
        # create the saturation line
        psy = self.psychrometric_chart
        x_mid = (left[-1].x + right[-1].x) / 2
        t_mid, t_mid_c = self._x_to_t(x_mid)
        hr_mid = humid_ratio_from_db_rh(t_mid_c, 100, psy.average_pressure)
        mx, my = psy.t_x_value(t_mid), psy.hr_y_value(hr_mid)
        sat_line = Polyline2D((left[-1], Point2D(mx, my), right[-1]),
                                interpolated=True)

        # create the comfort polygon
        comf_polygon = [left.reverse()]
        comf_polygon.append(LineSegment2D.from_end_points(left[0], right[0]))
        comf_polygon.append(right)
        comf_polygon.append(sat_line)
        return tuple(comf_polygon)

    def _evaluate_comfort(self, left, right):
        """Get a tuple of 0s and 1s for comfort from left and right polylines."""
        comfort_vals = []
        vec = Vector2D(1, 0)
        for pt in self._psychrometric_chart.data_points:
            ray = Ray2D(pt, vec)
            if len(right.intersect_line_ray(ray)) != 0:
                if len(left.intersect_line_ray(ray)) == 0:
                    comfort_vals.append(1)
                else:
                    comfort_vals.append(0)
            else:
                comfort_vals.append(0)
        return tuple(comfort_vals)

    def _utci_dict(self, polygon_index):
        """Get a UTCI dictionary for on set of inputs."""
        return {
            'ta': None,
            'tr': self._rad_temperature[polygon_index],
            'vel': self._wind_speed[polygon_index]
        }

    def _x_to_t(self, x_value):
        """Convert an X value on the psychrometric chart to a temperature."""
        psy = self.psychrometric_chart
        t_val = ((x_value - psy.base_point.x) / psy.x_dim) + psy.min_temperature
        t_val_c = t_val if not psy.use_ip else \
            self.TEMP_TYPE.to_unit([t_val], 'C', 'F')[0]
        return t_val, t_val_c

    def _y_to_hr(self, y_value):
        """Convert an Y value on the psychrometric chart to a humidity ratio."""
        psy = self.psychrometric_chart
        return (y_value - psy.base_point.y) / psy._y_dim

    def _check_input(self, input_param, input_name, default=None, check_positive=False):
        """Check a given input value."""
        if input_param is not None and len(input_param) != 0:
            assert isinstance(input_param, (list, tuple)), \
                'Input {} must be a list or a tuple.'.format(input_name)
            new_input_param = []
            for val in input_param:
                if val is not None:
                    val = float(val)
                    if check_positive:
                        assert val >= 0, 'Input {} must be greater or equal ' \
                            'to 0.'.format(input_name)
                new_input_param.append(val)
            input_param = tuple(new_input_param)
            if len(input_param) != self._polygon_count:
                return input_param + \
                    (input_param[-1],) * (self._polygon_count - len(input_param))
            return input_param
        else:
            return (default,) * self._polygon_count

    @staticmethod
    def _min_polylines(polylines):
        """Construct a minimum polyline form a list of polylines."""
        vert_list = list(polylines[0].vertices)
        for poly in polylines[1:]:
            for i, vert in enumerate(poly.vertices):
                if vert.x < vert_list[i].x:
                    vert_list[i] = vert
        return Polyline2D(vert_list, interpolated=True)

    @staticmethod
    def _max_polylines(polylines):
        """Construct a maximum polyline form a list of polylines."""
        vert_list = list(polylines[0].vertices)
        for poly in polylines[1:]:
            for i, vert in enumerate(poly.vertices):
                if vert.x > vert_list[i].x:
                    vert_list[i] = vert
        return Polyline2D(vert_list, interpolated=True)

    @staticmethod
    def _min_index(polylines):
        """Get the index of the left-most polygon."""
        x_vals = [p[0].x for p in polylines]
        return x_vals.index(min(x_vals))

    @staticmethod
    def _max_index(polylines):
        """Get the index of the left-most polygon."""
        x_vals = [p[0].x for p in polylines]
        return x_vals.index(max(x_vals))

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """PolygonPMV representation."""
        return "Polygon PMV: ({} Polygons)".format(self._polygon_count)
