# coding=utf-8
"""Comfort datacollection base object."""


class ComfortDataCollection(object):
    """Thermal comfort datacollection base class."""
    _model = None

    def __init__(self):
        self._calc_length = 0

    @property
    def comfort_model(self):
        """Return the name of the model to which the comfort datacollection belongs."""
        return self._model

    @property
    def calc_length(self):
        """The number of values in the Data Collections of this object."""
        return self._calc_length

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """Comfort model representation."""
        return "{} Comfort Model\n{} values".format(
            self.comfort_model, self._calc_length)
