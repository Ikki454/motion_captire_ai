"""Window sizing helpers.

Panels grow with their content (17 canonical bone rows, six pipeline
sections), so a fixed window size means scrolling on some setups and
wasted space on others. These helpers size a window to its content and
cap it to the screen it is shown on.
"""

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QScrollArea, QWidget

_SCREEN_FRACTION = 0.92
_FALLBACK_SCREEN_HEIGHT = 900


def fitted_height(
    current_height: int,
    viewport_height: int,
    content_height: int,
    screen_height: int,
    fraction: float = _SCREEN_FRACTION,
) -> int:
    """Return the window height that shows all content, capped to the screen.

    Args:
        current_height: The window's height right now.
        viewport_height: Height the scrollable viewport currently offers.
        content_height: Height the scrolled widget wants.
        screen_height: Usable screen height.
        fraction: Share of the screen the window may occupy.

    Returns:
        ``current_height`` grown by the shortfall, never above
        ``screen_height * fraction`` and never below ``current_height``
        when that already fits.
    """

    shortfall = max(0, content_height - viewport_height)
    cap = max(1, int(screen_height * fraction))
    return max(1, min(current_height + shortfall, cap))


def available_screen_height(widget: QWidget) -> int:
    """Return the usable height of the screen ``widget`` sits on."""

    screen = widget.screen() or QGuiApplication.primaryScreen()

    if screen is None:  # headless / no display attached
        return _FALLBACK_SCREEN_HEIGHT

    return screen.availableGeometry().height()


def fit_window_to_scroll_area(window: QWidget, scroll: QScrollArea) -> None:
    """Grow ``window`` so ``scroll`` shows its content without scrolling."""

    inner = scroll.widget()

    if inner is None:
        return

    window.resize(
        window.width(),
        fitted_height(
            window.height(),
            scroll.viewport().height(),
            inner.sizeHint().height(),
            available_screen_height(window),
        ),
    )
