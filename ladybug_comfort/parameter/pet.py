# coding=utf-8
"""Parameters for specifying body characteristics for the PET model."""
from __future__ import division
import re

from ._base import ComfortParameter


class PETParameter(ComfortParameter):
    """Parameters specifying body characteristics for the PET model.

    Args:
        age: The age of the human subject in years. (Default: 36 years for middle age
            of the average worldwide life expectancy).
        sex: A value between 0 and 1 to indicate the sex of the human subject,
            which influences the computation of basal metabolism. 0 indicates male.
            1 indicates female and any number in between denotes a weighted average
            between the two. (Default: 0.5).
        height: The height of the human subject in meters. Average male height
            is around 1.75m while average female height is 1.55m. (Default: 1.65m
            for a worldwide average between male and female height).
        body_mass: The body mass of the human subject in kilograms. (Default: 62 kg
            for the worldwide average adult human body mass).
        posture: A text string indicating the posture of the body. Letters must
            be lowercase. Default is "standing". Choose from the following:

            * standing
            * seated
            * crouching

        humid_acclimated: A boolean to note whether the human subject is acclimated
            to a humid/tropical climate (True) or is acclimated to a temperate
            climate (False). When True, the categories developed by Lin and
            Matzarakis (2008) will be used to assess comfort instead of the original
            categories developed by Matzarakis and Mayer (1996).

    Properties:
        * age
        * sex
        * height
        * body_mass
        * posture
        * humid_acclimated
    """
    _model = 'Physiological Equivalent Temperature'
    POSTURES = ('standing', 'seated', 'crouching')
    __slots__ = ('_age', '_sex', '_height', '_body_mass', '_posture',
                 '_humid_acclimated')

    def __init__(self, age=None, sex=None, height=None, body_mass=None,
                 posture=None, humid_acclimated=False):
        """Initialize PET Body Parameters."""
        if age is not None:
            assert 0 <= age <= 120, 'Age must be between 0 and 120. Got {}'.format(age)
            self._age = age
        else:
            self._age = 36

        if sex is not None:
            assert 0 <= sex <= 1, 'Sex must be between 0 and 1. Got {}'.format(sex)
            self._sex = sex
        else:
            self._sex = 0.5

        if height is not None:
            assert 0.6 <= height <= 3, \
                'Height must be between 0.6 and 3. Got {}'.format(height)
            self._height = height
        else:
            self._height = 1.65

        if body_mass is not None:
            assert 0 < body_mass <= 300, 'Body mass must be between'\
                ' 0 and 300. Got {}'.format(body_mass)
            self._body_mass = body_mass
        else:
            self._body_mass = 62

        if posture is not None:
            assert isinstance(posture, str), 'posture must be a string.'\
                ' Got {}'.format(type(posture))
            assert posture.lower() in self.POSTURES, 'posture {} is not '\
                'acceptable. Choose from {}'.format(posture, self.POSTURES)
            self._posture = posture
        else:
            self._posture = 'standing'

        self._humid_acclimated = bool(humid_acclimated)

    @classmethod
    def from_dict(cls, data):
        """Create a PETParameter object from a dictionary.

        Args:
            data: A PETParameter dictionary in following the format below.

        .. code-block:: python

            {
            'type': 'PETParameter',
            'age': 36,
            'sex': 1,
            'height': 1.55,
            'body_mass': 45,
            'posture': 'standing',
            'humid_acclimated': True
            }
        """
        assert data['type'] == 'PETParameter', \
            'Expected PETParameter dictionary. Got {}.'.format(data['type'])
        age = data['age'] if 'age' in data else None
        sex = data['sex'] if 'sex' in data else None
        height = data['height'] if 'height' in data else None
        body_mass = data['body_mass'] if 'body_mass' in data else None
        posture = data['posture'] if 'posture' in data else None
        h_acc = data['humid_acclimated'] if 'humid_acclimated' in data else False
        return cls(age, sex, height, body_mass, posture, h_acc)

    @classmethod
    def from_string(cls, pet_parameter_string):
        """Create an PETParameter object from an PETParameter string."""
        str_pattern = re.compile(r"\-\-(\S*\s\S*)")
        matches = str_pattern.findall(pet_parameter_string)
        par_dict = {item.split(' ')[0]: item.split(' ')[1] for item in matches}

        age = float(par_dict['age']) if 'age' in par_dict else None
        sex = float(par_dict['sex']) if 'sex' in par_dict else None
        height = float(par_dict['height']) if 'height' in par_dict else None
        body_mass = float(par_dict['body-mass']) if 'body-mass' in par_dict else None
        posture = par_dict['posture'] if 'posture' in par_dict else None
        h_acc = False if 'acclimated' not in par_dict \
            or par_dict['acclimated'].lower() == 'temperate' else True
        return cls(age, sex, height, body_mass, posture, h_acc)

    @property
    def age(self):
        """The age of the human subject in years."""
        return self._age

    @property
    def sex(self):
        """A value between 0 and 1 to indicate the sex of the human subject.

        This influences the computation of basal metabolism.
        0 indicates male.
        1 indicates female.
        Any number in between denotes a weighted average between the two.
        """
        return self._sex

    @property
    def height(self):
        """The height of the human subject in meters.

        Average male height is around 1.75m while average female height is 1.55m.
        """
        return self._height

    @property
    def body_mass(self):
        """The body mass of the human subject in kilograms."""
        return self._body_mass

    @property
    def posture(self):
        """A text string indicating the posture of the body."""
        return self._posture

    @property
    def humid_acclimated(self):
        """A boolean for whether subject is acclimated to a humid or temperate climate.

        When True, the categories developed by Lin and Matzarakis (2008) for a
        humid/subtropical climate will be used to assess comfort instead of the
        original categories developed by Matzarakis and Mayer (1996).
        """
        return self._humid_acclimated

    def to_dict(self):
        """PETParameter dictionary representation."""
        return {
            'type': 'PETParameter',
            'age': self.age,
            'sex': self.sex,
            'height': self.height,
            'body_mass': self.body_mass,
            'posture': self.posture,
            'humid_acclimated': self.humid_acclimated
        }

    def __copy__(self):
        return PETParameter(
            self.age, self.sex, self.height, self.body_mass, self.posture,
            self.humid_acclimated)

    def __repr__(self):
        """PET body parameters representation."""
        base = '--age {} --sex {} --height {} --body-mass {} --posture {}'.format(
            self.age, self.sex, self.height, self.body_mass, self.posture)
        if self.humid_acclimated:
            base = '{} --acclimated humid'.format(base)
        return base
