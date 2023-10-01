# coding=utf-8
"""Object for plotting a Adaptive Comfort Chart."""
from __future__ import division

from ladybug_geometry.geometry2d.pointvector import Point2D, Vector2D
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.polyline import Polyline2D
from ladybug_geometry.geometry2d.mesh import Mesh2D
from ladybug_geometry.geometry3d.pointvector import Point3D

from ladybug.datacollection import DailyCollection, MonthlyCollection
from ladybug.legend import LegendParameters
from ladybug.graphic import GraphicContainer
from ladybug.datatype.time import Time
from ladybug.datatype.temperature import Temperature, OperativeTemperature

from ..adaptive import t_operative
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
        * neutral_temperature
        * degrees_from_neutral
        * is_comfortable
        * thermal_condition
        * percent_comfortable
        * percent_uncomfortable
        * percent_neutral
        * percent_hot
        * percent_cold
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
        '_use_ip', '_tp_category', '_to_category', '_prevail_range', '_op_range'
        '_x_range', '_y_range', '_time_multiplier',
        '_time_matrix', '_hour_values', '_remove_pattern', '_container'
    )
    TEMP_TYPE = Temperature()

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

        # create the graphic container
        if self._use_ip:  # categorize based on every 1.66 fahrenheit
            self._tp_category, self._to_category = [], []
            current_t, max_t = self._max_prevailing, self._min_prevailing + 1.75
            while current_t < max_t:
                current_t += (5 / 3)
                self._tp_category.append(current_t)
            current_t, max_t = self._max_operative, self._min_operative + 1.75
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
        max_x = base_point.x + (self._max_prevailing - self._min_prevailing + 5) \
            * self._x_dim
        max_y = base_point.y + (self._max_operative - self._min_operative + 5) \
            * self._y_dim
        max_pt = Point3D(max_x, max_y, 0)
        min_pt = Point3D(base_point.x, base_point.y, 0)
        self._container = GraphicContainer(
            self._hour_values, min_pt, max_pt, legend_parameters, Time(), 'hr')
        self._process_legend_default(self._container.legend_parameters)

        # create global attributes used by several of the geometry properties
        self._prevail_range = list(range(self._min_prevailing, self._max_prevailing, 5)) \
            + [self._max_prevailing]
        self._x_range = [self.tp_x_value(t) for t in self._prevail_range]
        if use_ip:  # ensure that _temp_range is always in celsius
            self._prevail_range = self.TEMP_TYPE.to_unit(self._prevail_range, 'C', 'F')
        
        self._y_range = [self._y_dim * hr + self._base_point.y for hr in self._hr_range]

        # set null values for properties that are optional
        self._chart_border = None
        self._enth_range = None
        self._enth_lines = None
        self._wb_range = None
        self._wb_lines = None
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
        * 0 = netural
        * +1 = hot
        """
        return self._collection.thermal_condition

    @property
    def percent_comfortable(self):
        """The percent of time comfortabe given by the assigned comfort_parameter."""
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
