# coding=utf-8
"""Object for plotting a PMV comfort polygon on a Psychrometric Chart."""
from __future__ import division

from ..pmv import calc_missing_pmv_input, pmv_from_ppd
from ..parameter.pmv import PMVParameter

from ladybug.psychchart import PsychrometricChart
from ladybug.psychrometrics import humid_ratio_from_db_rh, wet_bulb_from_db_hr, \
    humid_ratio_from_db_wb, db_temp_from_rh_hr
from ladybug._datacollectionbase import BaseCollection
from ladybug.datacollection import HourlyContinuousCollection, \
    HourlyDiscontinuousCollection
from ladybug.datatype.temperature import Temperature
from ladybug.datatype.temperaturedelta import TemperatureDelta
from ladybug.datatype.thermalcondition import ThermalComfort

from ladybug_geometry.geometry2d.pointvector import Point2D, Vector2D
from ladybug_geometry.geometry2d.ray import Ray2D
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.polyline import Polyline2D
from ladybug_geometry.intersection2d import intersect_line2d_infinite


class PolygonPMV(object):
    """Object to plot a PMV comfort polygon on a Psychrometric Chart.

    Args:
        psychrometric_chart: A ladybug-core PsychrometricChart object on which the
            PMV comfort polygon will be plot.
        rad_temperature: A list of numbers for the mean radiant temperature in Celsius.
            If None, a polygon for operative temperature will be plot, assuming that
            radiant temperature and air temperature are the same. (Default: None).
        air_speed: A list of numbers for the air speed values in m/s. If None, a
            low air speed of 0.1 m/s wil be used for all polygons. (Default: None).
        met_rate: A list of numbers for the metabolic rate in met. If None, a met
            rate of 1.1 met will be used for all polygons, indicating a human
            subject who is seated, typing. (Default: None).
        clo_value: A list of numbers for the clothing level in clo. If None, a clo
            level of 0.7 clo will be used for all polygons, indicating a human
            subject with a long sleeve shirt and pants. (Default: None).
        external_work: A list of numbers for the external work in met. If None, a met
            rate of 0 met will be used for all polygons, indicating a human
            subject who is seated. (Default: None).
        comfort_parameter: Optional PMVParameter object to specify parameters under
            which conditions are considered acceptable. If None, default will
            assume a PPD threshold of 10%, no absolute humidity constraints
            and a still air threshold of 0.1 m/s.

    Properties:
        * psychrometric_chart
        * rad_temperature
        * air_speed
        * met_rate
        * clo_value
        * external_work
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
    """
    TEMP_TYPE = Temperature()
    DELTA_TEMP_TYPE = TemperatureDelta()

    def __init__(self, psychrometric_chart, rad_temperature=None, air_speed=None,
                 met_rate=None, clo_value=None, external_work=None,
                 comfort_parameter=None):
        """Initialize a PMV comfort polygon."""
        # check the psychrometric_chart input
        assert isinstance(psychrometric_chart, PsychrometricChart), 'PolygonPMV ' \
            'psychrometric_chart must be a ladybug PsychrometricChart. ' \
            'Got {}.'.format(type(psychrometric_chart))
        self._psychrometric_chart = psychrometric_chart

        # determine the number of comfort polygons to be drawn
        all_data = (rad_temperature, air_speed, met_rate, clo_value, external_work)
        param_lens = [len(arr) for arr in all_data if arr is not None]
        self._polygon_count = max(param_lens) if len(param_lens) != 0 else 0
        self._polygon_count = 1 if self._polygon_count == 0 else self._polygon_count

        # check parameters with defaults
        self._rad_temperature = self._check_input(
            rad_temperature, 'rad_temperature', None)
        self._air_speed = self._check_input(air_speed, 'air_speed', 0.1, True)
        self._met_rate = self._check_input(met_rate, 'met_rate', 1.1, True)
        self._clo_value = self._check_input(clo_value, 'clo_value', 0.7, True)
        self._external_work = self._check_input(external_work, 'external_work', 0., True)

        # check comfort parameters
        if comfort_parameter is None:
            self._comfort_par = PMVParameter()
        else:
            assert isinstance(comfort_parameter, PMVParameter), 'comfort_parameter '\
                'must be a PMVParameter object. Got {}'.format(type(comfort_parameter))
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
    def air_speed(self):
        """Tuple of air speed values in m/s."""
        return self._air_speed

    @property
    def met_rate(self):
        """Tuple of metabolic rate in met.

        * 1 met = Metabolic rate of a resting seated person
        * 1.2 met = Metabolic rate of a standing person
        * 2 met = Metabolic rate of a walking person
        * If left blank, default is set to 1.1 met (for seated, typing).
        """
        return self._met_rate

    @property
    def clo_value(self):
        """Tuple of clothing level of the human subject in clo.

        * 1 clo = Three-piece suit
        * 0.5 clo = Shorts + T-shirt
        * 0 clo = No clothing
        * If left blank, default is set to 0.85 clo.
        """
        return self._clo_value

    @property
    def external_work(self):
        """Tuple of the work done by the human subject in met."""
        return self._external_work

    @property
    def comfort_parameter(self):
        """PMV comfort parameters that are assigned to this object."""
        return self._comfort_par.duplicate()  # duplicate since ppd_thresh is setable

    @property
    def polygon_count(self):
        """Integer for the number of comfort polygons contined on the object."""
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
        """A tuple of tuples with each sub-tuple representing one of the comfort polygons.

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
        """A data collection or 0/1 for whether the data is in the merged comfort polygon.
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

    def evaporative_cooling_polygon(self):
        """Get a tuple of Polyline2D and LineSegment2D for an evaporative cooling polygon.

        This will be None if the polygon does not fit on the chart.
        """
        # check to be sure the evaporative cooling polygon fits on the chart
        if self.is_comfort_too_hot:
            return None
        psy = self._psychrometric_chart
        comf_poly = self.merged_comfort_polygon

        # get the line of constant wet bulb that forms the top of the polygon
        top_pt = comf_poly[2][-1]
        _, db_c = self._x_to_t(top_pt.x)
        hr = self._y_to_hr(top_pt.y)
        wb_c = wet_bulb_from_db_hr(db_c, hr, psy.average_pressure)
        e_db = psy.max_temperature if not psy.use_ip else \
            self.TEMP_TYPE.to_unit([psy.max_temperature], 'C', 'F')[0]
        e_hr = humid_ratio_from_db_wb(e_db, wb_c, psy.average_pressure)
        e_pt = Point2D(psy.t_x_value(psy.max_temperature), psy.hr_y_value(e_hr))
        wb_line_top = LineSegment2D.from_end_points(e_pt, top_pt)

        # figure out if a vertical chart border seg is needed or trim the wb_line_top
        if e_hr > 0:
            bx = (psy.max_temperature - psy.min_temperature) * psy._x_dim
            b_pt = Point2D(psy.base_point.x + bx, psy.base_point.y)
            right_border = LineSegment2D.from_end_points(b_pt, e_pt)
            evap_lines = [wb_line_top, right_border]
        else:
            b_pt = psy.chart_border.intersect_line_ray(wb_line_top)[0]
            evap_lines = [LineSegment2D.from_end_points(b_pt, wb_line_top.p2)]

        # figure out if another constant WB line is needed on the left
        if self._comfort_par.humid_ratio_lower != 0:
            left_pt = comf_poly[1].p1
            _, db_c = self._x_to_t(left_pt.x)
            hr = self._y_to_hr(left_pt.y)
            wb_c = wet_bulb_from_db_hr(db_c, hr, psy.average_pressure)
            e_db = psy.max_temperature if not psy.use_ip else \
                self.TEMP_TYPE.to_unit([psy.max_temperature], 'C', 'F')[0]
            e_hr = humid_ratio_from_db_wb(e_db, wb_c, psy.average_pressure)
            e_pt = Point2D(psy.t_x_value(psy.max_temperature), psy.hr_y_value(e_hr))
            wb_line_left = LineSegment2D.from_end_points(left_pt, e_pt)
            if e_hr > 0:  # polygon intersects left of chart
                evap_lines[1] = LineSegment2D.from_end_points(
                    wb_line_left.p2, evap_lines[1].p2)
                evap_lines.append(wb_line_left)
            else:  # polygon intersects bottom of chart
                b_pt = psy.chart_border.intersect_line_ray(wb_line_left)[0]
                wb_line_left = LineSegment2D.from_end_points(wb_line_left.p1, b_pt)
                bot_line = LineSegment2D.from_end_points(b_pt, evap_lines[-1].p1)
                evap_lines.extend((bot_line, wb_line_left))
        else:
            bot_line = LineSegment2D.from_end_points(comf_poly[2][0], evap_lines[-1].p1)
            evap_lines.append(bot_line)

        # add the lines that border the comfort polygon
        if self._comfort_par.humid_ratio_lower != 0:
            evap_lines.extend((comf_poly[1].flip(), comf_poly[2].reverse()))
        else:
            evap_lines.append(comf_poly[2].reverse())
        evap_lines.reverse()
        return tuple(evap_lines)

    def fan_use_polygon(self, air_speed=1.0):
        """Get a tuple of Polyline2D and LineSegment2D for use of fans in the space.

        This will be None if the polygon does not fit on the chart.

        Args:
            air_speed: The air speed around the occupants that the fans create
                in m/s. Note that values above 1 m/s tend to blow papers
                around. (Default: 1.0 m/3)
        """
        # check to be sure the fan use polygon fits on the chart
        if self.is_comfort_too_hot:
            return None
        comf_poly = self.merged_comfort_polygon

        # get the warmest set of thermal conditions to add fans to
        poly_i = list(range(self.polygon_count))
        p_x_vals = [pl[3].x for pl in self.right_comfort_lines]
        max_i = [x for _, x in sorted(zip(p_x_vals, poly_i))][-1]

        # get the PMV dict and check to be sure the air speed is less than fan speed
        sat = self._comfort_par.still_air_threshold
        _, pmv_max = pmv_from_ppd(self._comfort_par.ppd_comfort_thresh) if \
            self._comfort_par.ppd_comfort_thresh != 10 else (-0.5, 0.5)
        pmv_dict = self._pmv_dict(max_i)
        if pmv_dict['vel'] >= air_speed:  # comfort air speed too fast
            return None

        # compute the air temperatures and HR when the fan speed is higher
        pmv_dict['vel'] = air_speed
        pr = self.psychrometric_chart.average_pressure
        rel_humids = (0, 20, 40, 60, 80, 100)
        air_temps = []
        for rh in rel_humids:
            pmv_dict['rh'] = rh
            max_dict = calc_missing_pmv_input(pmv_max, pmv_dict, still_air_threshold=sat)
            air_temps.append(max_dict['ta'])
        hr = [humid_ratio_from_db_rh(t, rh, pr) for t, rh in zip(air_temps, rel_humids)]

        # convert the air temperatures and HR to a polyline
        psy, right_pts = self.psychrometric_chart, []
        for h, ta in zip(hr, air_temps):
            ta = ta if not psy.use_ip else self.TEMP_TYPE.to_unit([ta], 'F', 'C')[0]
            right_pts.append(Point2D(psy.t_x_value(ta), psy.hr_y_value(h)))
        right = Polyline2D(right_pts, interpolated=True)

        # trim the polyline top (and bottom if necessary)
        left = comf_poly[2].reverse()
        ray = Ray2D(left[0], Vector2D(1, 0))
        right = self._intersect_top(right, ray)
        if self._comfort_par.humid_ratio_lower != 0:
            ray = Ray2D(left[-1], Vector2D(1, 0))
            right = self._intersect_bottom(right, ray)

        # put everything together into one list
        bottom = LineSegment2D.from_end_points(left[-1], right[0])
        top = LineSegment2D.from_end_points(right[-1], left[0])
        return (left, bottom, right, top)

    def night_flush_polygon(self, temperature_above_comfort=12):
        """Get a tuple of Polyline2D and LineSegment2D for a night flushing polygon.

        This will be None if the polygon does not fit on the chart.

        Args:
            temperature_above_comfort: A number in degrees Celsius representing the
                maximum daily temperature above the comfort range which can still
                be counted in the Night Flush polygon. (Default: 12 C).
        """
        # check to be sure the night flush polygon fits on the chart
        if self.is_comfort_too_hot:
            return None
        psy = self._psychrometric_chart
        left = self.merged_comfort_polygon[2]

        # move the left line over by the temperature above comfort
        tac = temperature_above_comfort if not psy.use_ip else \
            self.DELTA_TEMP_TYPE.to_unit([temperature_above_comfort], 'dF', 'dC')[0]
        move_vec = Vector2D(tac * psy.x_dim, 0)
        right = left.move(move_vec)
        left = left.reverse()

        # trim or simplify the right line if it is off of the chart
        m_x = psy.base_point.x + (psy.max_temperature - psy.min_temperature) * psy.x_dim
        ex_line = None
        if right[-1].x > m_x:  # polygon off the chart; recreate it
            p1, p2 = Point2D(m_x, left[-1].y), Point2D(m_x, left[0].y)
            right = LineSegment2D.from_end_points(p1, p2)
            right = Polyline2D((right.p1, right.midpoint, right.p2))
        elif right[0].x > m_x:  # polygon partially off the chart; trim it
            border_seg = psy.chart_border.segments[2]
            b_pt = right.intersect_line_ray(border_seg)[0]
            ray = Ray2D(Point2D(left[0].x, b_pt.y), Vector2D(1, 0))
            right = self._intersect_bottom(right, ray)
            ex_line = LineSegment2D.from_end_points(Point2D(m_x, left[-1].y), right[0])

        # assemble everything into one list of polylines
        nf_lines = [left]
        if ex_line is not None:
            nf_lines.append(LineSegment2D.from_end_points(left[-1], ex_line.p1))
            nf_lines.append(ex_line)
        else:
            nf_lines.append(LineSegment2D.from_end_points(left[-1], right[0]))
        nf_lines.append(right)
        nf_lines.append(LineSegment2D.from_end_points(right[-1], left[0]))
        return tuple(nf_lines)

    def internal_heat_polygon(self, balance_temperature=12.8):
        """Get a tuple of Polyline2D and LineSegment2D for an internal heat gain polygon.

        This will be None if the polygon does not fit on the chart.

        Args:
            balance_temperature: The balance temperature of the building in Celsius when
                accounting for all internal heat. Must be greater or equal to 5 C.
                In order for this method to not return None, this value must be
                less than the coldest temperature of the merged comfort
                polygon. (Default: 12.8 C)
        """
        # check to be sure the internal heat polygon fits on the chart
        self._balance_check(balance_temperature)
        psy = self._psychrometric_chart
        comf_poly = self.merged_comfort_polygon
        bal = balance_temperature if not psy.use_ip else \
            self.TEMP_TYPE.to_unit([balance_temperature], 'F', 'C')[0]
        bal_x = psy.t_x_value(bal)
        if self.is_comfort_too_cold or comf_poly[0][0].x < bal_x:
            return None

        # get the vertical line at the balance point
        if psy.min_temperature <= bal:  # the whole polygon fits on the chart
            hr_e = humid_ratio_from_db_rh(balance_temperature, 100, psy.average_pressure)
            hr_y = psy.hr_y_value(hr_e)
            hr_y = hr_y if hr_y < comf_poly[0][0].y else comf_poly[0][0].y
            left1 = Point2D(bal_x, hr_y)
            left2 = Point2D(bal_x, comf_poly[0][-1].y)
        else:
            _, min_tc = self._x_to_t(psy.base_point.x)
            hr_e = humid_ratio_from_db_rh(min_tc, 100, psy.average_pressure)
            hr_y = psy.hr_y_value(hr_e)
            hr_y = hr_y if hr_y < comf_poly[0][0].y else comf_poly[0][0].y
            left1 = Point2D(psy.basepoint.x, hr_y)
            left2 = Point2D(psy.basepoint.x, comf_poly[0][-1].y)
        left_lin = LineSegment2D.from_end_points(left1, left2)

        # get the bottom line and the line bordering the comfort polygon
        bot_lin = LineSegment2D.from_end_points(left_lin.p2, comf_poly[0][-1])
        right_lin = comf_poly[0].reverse()
        inht_lines = [left_lin, bot_lin, right_lin]

        # get the last line, which may intersect with the saturation line
        if left_lin.p1.y == comf_poly[0][0].y:  # straight line across
            top_lin = LineSegment2D.from_end_points(comf_poly[0][0], left_lin.p1)
            inht_lines.append(top_lin)
        else:  # polygon includes some of the saturation line
            l_comf_pt = self.left_comfort_line[-1]
            x_mid = (left_lin.p1.x + l_comf_pt.x) / 2
            t_mid, t_mid_c = self._x_to_t(x_mid)
            hr_mid = humid_ratio_from_db_rh(t_mid_c, 100, psy.average_pressure)
            mx, my = psy.t_x_value(t_mid), psy.hr_y_value(hr_mid)
            sat_line = Polyline2D((left_lin.p1, Point2D(mx, my), l_comf_pt),
                                  interpolated=True)
            if comf_poly[0][0].y == l_comf_pt.y:  # sat line only
                inht_lines.append(sat_line.reverse())
            else:  # sat line gets split with the max HR
                max_hr_y = psy.hr_y_value(self._comfort_par.humid_ratio_upper)
                left_x = psy.base_point.x - 100 * psy.x_dim
                ray = Ray2D(Point2D(left_x, max_hr_y), Vector2D(1, 0))
                sat_line = self._intersect_top(sat_line, ray)
                intpt = sat_line[-1] if isinstance(sat_line, Polyline2D) else sat_line.p2
                inht_lines.append(LineSegment2D.from_end_points(right_lin[-1], intpt))
                sat_line = sat_line.reverse() if isinstance(sat_line, Polyline2D) \
                    else sat_line.flip()
                inht_lines.append(sat_line)
        return tuple(inht_lines)

    def passive_solar_polygon(self, max_temperature_delta, balance_temperature=None):
        """Get a tuple of Polyline2D and LineSegment2D for a passive solar polygon.

        This will be None if the polygon does not fit on the chart.

        Args:
            max_temperature_delta: The maximum temperature delta from the balance
                temperature (in Celsius) that passive solar heating is able to
                support. This can be obtained by running the evaluate_passive_solar
                method on this class
            balance_temperature: The balance temperature of the building in Celsius when
                accounting for all internal heat. Must be greater or equal to 5 C.
                If None, it will be assumed that the passively-heated space has no
                internal heat gains and all passive solar potential will be evaluated
                from the coldest comfort temperature. (Default: None).
        """
        # check that the passive solar polygon will fit on the chart
        psy = self._psychrometric_chart
        pres = psy.average_pressure
        comf_poly = self.merged_comfort_polygon
        bal_temp = balance_temperature if balance_temperature is not None else \
            self._x_to_t(comf_poly[0][-1].x)[1]
        if balance_temperature is None and bal_temp < 5:
            return None
        self._balance_check(bal_temp)
        bal = bal_temp if not psy.use_ip else \
            self.TEMP_TYPE.to_unit([bal_temp], 'F', 'C')[0]
        min_sol_t = bal_temp - max_temperature_delta
        min_sol_t = min_sol_t if not psy.use_ip else \
            self.TEMP_TYPE.to_unit([min_sol_t], 'F', 'C')[0]
        min_sol_t = min_sol_t if min_sol_t > psy.min_temperature else psy.min_temperature
        min_sol_x = psy.t_x_value(min_sol_t)
        min_sol_t_c = min_sol_t if not psy.use_ip else \
            self.TEMP_TYPE.to_unit([min_sol_t], 'C', 'F')[0]
        if self.is_comfort_too_cold or comf_poly[0][0].x < min_sol_x or \
                psy.min_temperature >= bal:
            return None

        # get the polyline for the right of the polygon
        bal_x, need_connect = psy.t_x_value(bal), True
        if balance_temperature is None or comf_poly[0][0].x < bal_x:
            right = comf_poly[0].reverse()
            if comf_poly[0][0].y == self.left_comfort_line[-1].y:
                need_connect = False
        else:  # there's a single vertical line for the right of the polygon
            hr_e = humid_ratio_from_db_rh(balance_temperature, 100, pres)
            hr_y = psy.hr_y_value(hr_e)
            if hr_y < comf_poly[0][0].y:
                need_connect = False
            else:
                hr_y = comf_poly[0][0].y
            r1, r2 = Point2D(bal_x, comf_poly[0][-1].y), Point2D(bal_x, hr_y)
            right = LineSegment2D.from_end_points(r1, r2)
            right = Polyline2D((right.p1, right.midpoint, right.p2))
        sol_lines = [right]

        # create the connector line to the saturation line if its needed
        need_sat = True
        if need_connect:
            hr = self._y_to_hr(right[-1].y)
            sat_int_c = db_temp_from_rh_hr(100, hr, pres)
            sat_int = sat_int_c if not psy.use_ip else \
                self.TEMP_TYPE.to_unit([sat_int_c], 'F', 'C')[0]
            if sat_int < min_sol_t:  # we don't make it to the saturation line
                need_sat = False
                t1, t2 = right[-1], Point2D(min_sol_x, right[-1].y)
            else:
                sat_int_x = psy.t_x_value(sat_int)
                t1, t2 = right[-1], Point2D(sat_int_x, right[-1].y)
            sol_lines.append(LineSegment2D.from_end_points(t1, t2))

        # create the left line if it fits (or get the saturation line intersect)
        left, int_pt = None, None
        if need_sat:
            hr_l = humid_ratio_from_db_rh(min_sol_t_c, 100, pres)
            min_hr = self._comfort_par.humid_ratio_lower
            if hr_l > min_hr:  # left line exists
                l1 = Point2D(min_sol_x, psy.hr_y_value(hr_l))
                l2 = Point2D(min_sol_x, right[0].y)
                left = LineSegment2D.from_end_points(l1, l2)
            else:  # left line does not exist; determine the intersection
                int_t_c = db_temp_from_rh_hr(100, min_hr, pres)
                int_t = int_t_c if not psy.use_ip else \
                    self.TEMP_TYPE.to_unit([int_t_c], 'F', 'C')[0]
                int_pt = Point2D(psy.t_x_value(int_t), psy.hr_y_value(min_hr))
        else:  # no intersection with the saturation line
            l1, l2 = sol_lines[-1].p2, Point2D(sol_lines[-1].p2.x, right[0].y)
            left = LineSegment2D.from_end_points(l1, l2)

        # create the portion against the saturation line if its needed
        if need_sat:
            r_pt = sol_lines[-1].p2 if isinstance(sol_lines[-1], LineSegment2D) \
                else sol_lines[-1][-1]
            l_pt = left.p1 if left is not None else int_pt
            x_mid = (l_pt.x + r_pt.x) / 2
            t_mid, t_mid_c = self._x_to_t(x_mid)
            hr_mid = humid_ratio_from_db_rh(t_mid_c, 100, pres)
            mx, my = psy.t_x_value(t_mid), psy.hr_y_value(hr_mid)
            sat_line = Polyline2D((r_pt, Point2D(mx, my), l_pt), interpolated=True)
            sol_lines.append(sat_line)
        if left is not None:
            sol_lines.append(left)

        # create the bottom line
        l_pt = sol_lines[-1].p2 if isinstance(sol_lines[-1], LineSegment2D) \
            else sol_lines[-1][-1]
        sol_lines.append(LineSegment2D.from_end_points(l_pt, right[0]))
        return sol_lines

    def evaluate_polygon(self, polygon, tolerance=0.01):
        """Evaluate a strategy polygon in relation to the data points of the chart.

        Args:
            polygon: A tuple of Polyline2D and LineSegment2D that form a closed
                polygon on the psychrometric chart.
            tolerance: The minimum difference between vertices below which vertices
                are considered the same. (Default: 0.01).

        Returns:
            A list of 0 and 1 values for whether data points lie inside the polygon.
            These can be passed to the create_collection method on this class to
            get a data collection for the time inside the polygon.
        """
        joined_poly = self._lines_to_polygon(polygon, tolerance)  # get a joined polygon
        # create a list of all points in the polygon
        value_list = []
        for point in self._psychrometric_chart.data_points:
            val = 1 if joined_poly.is_point_inside_bound_rect(point) else 0
            value_list.append(val)
        return value_list

    def evaluate_night_flush_polygon(self, polygon, outdoor_temperature,
                                     night_below_comfort=3.0, time_constant=8,
                                     tolerance=0.01):
        """Evaluate the night flush strategy polygon in relation to the data points.

        Args:
            polygon: A tuple of Polyline2D and LineSegment2D that form a closed
                polygon on the psychrometric chart for the night flushing polygon.
            outdoor_temperature: An annual hourly continuous data collection of
                outdoor temperature in Celsius, which will be used to evaluate if
                previous hours are cool enough to benefit from night flushing.
            night_below_comfort: A number in degrees Celsius representing the minimum
                temperature below the maximum comfort temperature that the outdoor
                temperature must drop at night in order to count towards the Night
                Flush polygon. (Default: 3C).
            time_constant: A number that represents the number of hours that a
                theoretical building can passively maintain its temperature. This
                is used to determine how many hours a space can maintain the coolth
                of the night_below_comfort before conditions drive it out of the
                comfort polygon. The better-insulated a building is and the higher
                its thermal mass, the greater this number can be.
            tolerance: The minimum difference between vertices below which vertices
                are considered the same. (Default: 0.01).
        """
        # check to be sure that the data is hourly continuous
        psy = self.psychrometric_chart
        joined_poly = self._lines_to_polygon(polygon, tolerance)  # get a joined polygon
        temp_vals = psy._t_values_c  # all temperatures on the chart
        if len(temp_vals) == 1:
            val = 1 if joined_poly.is_point_inside_bound_rect(psy.data_points[0]) \
                else 0
            return [val]
        else:  # make sure the collection is hourly continuous
            time_ind = self._check_hourly(outdoor_temperature, 'Night Flushing')
            tcon_i = time_constant * outdoor_temperature.header.analysis_period.timestep

        # calculate the target temperature to hit at night for flushing
        right = self.merged_comfort_polygon[2]
        avg_x = (right[0].x + right[0].x) / 2
        _, max_t_c = self._x_to_t(avg_x)
        target_temp = max_t_c - night_below_comfort  # night temperature ok to flush

        # create a list of all points in the polygon
        value_list = []
        for hour, point in zip(time_ind, psy.data_points):
            if joined_poly.is_point_inside_bound_rect(point):
                for past_temp in outdoor_temperature[hour - tcon_i:hour]:
                    if past_temp < target_temp:
                        value_list.append(1)
                        break
                else:
                    value_list.append(0)
            else:
                value_list.append(0)
        return value_list

    def evaluate_passive_solar(self, incident_irradiance, solar_heat_capacity=50,
                               time_constant=8, balance_temperature=None):
        """Evaluate the psychrometric chart data points in relation to passive heating.

        Args:
            incident_irradiance: An annual hourly continuous data collection of
                irradiance (or radiation) in W/m2 (or Wh/m2) that aligns with the data
                points on the psychrometric chart. The irradiance values
                should be incident on the orientation of the passive solar heated
                windows. So using global horizontal radiation assumes that all
                windows are skylights (like a greenhouse). The directional_irradiance
                method on the ladybug core Wea class can be used to get irradiance
                data for a specific surface orientation.
            solar_heat_capacity: A number representing the amount of outdoor solar flux
                (W/m2) that is needed to raise the temperature of a theoretical building
                by 1 degree Celsius. The lower this number, the more efficiently the
                space is able to absorb passive solar heat. The default assumes a
                relatively small passively solar heated zone without much mass. A
                higher number will be required the larger the space is and the more
                mass that it has. (Default: 50 W/m2)
            time_constant: A number that represents the number of hours that a
                theoretical building can passively maintain its temperature. This
                is used to determine how many hours a space can maintain the warmth
                of the sun before conditions drive it out of the comfort polygon.
                The better-insulated a building is and the higher its thermal mass,
                the greater this number can be. (Default: 8).
            balance_temperature: The balance temperature of the building in Celsius when
                accounting for all internal heat. Must be greater or equal to 5 C.
                If None, it will be assumed that the passively-heated space has no
                internal heat gains and all passive solar potential will be evaluated
                from the coldest comfort temperature. (Default: None).

        Returns:
            A tuple of two values. The first is a list of 0/1 values for whether the
            data points can be passively solar heated. The second is the maximum
            temperature delta from the balance_temperature (in Celsius) that the
            passive solar heating was able to support.
        """
        # check the building balance temperature
        psy = self._psychrometric_chart
        comf_poly = self.merged_comfort_polygon
        bal_temp = balance_temperature if balance_temperature is not None else \
            self._x_to_t(comf_poly[0][-1].x)[1]
        bal_temp = 5 if bal_temp < 5 else bal_temp

        # check that the data is hourly continuous
        temp_vals = psy._t_values_c  # all temperatures on the chart
        comf_val = self.merged_comfort_values
        if len(temp_vals) == 1:
            t = temp_vals[0]
            val = 1 if bal_temp - 20 < t < bal_temp and comf_val[0] == 0 else 0
            return([val]), 20
        else:  # make sure the collection is hourly continuous
            time_ind = self._check_hourly(incident_irradiance, 'Passive Solar')
            tcon_i = time_constant * incident_irradiance.header.analysis_period.timestep

        # get a list of booleans that account for the HR limits
        if self._comfort_par.humid_ratio_lower == 0:
            hr_in_range = [True] * psy._calc_length
        else:
            min_hr_y, hr_in_range = comf_poly[0][-1].y, []
            for pt in psy.data_points:
                hr_ok = True if pt.y > min_hr_y else False
                hr_in_range.append(hr_ok)
        if comf_poly[0][0].y != self.left_comfort_line[-1]:  # max HR in effect
            max_hr_y = comf_poly[0][0].y
            for i, pt in enumerate(psy.data_points):
                if pt.y > max_hr_y:
                    hr_in_range[i] = False

        # loop through the data and determine if the point can be passively heated
        deltas, value_list = [], []
        for temp, comf, hr_ok, hour in zip(temp_vals, comf_val, hr_in_range, time_ind):
            if comf == 0 and hr_ok and temp <= bal_temp:
                # compute the total amount of solar heat over the time constant
                past_rad = incident_irradiance[hour - tcon_i:hour]
                solar_heat_contribs = [rad * ((i + 1) / time_constant)
                                       for i, rad in enumerate(past_rad)]
                # see if enough solar heat has collected in the space to overcome delta t
                temp_delta = bal_temp - temp
                if sum(solar_heat_contribs) > solar_heat_capacity * temp_delta:
                    deltas.append(temp_delta)
                    value_list.append(1)
                else:
                    value_list.append(0)
            else:  # the conditions are too warm to be in the polygon
                value_list.append(0)
        max_delta = max(deltas) if len(deltas) != 0 else 20
        return value_list, max_delta

    def comfort_polylines(self, polygon_index):
        """Get the left and right Polyline2D that define a PMV polygon comfort range.

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
        # get the PPD thresholds and PMV dict
        sat = self._comfort_par.still_air_threshold
        pmv_min, pmv_max = pmv_from_ppd(self._comfort_par.ppd_comfort_thresh) if \
            self._comfort_par.ppd_comfort_thresh != 10 else (-0.5, 0.5)
        pmv_dict = self._pmv_dict(polygon_index)

        # compute the min and max air temperatures of relative humidity
        air_temperatures = []
        for rh in rel_humid:
            pmv_dict['rh'] = rh
            min_dict = calc_missing_pmv_input(pmv_min, pmv_dict, still_air_threshold=sat)
            max_dict = calc_missing_pmv_input(pmv_max, pmv_dict, still_air_threshold=sat)
            air_temperatures.append((min_dict['ta'], max_dict['ta']))
        return air_temperatures

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
        # create the saturation line if it will be required
        psy = self.psychrometric_chart
        max_hr_y = psy.hr_y_value(self._comfort_par.humid_ratio_upper)
        if max_hr_y >= left[-1].y:
            x_mid = (left[-1].x + right[-1].x) / 2
            t_mid, t_mid_c = self._x_to_t(x_mid)
            hr_mid = humid_ratio_from_db_rh(t_mid_c, 100, psy.average_pressure)
            mx, my = psy.t_x_value(t_mid), psy.hr_y_value(hr_mid)
            sat_line = Polyline2D((left[-1], Point2D(mx, my), right[-1]),
                                  interpolated=True)

        # clip the left and right comfort lines if there are max and min HR
        left_x = psy.base_point.x - 100 * psy.x_dim
        right_y = right[-1].y
        if self._comfort_par.humid_ratio_lower != 0:
            min_hr_y = psy.hr_y_value(self._comfort_par.humid_ratio_lower)
            if min_hr_y >= left[-1].y:
                raise ValueError(
                    'humid_ratio_lower is too high for a comfort polygon in such cold '
                    'temperatures.\nRaise the humid_ratio_lower to see the comfort '
                    'polygon.')
            ray = Ray2D(Point2D(left_x, min_hr_y), Vector2D(1, 0))
            left = self._intersect_bottom(left, ray)
            right = self._intersect_bottom(right, ray)
        if max_hr_y < right_y:  # trim the polylines with the max/min HR
            ray = Ray2D(Point2D(left_x, max_hr_y), Vector2D(1, 0))
            left = self._intersect_top(left, ray)
            right = self._intersect_top(right, ray)

        # create the bottom of the comfort polygon
        comf_polygon = [left.reverse()]
        comf_polygon.append(LineSegment2D.from_end_points(left[0], right[0]))

        # create the top of the comfort polygon
        comf_polygon.append(right)
        if max_hr_y <= left[-1].y:
            comf_polygon.append(LineSegment2D.from_end_points(right[-1], left[-1]))
        elif max_hr_y < right_y:
            sat_line = self._intersect_top(sat_line, ray)
            int_pt = sat_line[-1] if isinstance(sat_line, Polyline2D) else sat_line.p2
            comf_polygon.append(LineSegment2D.from_end_points(right[-1], int_pt))
            comf_polygon.append(sat_line)
        else:
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

    def _pmv_dict(self, polygon_index):
        """Get a PMV dictionary for on set of inputs."""
        return {'ta': None,
                'tr': self._rad_temperature[polygon_index],
                'vel': self._air_speed[polygon_index],
                'met': self._met_rate[polygon_index],
                'clo': self._clo_value[polygon_index],
                'wme': self._external_work[polygon_index]}

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

    def _check_hourly(self, data, strategy_name):
        """Check data on the psych chart originates from a hourly collection.

        Args:
            data: The data that is being evaluated against the psychrometric chart
                data points.
            strategy_name: The name of the strategy that's being evaluated.

        Returns:
            A tuple of indices for which hours of the input data correspond to the
            psychrometric chart data points.
        """
        # check the input data first
        assert isinstance(data, HourlyContinuousCollection), '{} ' \
            'data must be hourly and continuous.'.format(strategy_name)
        assert data.header.analysis_period.is_annual, '{} ' \
            'data must be annual.'.format(strategy_name)
        # check the data in relation to the psychrometric chart data
        psy = self.psychrometric_chart
        coll = psy.temperature if isinstance(psy.temperature, BaseCollection) \
            else psy.relative_humidity
        accept = (HourlyContinuousCollection, HourlyDiscontinuousCollection)
        assert isinstance(coll, accept), 'Psychrometric chart ' \
            'data must be hourly to evaluate {}.'.format(strategy_name)
        a_per = coll.header.analysis_period
        t_step = a_per.timestep
        assert coll.header.analysis_period.timestep == t_step, '{} data' \
            'timestep must be the same as data on the psych chart.'.format(strategy_name)
        # get the indices of psych chart data to compare with strategy data
        if isinstance(coll, HourlyContinuousCollection):
            return tuple(int(hr * t_step) for hr in a_per.hoys)
        else:
            return tuple(int(dt.hoy * t_step) for dt in coll.datetimes)

    @staticmethod
    def _balance_check(balance_temperature):
        """Check to see if a building balance temperature is acceptable."""
        assert balance_temperature >= 5, 'balance_temperature must be greater than or ' \
            'equal to 5 C in order to be drawn correctly and reasonably represent a ' \
            'real building.'

    @staticmethod
    def _lines_to_polygon(polygon, tolerance):
        """Convert a list of Polyline2D and LineSegment2D to a single Polygon2D."""
        all_segs = []
        for obj in polygon:
            if isinstance(obj, Polyline2D):
                all_segs.extend(obj.segments)
            else:
                all_segs.append(obj)
        joined_segs = Polyline2D.join_segments(all_segs, tolerance)[0]
        return joined_segs.to_polygon(tolerance)

    @staticmethod
    def _intersect_bottom(polyline, ray):
        """Intersect a Polyline2D on the bottom."""
        min_dist = polyline[0].distance_to_point(polyline[1]) / 4
        for i, _s in enumerate(polyline.segments):
            inters = intersect_line2d_infinite(_s, ray)
            if inters is not None:
                if inters.distance_to_point(polyline[i + 1]) > min_dist:
                    verts = (inters,) + polyline.vertices[i + 1:]
                else:  # avoid a bad interpolation
                    end_v = polyline.vertices[i + 2:]
                    verts = (inters,) + end_v if len(end_v) != 0 else \
                        (inters,) + polyline.vertices[i + 1:]
                polyline = Polyline2D(verts, interpolated=True) if len(verts) != 2 else \
                    LineSegment2D.from_end_points(verts[0], verts[1])
                break
        if isinstance(polyline, LineSegment2D):
            polyline = Polyline2D((polyline.p1, polyline.midpoint, polyline.p2))
        return polyline

    @staticmethod
    def _intersect_top(polyline, ray):
        """Intersect a Polyline2D on the top."""
        min_dist = polyline[0].distance_to_point(polyline[1]) / 4
        verts = [polyline[0]]
        for i, _s in enumerate(polyline.segments):
            inters = intersect_line2d_infinite(_s, ray)
            if inters is None:
                verts.append(polyline[i + 1])
            else:
                if len(verts) == 1 or inters.distance_to_point(verts[-1]) > min_dist:
                    verts.append(inters)
                else:  # avoid a bad interpolation
                    verts[-1] = inters
                break
        polyline = Polyline2D(verts, interpolated=True) if len(verts) != 2 else \
            LineSegment2D.from_end_points(verts[0], verts[1])
        if isinstance(polyline, LineSegment2D):
            polyline = Polyline2D((polyline.p1, polyline.midpoint, polyline.p2))
        return polyline

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

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """PolygonPMV representation."""
        return "Polygon PMV: ({} Polygons)".format(self._polygon_count)
