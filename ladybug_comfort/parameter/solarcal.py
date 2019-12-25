# coding=utf-8
"""Parameters for specifying body characteristics for the SolarCal model."""
from __future__ import division

from ._base import ComfortParameter
from ..solarcal import sharp_from_solar_and_body_azimuth


class SolarCalParameter(ComfortParameter):
    """Parameters specifying body characteristics for the SolarCal model.

    Properties:
        posture
        sharp
        body_azimuth
        body_absorptivity
        body_emissivity
    """
    _model = 'SolarCal'
    POSTURES = ('standing', 'seated', 'supine')
    __slots__ = ('_posture', '_sharp', '_body_azimuth', '_body_absorptivity',
                 '_body_emissivity')

    def __init__(self, posture=None, sharp=None, body_azimuth=None,
                 body_absorptivity=None, body_emissivity=None):
        """Initalize SolarCal Body Parameters.

        Args:
            posture: A text string indicating the posture of the body. Letters must
                be lowercase.  Choose from the following: "standing", "seated", "supine".
                Default is "standing".
            sharp: A number between 0 and 180 representing the solar horizontal
                angle relative to front of person (SHARP). 0 signifies sun that is
                shining directly into the person's face and 180 signifies sun that
                is shining at the person's back. Default is 135, asuming that a person
                typically faces their side or back to the sun to avoid glare.
            body_azimuth: A number (between 0 and 360) representing the direction that
                the human is facing in degrees (0=North, 90=East, 180=South, 270=West).
                If this number is greater than 360 or less than 0, it will be converted
                to the correct angle within this range.
                Default is None, which will assume that the sharp input dictates the
                degrees the human is facing from the sun.
            body_absorptivity: A number between 0 and 1 representing the average
                shortwave absorptivity of the body (including clothing and skin color).
                Typical clothing values - white: 0.2, khaki: 0.57, black: 0.88
                Typical skin values - white: 0.57, brown: 0.65, black: 0.84
                Default is 0.7 for average (brown) skin and medium clothing.
            body_emissivity: A number between 0 and 1 representing the average
                longwave emissivity of the body.  Default is 0.95, which is almost
                always the case except in rare situations of wearing metalic clothing.
        """
        if posture is not None:
            assert isinstance(posture, str), 'posture must be a string.'\
                ' Got {}'.format(type(posture))
            assert posture.lower() in self.POSTURES, 'posture {} is not '\
                'acceptable. Choose from {}'.format(posture, self.POSTURES)
            self._posture = posture
        else:
            self._posture = 'standing'

        if sharp is not None and body_azimuth is not None:
            raise TypeError('sharp and body_azimuth are mutually exclusive.\n'
                            'You may specify one or the other but not both.\n'
                            'Set one of them to None.')
        elif body_azimuth is not None:
            if body_azimuth > 360:
                while body_azimuth > 360:
                    body_azimuth = body_azimuth - 360
            elif body_azimuth < 0:
                while body_azimuth < 0:
                    body_azimuth = body_azimuth + 360
            self._sharp = None
            self._body_azimuth = body_azimuth
        elif sharp is not None:
            assert 0 <= sharp <= 180, 'sharp must be between 0 and 180.'\
                ' Got {}'.format(sharp)
            self._sharp = sharp
            self._body_azimuth = None
        else:
            self._sharp = 135
            self._body_azimuth = None

        if body_absorptivity is not None:
            assert 0 <= body_absorptivity <= 1, 'body_absorptivity must be between'\
                ' 0 and 1. Got {}'.format(body_absorptivity)
            self._body_absorptivity = body_absorptivity
        else:
            self._body_absorptivity = 0.7

        if body_emissivity is not None:
            assert 0 <= body_emissivity <= 1, 'body_emissivity must be between'\
                ' 0 and 1. Got {}'.format(body_emissivity)
            self._body_emissivity = body_emissivity
        else:
            self._body_emissivity = 0.95

    @property
    def posture(self):
        """A text string indicating the posture of the body."""
        return self._posture

    @property
    def sharp(self):
        """The solar horizontal angle relative to front of person (SHARP).

        Between 0 and 180. 0 signifies sun that is shining directly into the person's
        face and 180 signifies sun that is shining at the person's back."""
        return self._sharp

    @property
    def body_azimuth(self):
        """Number representing the direction that the human is facing in degrees.

        Between 0 and 360. 0=North, 90=East, 180=South, 270=West."""
        return self._body_azimuth

    @property
    def body_absorptivity(self):
        """Number representing the average shortwave absorptivity of the body.

        Between 0 and 1. Includes clothing and skin color."""
        return self._body_absorptivity

    @property
    def body_emissivity(self):
        """Number representing the average longwave emissivity of the body.

        Between 0 and 1. Typically 0.95."""
        return self._body_emissivity

    def get_sharp(self, solar_azimuth):
        if self.sharp is not None:
            return self.sharp
        return sharp_from_solar_and_body_azimuth(solar_azimuth, self.body_azimuth)

    def duplicate(self):
        """Duplicate SolarCal Parameters."""
        return SolarCalParameter(self.posture, self.sharp, self.body_azimuth,
                                 self.body_absorptivity, self.body_emissivity)

    def __repr__(self):
        """SolarCal body parameters representation."""
        if self.sharp is not None:
            return "SolarCal Body Parameters\n Posture: {}\n SHARP: {}"\
                "\n Body Absortivity: {}\n Body Emissivity: {}".format(
                    self.posture, self.sharp, self.body_absorptivity,
                    self.body_emissivity)
        else:
            return "SolarCal Body Parameters\n Posture: {}\n Body Azimuth: {}"\
                "\n Body Absortivity: {}\n Body Emissivity: {}".format(
                    self.posture, self.body_azimuth, self.body_absorptivity,
                    self.body_emissivity)
