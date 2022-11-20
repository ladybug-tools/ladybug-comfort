# coding utf-8
import pytest

from ladybug_comfort.pet import physiologic_equivalent_temperature


def test_pet():
    """Test the physiologic_equivalent_temperature function"""
    # sample input data for the PET model
    rh = 50  # relative humidity [%]
    vel = 1  # air velocity [m/s]
    met = 2.3  # metabolic rate [met]
    clo = 1  # clothing level [clo]

    result = physiologic_equivalent_temperature(-20, 10, vel, rh, met, clo)
    assert result['pet'] == pytest.approx(-16.9, rel=1e-2)
    assert result['t_core'] == pytest.approx(22.8, rel=1e-2)
    assert result['t_skin'] == pytest.approx(4.04, rel=1e-2)
    assert result['t_clo'] == pytest.approx(-7.78, rel=1e-2)

    result = physiologic_equivalent_temperature(20, 30, vel, rh, met, clo)
    assert result['pet'] == pytest.approx(22.3, rel=1e-2)
    assert result['t_core'] == pytest.approx(36.88, rel=1e-2)
    assert result['t_skin'] == pytest.approx(28.8, rel=1e-2)
    assert result['t_clo'] == pytest.approx(24.6, rel=1e-2)

    result = physiologic_equivalent_temperature(30, 60, vel, rh, met, clo)
    assert result['pet'] == pytest.approx(42.5, rel=1e-2)
    assert result['t_core'] == pytest.approx(39.28, rel=1e-2)
    assert result['t_skin'] == pytest.approx(38.18, rel=1e-2)
    assert result['t_clo'] == pytest.approx(40.29, rel=1e-2)
