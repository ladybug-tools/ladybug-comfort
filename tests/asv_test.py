# coding utf-8
import pytest

from ladybug_comfort.asv import actual_sensation_vote
from ladybug_comfort.asv import actual_sensation_vote_effect_category


def test_actual_sensation_vote():
    """Test the actual_sensation_vote function."""
    assert actual_sensation_vote(40, 10, 15, 10) == pytest.approx(-0.4090,
                                                                  rel=1e-3)
    assert actual_sensation_vote(20, 50, 34, 48) == pytest.approx(-3.1250,
                                                                  rel=1e-3)


def test_actual_sensation_vote_effect_category():
    """Test the actual_sensation_vote_effect_category function"""
    assert actual_sensation_vote_effect_category(2.5) == 2
    assert actual_sensation_vote_effect_category(1.4) == 1
    assert actual_sensation_vote_effect_category(0.5) == 0
    assert actual_sensation_vote_effect_category(-1.4) == -1
    assert actual_sensation_vote_effect_category(-2.5) == -2
