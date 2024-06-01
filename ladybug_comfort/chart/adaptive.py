# coding=utf-8
"""Object for plotting a Adaptive Comfort Chart."""
from __future__ import division

from ladybug_geometry.geometry2d import Point2D, Vector2D, LineSegment2D, \
    Polyline2D, Polygon2D, Mesh2D
from ladybug_geometry.geometry3d import Point3D, Vector3D

from ladybug.datacollection import DailyCollection, MonthlyCollection
from ladybug.graphic import GraphicContainer
from ladybug.datatype.time import Time
from ladybug.datatype.temperaturedelta import TemperatureDelta
from ladybug.datatype.temperature import Temperature, OperativeTemperature

from ..adaptive import neutral_temperature_ashrae55, neutral_temperature_en15251, \
    neutral_temperature_conditioned_function, cooling_effect_ashrae55, \
    cooling_effect_en15251, t_operative
from ..collection.base import BaseCollection
from ..collection.adaptive import Adaptive


class AdaptiveChart(object):
    """Adaptive comfort DataCollection object.

    Args:
        outdoor_temperature: Either one of the following inputs are acceptable:

            * A Data Collection of prevailing outdoor temperature values in C.
              Such a Data Collection must align with the operative_temperature
              input and bear the PrevailingOutdoorTemperature data type in
              its header.
            * A single prevailing outdoor temperature value in C to be used
              for all of the operative_temperature inputs below.
            * A Data Collection of actual outdoor temperatures recorded over
              the entire year. This Data Collection must be continuous and
              must either be an Hourly Collection or Daily Collection. In the event
              that the input comfort_parameter has a prevailing_temperature_method
              of 'Monthly', Monthly collections are also acceptable here. Note
              that, because an annual input is required, this input collection
              does not have to align with the operative_temperature input.

        operative_temperature: Data Collection of operative temperature (To)
            values in degrees Celsius.
        air_speed: A number for the air speed values in m/s. If None, a low air
            speed of 0.1 m/s wil be used. (Default: None).
        comfort_parameter: Optional AdaptiveParameter object to specify parameters
            under which conditions are considered acceptable. If None, default will
            assume ASHRAE-55 criteria.
        legend_parameters: An optional LegendParameter object to change the display
            of the AdaptiveChart. (Default: None).
        base_point: A Point2D to be used as a starting point to generate the geometry
            of the plot. (Default: (0, 0)).
        x_dim: A number to set the X dimension of each degree of temperature on the
            chart. (Default: 1).
        y_dim: A number to set the Y dimension of each degree of temperature on
            the chart. (Default: 1).
            Note that most maximum humidity ratios are around 0.03. (Default: 1500).
        min_prevailing: An integer for the minimum prevailing temperature on the
            chart in degrees. This should be celsius if use_ip is False and fahrenheit
            if use_ip is True. (Default: 10; suitable for celsius).
        max_prevailing: An integer for the maximum prevailing temperature on the
            chart in degrees. This should be celsius if use_ip is False and fahrenheit
            if use_ip is True. (Default: 33; suitable for celsius).
        min_operative: An integer for the minimum indoor operative temperature on the
            chart in degrees. This should be celsius if use_ip is False and fahrenheit
            if use_ip is True. (Default: 14; suitable for celsius).
        max_operative: An integer for the maximum indoor operative temperature on the
            chart in degrees. This should be celsius if use_ip is False and fahrenheit
            if use_ip is True. (Default: 40; suitable for celsius).
        use_ip: Boolean to note whether temperature values should be plotted in
            Fahrenheit instead of Celsius. (Default: False).

    Properties:
        * collection
        * prevailing_outdoor_temperature
        * operative_temperature
        * air_speed
        * comfort_parameter
        * legend_parameters
        * base_point
        * x_dim
        * y_dim
        * min_prevailing
        * max_prevailing
        * min_operative
        * max_operative
        * use_ip
        * chart_border
        * prevailing_labels
        * prevailing_label_points
        * prevailing_lines
        * operative_labels
        * operative_label_points
        * operative_lines
        * neutral_temperature
        * degrees_from_neutral
        * neutral_polyline
        * comfort_polygon
        * is_comfortable
        * thermal_condition
        * percent_comfortable
        * percent_uncomfortable
        * percent_neutral
        * percent_hot
        * percent_cold
        * title_text
        * title_location
        * x_axis_text
        * x_axis_location
        * y_axis_text
        * y_axis_location
        * data_points
        * time_matrix
        * hour_values
        * colored_mesh
        * legend
        * container
    """
    __slots__ = (
        '_collection', '_prevailing_outdoor_temperature', '_operative_temperature',
        '_neutral_temperature', '_degrees_from_neutral',
        '_base_point', '_x_dim', '_y_dim',
        '_min_prevailing', '_max_prevailing', '_min_operative', '_max_operative',
        '_use_ip', '_tp_category', '_to_category', '_prevail_range', '_op_range',
        '_x_range', '_y_range', '_time_multiplier',
        '_time_matrix', '_hour_values', '_remove_pattern', '_container',
        '_chart_border', '_data_points', '_colored_mesh'
    )
    TEMP_TYPE = Temperature()
    DT_TYPE = TemperatureDelta()

    def __init__(
        self, outdoor_temperature, operative_temperature, air_speed=None,
        comfort_parameter=None, legend_parameters=None, base_point=Point2D(),
        x_dim=1, y_dim=1, min_prevailing=10, max_prevailing=33,
        min_operative=14, max_operative=40, use_ip=False
    ):
        # check inputs that determine other inputs
        assert air_speed is None or isinstance(air_speed, (float, int)), \
            'Expected number or None for air_speed. Got {}.'.format(type(air_speed))
        self._use_ip = bool(use_ip)

        # build an adaptive comfort collection from the data
        self._collection = Adaptive(outdoor_temperature, operative_temperature,
                                    air_speed, comfort_parameter)

        # ensue all temperatures are in the correct units
        if self._use_ip:  # convert everything to Fahrenheit
            self._prevailing_outdoor_temperature = \
                self._collection.prevailing_outdoor_temperature.to_ip()
            self._operative_temperature = \
                self._collection.operative_temperature.to_ip()
            self._neutral_temperature = \
                self._collection.neutral_temperature.to_ip()
            self._degrees_from_neutral = \
                self._collection.degrees_from_neutral.to_ip()
        else:
            self._prevailing_outdoor_temperature = \
                self._collection.prevailing_outdoor_temperature
            self._operative_temperature = \
                self._collection.operative_temperature
            self._neutral_temperature = self._collection.neutral_temperature
            self._degrees_from_neutral = self._collection.degrees_from_neutral

        # extract the timestep from the data collections
        if isinstance(self._operative_temperature, MonthlyCollection):
            self._time_multiplier = 30 * 24
        elif isinstance(self._operative_temperature, DailyCollection):
            self._time_multiplier = 24
        else:  # it's an hourly or sub-hourly collection
            self._time_multiplier = \
                1 / self._operative_temperature.header.analysis_period.timestep

        # assign the inputs as properties of the chart
        assert isinstance(base_point, Point2D), 'Expected Point2D for ' \
            'PsychrometricChart base point. Got {}.'.format(type(base_point))
        self._base_point = base_point
        self._x_dim = self._check_number(x_dim, 'x_dim')
        self._y_dim = self._check_number(y_dim, 'y_dim')
        assert max_prevailing - min_prevailing >= 10, 'Adaptive chart ' \
            'max_prevailing and min_prevailing difference must be at least 10.'
        assert max_operative - min_operative >= 10, 'Adaptive chart ' \
            'max_operative and min_operative difference must be at least 10.'
        self._max_prevailing = int(max_prevailing)
        self._min_prevailing = int(min_prevailing)
        self._max_operative = int(max_operative)
        self._min_operative = int(min_operative)
        if self._use_ip:
            assert self._max_prevailing > 50, 'max_prevailing must be greater than ' \
                '50F. Got {}.'.format(self._max_prevailing)
            assert self._min_prevailing < 86, 'min_prevailing must be less than ' \
                '86F. Got {}.'.format(self._min_prevailing)
        else:
            assert self._max_prevailing > 10, 'max_prevailing must be greater than ' \
                '10C. Got {}.'.format(self._max_prevailing)
            assert self._min_prevailing < 30, 'min_prevailing must be less than ' \
                '30C. Got {}.'.format(self._min_prevailing)

        # create the graphic container
        if self._use_ip:  # categorize based on every 1.66 fahrenheit
            self._tp_category, self._to_category = [], []
            current_t, max_t = self._min_prevailing, self._max_prevailing + 1.75
            while current_t < max_t:
                current_t += (5 / 3)
                self._tp_category.append(current_t)
            current_t, max_t = self._min_operative, self._max_operative + 1.75
            while current_t < max_t:
                current_t += (5 / 3)
                self._to_category.append(current_t)
        else:  # categorize based on every degree celsius
            self._tp_category = list(range(self._min_prevailing + 1,
                                           self._max_prevailing + 1))
            self._to_category = list(range(self._min_operative + 1,
                                           self._max_operative + 1))
        self._time_matrix, self._hour_values, self._remove_pattern = \
            self._compute_hour_values()
        assert len(self._hour_values) > 0, \
            'No data was found to lie on the adaptive chart.'
        max_x = base_point.x + (self._max_prevailing - self._min_prevailing + 1) \
            * self._x_dim
        max_y = base_point.y + (self._max_operative - self._min_operative + 1) \
            * self._y_dim
        max_pt = Point3D(max_x, max_y, 0)
        min_pt = Point3D(base_point.x, base_point.y, 0)
        self._container = GraphicContainer(
            self._hour_values, min_pt, max_pt, legend_parameters, Time(), 'hr')
        self._process_legend_default(self._container.legend_parameters)

        # create global attributes used by several of the geometry properties
        self._prevail_range = list(range(self._min_prevailing, self._max_prevailing, 2)) \
            + [self._max_prevailing]
        self._x_range = [self.tp_x_value(t) for t in self._prevail_range]
        self._op_range = list(range(self._min_operative, self._max_operative, 2)) \
            + [self._max_operative]
        self._y_range = [self.to_y_value(t) for t in self._op_range]
        if use_ip:  # ensure that _temp_range is always in celsius
            self._prevail_range = self.TEMP_TYPE.to_unit(self._prevail_range, 'C', 'F')
            self._op_range = self.TEMP_TYPE.to_unit(self._op_range, 'C', 'F')

        # set null values for properties that are optional
        self._chart_border = None
        self._data_points = None
        self._colored_mesh = None

    @classmethod
    def from_air_and_rad_temp(
        cls, outdoor_temperature, air_temperature, rad_temperature=None, air_speed=None,
        comfort_parameter=None, legend_parameters=None, base_point=Point2D(),
        x_dim=1, y_dim=1, min_prevailing=10, max_prevailing=33,
        min_operative=14, max_operative=40, use_ip=False
    ):
        """Initialize an AdaptiveChart from air and radiant temperature."""
        if rad_temperature is None:
            to = air_temperature
        else:
            to = BaseCollection.compute_function_aligned(
                t_operative, [air_temperature, rad_temperature],
                OperativeTemperature(), 'C')
        return cls(
            outdoor_temperature, to, air_speed, comfort_parameter,
            legend_parameters, base_point, x_dim, y_dim,
            min_prevailing, max_prevailing, min_operative, max_operative, use_ip
        )

    @property
    def prevailing_outdoor_temperature(self):
        """Data Collection of prevailing outdoor temperature.

        This will be in in degrees C if use_ip is False and degrees F if use_ip is True.
        """
        return self._prevailing_outdoor_temperature

    @property
    def operative_temperature(self):
        """Data Collection of indoor operative temperature.

        This will be in in degrees C if use_ip is False and degrees F if use_ip is True.
        """
        return self._operative_temperature

    @property
    def air_speed(self):
        """Value for air speed in m/s."""
        return self._collection.air_speed[0]

    @property
    def comfort_parameter(self):
        """Adaptive comfort parameters that are assigned to this object."""
        return self._collection.comfort_parameter

    @property
    def legend_parameters(self):
        """The legend parameters customizing this adaptive chart."""
        return self._container.legend_parameters

    @property
    def base_point(self):
        """Point3D for the base point of this adaptive chart."""
        return self._base_point

    @property
    def x_dim(self):
        """The X dimension for each degree of prevailing temperature on the chart."""
        return self._x_dim

    @property
    def y_dim(self):
        """The Y dimension for each degree of operative temperature on the chart."""
        return self._y_dim

    @property
    def min_prevailing(self):
        """An integer for the minimum prevailing outdoor temperature on the chart.

        Will be in celsius if use_ip is False and fahrenheit if use_ip is True.
        """
        return self._min_prevailing

    @property
    def max_prevailing(self):
        """An integer for the maximum prevailing outdoor temperature on the chart.

        Will be in celsius if use_ip is False and fahrenheit if use_ip is True.
        """
        return self._max_prevailing

    @property
    def min_operative(self):
        """An integer for the minimum indoor operative temperature on the chart.

        Will be in celsius if use_ip is False and fahrenheit if use_ip is True.
        """
        return self._min_operative

    @property
    def max_operative(self):
        """An integer for the maximum indoor operative temperature on the chart.

        Will be in celsius if use_ip is False and fahrenheit if use_ip is True.
        """
        return self._max_operative

    @property
    def use_ip(self):
        """Boolean for whether temperature should be in Fahrenheit or Celsius."""
        return self._use_ip

    @property
    def chart_border(self):
        """Get a Polygon2D for the border of the chart."""
        if self._chart_border is None:
            self._chart_border = self._compute_border()
        return self._chart_border

    @property
    def prevailing_labels(self):
        """Get a tuple of text for the prevailing temperature labels on the chart."""
        if self.use_ip:
            temp_range = tuple(range(self._min_prevailing, self._max_prevailing, 2)) \
                + (self._max_prevailing,)
            return tuple(str(val) for val in temp_range)
        return tuple(str(val) for val in self._prevail_range)

    @property
    def prevailing_label_points(self):
        """Get a tuple of Point2Ds for the prevailing temperature labels on the chart."""
        y_val = self._base_point.y - self.legend_parameters.text_height * 0.5
        return tuple(Point2D(x_val, y_val) for x_val in self._x_range)

    @property
    def prevailing_lines(self):
        """Get a tuple of LineSegment2Ds for the prevailing temperature lines."""
        t_lines = []  # create the array of line segments
        y_vec = Vector2D(0, self._y_range[-1] - self._y_range[0])
        for x_val in self._x_range:
            l_seg = LineSegment2D(Point2D(x_val, self._base_point.y), y_vec)
            t_lines.append(l_seg)
        return t_lines

    @property
    def operative_labels(self):
        """Get a tuple of text for the operative temperature labels on the chart."""
        if self.use_ip:
            temp_range = tuple(range(self._min_operative, self._max_operative, 2)) \
                + (self._max_operative,)
            return tuple(str(val) for val in temp_range)
        return tuple(str(val) for val in self._op_range)

    @property
    def operative_label_points(self):
        """Get a tuple of Point2Ds for the operative temperature labels on the chart."""
        x_val = self._base_point.x - self.legend_parameters.text_height * 2.5
        return tuple(Point2D(x_val, y_val) for y_val in self._y_range)

    @property
    def operative_lines(self):
        """Get a tuple of LineSegment2Ds for the operative temperature lines."""
        t_lines = []  # create the array of line segments
        x_vec = Vector2D(self._x_range[-1] - self._x_range[0], 0)
        for y_val in self._y_range:
            l_seg = LineSegment2D(Point2D(self._base_point.x, y_val), x_vec)
            t_lines.append(l_seg)
        return t_lines

    @property
    def neutral_polyline(self):
        """Get a LineSegment2D or Polyline2D noting the neutral temperature on the chart.
        """
        # get properties that are used to compute the neutral temperature
        tp_c_min, tp_c_max = self._prevail_range[0], self._prevail_range[-1]
        pl_pts = []
        if self.comfort_parameter.conditioning != 0:
            neutral_func = neutral_temperature_conditioned_function(
                self.comfort_parameter.conditioning, self.comfort_parameter.standard
            )
        elif self.comfort_parameter.ashrae_or_en:
            neutral_func = neutral_temperature_ashrae55
        else:
            neutral_func =neutral_temperature_en15251

        # get the beginning points
        x_val1 = self._x_range[0]
        if tp_c_min < 10:
            n_temp = neutral_func(10)
            y_val = self.to_y_value(n_temp) if not self.use_ip else \
                self.to_y_value(self.TEMP_TYPE.to_unit([n_temp], 'F', 'C')[0])
            pl_pts.append(Point2D(x_val1, y_val))
            x_val2 = self.tp_x_value(50) if self.use_ip else self.tp_x_value(10)
            pl_pts.append(Point2D(x_val2, y_val))
        else:
            n_temp = neutral_func(tp_c_min)
            y_val = self.to_y_value(n_temp) if not self.use_ip else \
                self.to_y_value(self.TEMP_TYPE.to_unit([n_temp], 'F', 'C')[0])
            pl_pts.append(Point2D(x_val1, y_val))
        # get the ending points
        x_val_end = self._x_range[-1]
        if self.comfort_parameter.ashrae_or_en:
            if tp_c_max > 33.5:
                n_temp = neutral_func(33.5)
                y_val = self.to_y_value(n_temp) if not self.use_ip else \
                    self.to_y_value(self.TEMP_TYPE.to_unit([n_temp], 'F', 'C')[0])
                x_vali = self.tp_x_value(92.3) if self.use_ip else self.tp_x_value(33.5)
                pl_pts.append(Point2D(x_vali, y_val))
                pl_pts.append(Point2D(x_val_end, y_val))
            else:
                n_temp = neutral_func(tp_c_max)
                y_val = self.to_y_value(n_temp) if not self.use_ip else \
                    self.to_y_value(self.TEMP_TYPE.to_unit([n_temp], 'F', 'C')[0])
                pl_pts.append(Point2D(x_val_end, y_val))
        else:
            if tp_c_max > 30:
                n_temp = neutral_func(30)
                y_val = self.to_y_value(n_temp) if not self.use_ip else \
                    self.to_y_value(self.TEMP_TYPE.to_unit([n_temp], 'F', 'C')[0])
                x_vali = self.tp_x_value(86) if self.use_ip else self.tp_x_value(30)
                pl_pts.append(Point2D(x_vali, y_val))
                pl_pts.append(Point2D(x_val_end, y_val))
            else:
                n_temp = neutral_func(tp_c_max)
                y_val = self.to_y_value(n_temp) if not self.use_ip else \
                    self.to_y_value(self.TEMP_TYPE.to_unit([n_temp], 'F', 'C')[0])
                pl_pts.append(Point2D(x_val_end, y_val))

        # return the neutral line
        return Polyline2D(pl_pts) if len(pl_pts) > 2 else \
            LineSegment2D.from_end_points(pl_pts[0], pl_pts[1])

    @property
    def comfort_polygon(self):
        """Get a Polygon2D for the comfort range on the chart."""
        # start off with the neutral polyline and move it based on the offset
        neutral_line = self.neutral_polyline
        offset_t_up = self.comfort_parameter.neutral_offset
        # lower threshold of EN-16798 is 1 degree cooler than upper threshold
        offset_t_low = -self.comfort_parameter.neutral_offset \
            if self.comfort_parameter.standard == 'ASHRAE-55' else \
            -self.comfort_parameter.neutral_offset - 1
        offset_t_up = offset_t_up if not self.use_ip else \
            self.DT_TYPE.to_unit([offset_t_up], 'dF', 'dC')[0]
        offset_t_low = offset_t_low if not self.use_ip else \
            self.DT_TYPE.to_unit([offset_t_low], 'dF', 'dC')[0]

        offset_dist_up = self.y_dim * offset_t_up
        offset_dist_low = self.y_dim * offset_t_low
        upper_line = neutral_line.move(Vector2D(0, offset_dist_up))
        lower_line = neutral_line.move(Vector2D(0, offset_dist_low))

        # trim the bottom of the polygon if there is a cold_prevail_temp_limit
        if self.comfort_parameter.cold_prevail_temp_limit > 10:
            limit_tc = self.comfort_parameter.cold_prevail_temp_limit
            limit_t = limit_tc if not self.use_ip else \
                self.TEMP_TYPE.to_unit([limit_tc], 'F', 'C')[0]
            limit_x = self.tp_x_value(limit_t)
            int_lin = LineSegment2D.from_end_points(Point2D(limit_x, self._y_range[0]),
                                                    Point2D(limit_x, self._y_range[-1]))
            i_pts = lower_line.intersect_line_ray(int_lin)
            if i_pts is not None and (len(i_pts) == 1 or isinstance(i_pts, Point2D)):
                int_pt = i_pts if isinstance(i_pts, Point2D) else i_pts[0]
                new_low_pts, int_passed = [], False
                for pt in lower_line.vertices:
                    if pt.x < int_pt.x:
                        new_low_pts.append(Point2D(pt.x, int_pt.y))
                    elif not int_passed:
                        new_low_pts.append(int_pt)
                        new_low_pts.append(pt)
                        int_passed = True
                    else:
                        new_low_pts.append(pt)
                lower_line = Polyline2D(new_low_pts) if len(new_low_pts) > 2 else \
                    LineSegment2D.from_end_points(new_low_pts[0], new_low_pts[1])

        # determine if there is a cooling effect
        if self.comfort_parameter.discrete_or_continuous_air_speed is True:
            cooling_func = cooling_effect_ashrae55
        else:
            cooling_func = cooling_effect_en15251
        ce = cooling_func(self.air_speed, self._prevail_range[-1])
        if ce == 0:  # we can build the polygon from upper/lower lines
            return Polygon2D(lower_line.vertices + tuple(reversed(upper_line.vertices)))

        # adjust the upper line to account for the cooling effect
        ce_t = ce if not self.use_ip else self.DT_TYPE.to_unit([ce], 'dF', 'dC')[0]
        ce_dist = self.y_dim * ce_t
        ce_vec = Vector2D(0, ce_dist)
        switch_tc = 12 if self.comfort_parameter.ashrae_or_en else 12.73
        switch_t = switch_tc if not self.use_ip else \
            self.TEMP_TYPE.to_unit([switch_tc], 'F', 'C')[0]
        switch_x = self.tp_x_value(switch_t)
        if upper_line.vertices[0].x >= switch_x:
            new_up_pts = [pt.move(ce_vec) for pt in upper_line.vertices]
        else:
            new_up_pts, switch_occurred = [], False
            for i, pt in enumerate(upper_line.vertices):
                if pt.x <= switch_x:
                    new_up_pts.append(pt)
                else:
                    if switch_occurred:
                        new_up_pts.append(pt.move(ce_vec))
                    else:
                        int_line1 = LineSegment2D.from_end_points(
                            Point2D(switch_x, self._y_range[0]),
                            Point2D(switch_x, self._y_range[-1]))
                        int_line2 = LineSegment2D.from_end_points(
                            upper_line.vertices[i - 1], pt)
                        int_pt = int_line1.intersect_line_ray(int_line2)
                        new_up_pts.append(int_pt)
                        new_up_pts.append(int_pt.move(ce_vec))
                        new_up_pts.append(pt.move(ce_vec))
                        switch_occurred = True
        return Polygon2D(lower_line.vertices + tuple(reversed(new_up_pts)))

    @property
    def neutral_temperature(self):
        """Data Collection of the desired neutral temperature in degrees C."""
        return self._neutral_temperature

    @property
    def degrees_from_neutral(self):
        """Data Collection of the degrees from desired neutral temperature in C."""
        return self._degrees_from_neutral

    @property
    def is_comfortable(self):
        """Data Collection of integers noting whether the input conditions are
        acceptable according to the assigned comfort_parameter.

        Values are one of the following:
        * 0 = uncomfortable
        * 1 = comfortable
        """
        return self._collection.is_comfortable

    @property
    def thermal_condition(self):
        """Data Collection of integers noting the thermal status of a subject
        according to the assigned comfort_parameter.

        Values are one of the following:
        * -1 = cold
        * 0 = neutral
        * +1 = hot
        """
        return self._collection.thermal_condition

    @property
    def percent_comfortable(self):
        """The percent of time comfortable given by the assigned comfort_parameter."""
        return self._collection.percent_comfortable

    @property
    def percent_uncomfortable(self):
        """The percent of time uncomfortable given by the assigned comfort_parameter."""
        return self._collection.percent_uncomfortable

    @property
    def percent_neutral(self):
        """The percent of time that the thermal_condition is neutral."""
        self._collection.percent_neutral

    @property
    def percent_cold(self):
        """The percent of time that the thermal_condition is cold."""
        self._collection.percent_cold

    @property
    def percent_hot(self):
        """The percent of time that the thermal_condition is hot."""
        self._collection.percent_hot

    @property
    def title_text(self):
        """Get text for the title of the chart."""
        title_items = ['Adaptive Chart', 'Time [hr]']
        extra_data = self.operative_temperature.header.metadata.items()
        if len(extra_data) == 0:
            extra_data = self.prevailing_outdoor_temperature.header.metadata.items()
        return '\n'.join(title_items + ['{}: {}'.format(k, v) for k, v in extra_data])

    @property
    def title_location(self):
        """Get a Point2D for the title of the chart."""
        origin = self.container.lower_title_location.o.move(
            Vector3D(0, -self.legend_parameters.text_height * 4))
        return Point2D(origin.x, origin.y)

    @property
    def x_axis_text(self):
        """Get text for the X-axis label of the chart."""
        unit = 'C' if not self.use_ip else 'F'
        return 'Prevailing Outdoor Temperature [{}]'.format(unit) \
            if self.comfort_parameter.avg_month_or_running_mean else \
            'Outdoor Running Mean Temperature [{}]'.format(unit)

    @property
    def x_axis_location(self):
        """Get a Point2D for the X-axis label of the chart."""
        y_val = self._base_point.y - self.legend_parameters.text_height * 2.5
        x_val = (self._x_range[0] + self._x_range[-1]) / 2
        return Point2D(x_val, y_val)

    @property
    def y_axis_text(self):
        """Get text for the Y-axis label of the chart."""
        unit = 'C' if not self.use_ip else 'F'
        if 'type' in self.operative_temperature.header.metadata:
            return '{} [{}]'.format(
                self.operative_temperature.header.metadata['type'], unit)
        return '{} [{}]'.format(self.operative_temperature.header.data_type, unit)

    @property
    def y_axis_location(self):
        """Get a Point2D for the Y-axis label of the chart."""
        x_val = self._base_point.x - self.legend_parameters.text_height * 5.5
        y_val = (self._y_range[0] + self._y_range[-1]) / 2
        return Point2D(x_val, y_val)

    @property
    def data_points(self):
        """Get a tuple of Point2Ds for each of the temperature values."""
        if self._data_points is None:
            zip_o = zip(self.prevailing_outdoor_temperature, self.operative_temperature)
            self._data_points = tuple(
                Point2D(self.tp_x_value(tp), self.to_y_value(to))
                for tp, to in zip_o
            )
        return self._data_points

    @property
    def time_matrix(self):
        """Get a tuple of of tuples where each sub-tuple is a row of the mesh.

        Each value in the resulting matrix corresponds to the number of prevailing/
        operative temperature points in a given cell of the mesh.
        """
        return tuple(tuple(row) for row in self._time_matrix)

    @property
    def hour_values(self):
        """Get a tuple for the number of hours associated with each colored_mesh face."""
        return self._hour_values

    @property
    def colored_mesh(self):
        """Get a colored mesh for the number of hours for each part of the chart."""
        if self._colored_mesh is None:
            self._colored_mesh = self._generate_mesh()
        return self._colored_mesh

    @property
    def legend(self):
        """The legend assigned to this graphic."""
        return self._container._legend

    @property
    def container(self):
        """Get the GraphicContainer for the colored mesh."""
        return self._container

    def data_mesh(self, data_collection, legend_parameters=None):
        """Get a colored mesh for a data_collection aligned with the chart's data.

        Args:
            data_collection: A data collection that is aligned with the prevailing
                and operative temperature values of the chart.
            legend_parameters: Optional legend parameters to customize the legend
                and look of the resulting mesh.

        Returns:
            A tuple with two values.

            -   mesh: A colored Mesh2D similar to the chart's colored_mesh property
                but where each face is colored with the average value of the input
                data_collection.

            -   container: A GraphicContainer object for the mesh, which possesses
                a legend that corresponds to the mesh.
        """
        # check to be sure the data collection aligns
        data_vals = data_collection.values
        _tp_values = self.prevailing_outdoor_temperature.values
        _to_values = self.operative_temperature.values
        assert len(data_vals) == len(self.operative_temperature.values), \
            'Number of data collection values ' \
            'must match those of the prevailing and operative temperature.'

        # create a matrix with a tally of the hours for all the data
        base_mtx = [[[] for val in self._tp_category] for rh in self._to_category]
        for tp, to, val in zip(_tp_values, _to_values, data_vals):
            if tp < self._min_prevailing or tp > self._max_prevailing:
                continue  # temperature value does not currently fit on the chart
            if to < self._min_operative or to > self._max_operative:
                continue  # temperature value does not currently fit on the chart
            for y, to_cat in enumerate(self._to_category):
                if to < to_cat:
                    break
            for x, tp_cat in enumerate(self._tp_category):
                if tp < tp_cat:
                    break
            base_mtx[y][x].append(val)

        # compute average values
        avg_values = [sum(val_list) / len(val_list) for tp_l in base_mtx
                      for val_list in tp_l if len(val_list) != 0]

        # create the colored mesh and graphic container
        base_contain = self.container
        container = GraphicContainer(
            avg_values, base_contain.min_point, base_contain.max_point,
            legend_parameters, data_collection.header.data_type,
            data_collection.header.unit)
        self._process_legend_default(container.legend_parameters)
        mesh = self.colored_mesh.duplicate()  # start with hour mesh as a base
        mesh.colors = container.value_colors
        return mesh, container

    def plot_point(self, prevailing, operative):
        """Get a Point2D for a given prevailing and operative temperature on the chart.

        Args:
            prevailing: A prevailing temperature value, which should be in Celsius
                if use_ip is False and Fahrenheit is use_ip is True.
            operative: An operative temperature value, which should be in Celsius
                if use_ip is False and Fahrenheit is use_ip is True.
        """
        return Point2D(self.tp_x_value(prevailing), self.to_y_value(operative))

    def to_y_value(self, temperature):
        """Get the Y-coordinate for a certain operative temperature on the chart.

        Args:
            temperature: A temperature value, which should be in Celsius if use_ip
                is False and Fahrenheit is use_ip is True.
        """
        return self.base_point.y + self._y_dim * (temperature - self._min_operative)

    def tp_x_value(self, temperature):
        """Get the X-coordinate for a certain prevailing temperature on the chart.

        Args:
            temperature: A temperature value, which should be in Celsius if use_ip
                is False and Fahrenheit is use_ip is True.
        """
        return self._base_point.x + self._x_dim * (temperature - self._min_prevailing)

    def _compute_hour_values(self):
        """Compute the matrix of binned time values based on the chart inputs.

        Returns:
            A tuple with three values.

            -   base_mtx: A full matrix with counts of values for each degree
                temperature and 5% RH of the chart.

            -   mesh_values: A list of numbers for the values of the mesh.

            -   remove_pattern: A list of booleans for which faces of the full mesh
                should be removed.
        """
        # create a matrix with a tally of the hours for all the data
        base_mtx = [[0 for tp in self._tp_category] for to in self._to_category]
        zip_obj = zip(self.prevailing_outdoor_temperature, self.operative_temperature)
        for tp, to in zip_obj:
            if tp < self._min_prevailing or tp > self._max_prevailing:
                continue  # temperature value does not currently fit on the chart
            if to < self._min_operative or to > self._max_operative:
                continue  # temperature value does not currently fit on the chart
            for y, to_cat in enumerate(self._to_category):
                if to < to_cat:
                    break
            for x, tp_cat in enumerate(self._tp_category):
                if tp < tp_cat:
                    break
            base_mtx[y][x] += 1

        # flatten the matrix and create a pattern to remove faces
        flat_values = [tc * self._time_multiplier for to_l in base_mtx for tc in to_l]
        remove_pattern = [val != 0 for val in flat_values]
        mesh_values = tuple(val for val in flat_values if val != 0)
        return base_mtx, mesh_values, remove_pattern

    def _generate_mesh(self):
        """Get the colored mesh from this object's hour values."""
        # global properties used in the generation of the mesh
        t_per_row = [self._min_prevailing] + self._tp_category
        x_per_row = [self.tp_x_value(t) for t in t_per_row]

        # loop through RH rows and create mesh vertices and faces
        vertices = [Point2D(x, self._base_point.y) for x in x_per_row]
        faces, vert_count, row_len = [], 0, len(t_per_row)
        for to in self._to_category:
            vert_count += row_len
            y1 = self.to_y_value(to)
            vertices.append(Point2D(x_per_row[0], y1))
            for i, t in enumerate(x_per_row[1:]):
                vertices.append(Point2D(x_per_row[i + 1], y1))
                v1 = vert_count - row_len + i
                v2 = v1 + 1
                v3 = vert_count + i + 1
                v4 = v3 - 1
                faces.append((v1, v2, v3, v4))

        # create the Mesh2D, remove unused faces, and assign the colors
        mesh = Mesh2D(vertices, faces)
        mesh = mesh.remove_faces_only(self._remove_pattern)
        mesh.colors = self._container.value_colors
        return mesh

    def _compute_border(self):
        """Compute a Polygon2D for the outer border of the chart."""
        # get properties used to establish the border of the chart
        bpt = self.base_point
        x_max = bpt.x + (self.max_prevailing - self.min_prevailing) * self._x_dim
        y_max = bpt.y + (self.max_operative - self.min_operative) * self._y_dim

        # get the points and build the polyline
        return Polygon2D(
            (bpt, Point2D(x_max, bpt.y), Point2D(x_max, y_max), Point2D(bpt.x, y_max))
        )

    def _process_legend_default(self, l_par):
        """Override the dimensions of the legend to ensure it fits the chart."""
        min_pt, max_pt = self.container.min_point, self.container.max_point
        if l_par.vertical and l_par.is_segment_height_default:
            l_par.properties_3d.segment_height = (max_pt.y - min_pt.y) / 20
            l_par.properties_3d._is_segment_height_default = True
        elif l_par.vertical and l_par.is_segment_height_default:
            l_par.properties_3d.segment_width = (max_pt.x - min_pt.x) / 20
            l_par.properties_3d._is_segment_width_default = True

    @staticmethod
    def _check_number(value, value_name):
        """Check a given value for a dimension input."""
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise TypeError('Expected number for Psychrometric Chart {}. '
                            'Got {}.'.format(value_name, type(value)))
        assert value > 0, 'Psychrometric Chart {} must be greater than 0. ' \
            'Got {}.'.format(value_name, value)
        return value

    def __len__(self):
        """Return length of values on the object."""
        return len(self.operative_temperature._values)

    def __getitem__(self, key):
        """Return a tuple of temperature and humidity."""
        return self.prevailing_outdoor_temperature._values[key], \
            self.operative_temperature._values[key]

    def __iter__(self):
        """Iterate through the values."""
        return zip(
            self.prevailing_outdoor_temperature._values,
            self.operative_temperature._values
        )

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """Adaptive Chart representation."""
        return 'Adaptive Chart: {} values'.format(len(self))
