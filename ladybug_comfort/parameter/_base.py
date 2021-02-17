# coding=utf-8
"""Comfort parameter base object."""


class ComfortParameter(object):
    """Thermal comfort parameter base class."""
    _model = None
    __slots__ = ()

    @property
    def comfort_model(self):
        """Return the name of the comfort model to which the parameters belong."""
        return self._model

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()
