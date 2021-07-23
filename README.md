
![Ladybug](http://www.ladybug.tools/assets/img/ladybug.png)


[![Build Status](https://travis-ci.com/ladybug-tools/ladybug.svg?branch=master)](https://travis-ci.com/ladybug-tools/ladybug-comfort)
[![Coverage Status](https://coveralls.io/repos/github/ladybug-tools/ladybug-comfort/badge.svg)](https://coveralls.io/github/ladybug-tools/ladybug-comfort)

[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/) [![Python 2.7](https://img.shields.io/badge/python-2.7-green.svg)](https://www.python.org/downloads/release/python-270/) [![IronPython](https://img.shields.io/badge/ironpython-2.7-red.svg)](https://github.com/IronLanguages/ironpython2/releases/tag/ipy-2.7.8/)

# ladybug-comfort

Ladybug-comfort is a Python library that adds thermal comfort functionalities to
[ladybug-core](https://github.com/ladybug-tools/ladybug/).

## [API Documentation](https://www.ladybug.tools/ladybug-comfort/docs/)

## Installation

`pip install ladybug-comfort`

## Usage

```
"""Get the percentage of time outdoor conditions are comfortable with/without sun + wind"""
from ladybug.epw import EPW
from ladybug_comfort.collection.utci import UTCI

epw_file_path = './tests/epw/chicago.epw'
epw = EPW(epw_file_path)
utci_obj_exposed = UTCI.from_epw(epw, include_wind=True, include_sun=True)
utci_obj_protected = UTCI.from_epw(epw, include_wind=False, include_sun=False)

print(utci_obj_exposed.percent_neutral)  # comfortable percent of time with sun + wind
print(utci_obj_protected.percent_neutral)  # comfortable percent of time without sun + wind
```

### derivative work

Ladybug-comfort is a derivative work of the following software projects:

* [CBE Comfort Tool](https://github.com/CenterForTheBuiltEnvironment/comfort_tool) for indoor thermal comfort calculations.  Available under GPL.
* [UTCI Fortran Code](http://www.utci.org/utci_doku.php) for outdoor thermal comfort calculations.  Available under MIT.

Applicable copyright notices for these works can be found within the relevant .py files.
