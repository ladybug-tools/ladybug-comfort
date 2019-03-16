# coding=utf-8
"""Comfort data collection base object."""

from ladybug._datacollectionbase import BaseCollection
from  ladybug.datatype.base import DataTypeBase


class ComfortCollection(object):
    """Thermal comfort datacollection base class."""
    _model = None

    def __init__(self):
        self._calc_length = 0
        self._base_collection = None
        self._input_collections = []

    @property
    def comfort_model(self):
        """Return the name of the model to which the comfort datacollection belongs."""
        return self._model

    @property
    def calc_length(self):
        """The number of values in the Data Collections of this object."""
        return self._calc_length

    def _check_datacoll(self, data_coll, dat_type, unit, name):
        """Check the data type and units of a Data Collection."""
        assert isinstance(data_coll, BaseCollection), '{} must be a ' \
            'Data Collection. Got {}.'.format(name, type(data_coll))
        assert isinstance(data_coll.header.data_type, dat_type) and \
            data_coll.header.unit == unit, '{} must be {} in {}. ' \
            'Got {} in {}'.format(name, dat_type().name, unit,
                                  data_coll.header.data_type.name,
                                  data_coll.header.unit)

    def _check_input(self, data_coll, dat_type, unit, name):
        """Check the a Data Collection."""
        if isinstance(data_coll, BaseCollection):
            self._check_datacoll(data_coll, dat_type, unit, name)
            self._input_collections.append(data_coll)
            return data_coll.values
        else:
            try:
                return [float(data_coll)] * self.calc_length
            except ValueError:
                raise TypeError('{} must be either a number or a Data Colleciton. '
                                'Got {}'.format(name, type(data_coll)))

    def _get_coll(self, attr_name, value_list, dat_type, unit):
        if not hasattr(self, attr_name):
            if callable(value_list):
                value_list = value_list()  # get values if passed a function
            if not isinstance(dat_type, DataTypeBase):
                dat_type = dat_type()  # convert the class to an instance
            coll = self._base_collection.get_aligned_collection(
                value_list, dat_type, unit, mutable=False)
            setattr(self, attr_name, coll)
        return getattr(self, attr_name)

    @property
    def isComfortCollection(self):
        """The number of values in the Data Collections of this object."""
        return self._calc_length

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """Comfort model representation."""
        return "{} ComfortCollection [{} values]".format(
            self.comfort_model, self._calc_length)
