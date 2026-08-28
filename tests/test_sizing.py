"""Tests for the window sizing helper."""

from app.ui.sizing import fitted_height


def test_grows_by_the_shortfall_when_the_screen_allows() -> None:
    # content needs 156px more than the viewport offers
    assert fitted_height(640, 434, 590, 1392) == 796


def test_leaves_a_window_that_already_fits_alone() -> None:
    assert fitted_height(800, 700, 500, 1392) == 800


def test_never_exceeds_the_screen() -> None:
    height = fitted_height(640, 200, 5000, 1000)

    assert height == int(1000 * 0.92)


def test_a_small_screen_caps_below_the_current_height() -> None:
    # a window taller than the screen is brought back inside it
    assert fitted_height(1200, 1100, 1200, 800) == 736


def test_height_is_always_positive() -> None:
    assert fitted_height(0, 0, 0, 0) >= 1
