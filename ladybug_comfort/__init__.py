# coding=utf-8
"""Ladybug thermal comfort libraries.

Properties:
    SOLARCALSPLINES: A dictionary with two keys: 'standing' and 'seated'.
        Each value for these keys is a 2D matrix of projection factors
        for human geometry.  Each row refers to an degree of azimuth and each
        colum refers to a degree of altitude.
"""

# load all functions that extend ladybug core objects.
import ladybug_comfort._extend_ladybug

# load the mannequin data and spline data that gets used in solarcal.
from ._loadmannequin import load_solarcal_splines
SOLARCALSPLINES = load_solarcal_splines()
