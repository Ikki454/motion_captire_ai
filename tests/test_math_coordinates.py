"""Tests for coordinate-space conversions (roadmap Phase 10)."""

from app.math.coordinates import (
    CoordinateSpace,
    image_to_canonical,
    mediapipe_world_to_canonical,
)


def test_image_to_canonical_flips_y_and_zeroes_z() -> None:
    result = image_to_canonical(120.0, 45.0)

    assert result.x == 120.0
    assert result.y == -45.0
    assert result.z == 0.0


def test_mediapipe_world_to_canonical_flips_y_and_z() -> None:
    result = mediapipe_world_to_canonical(0.3, -0.4, 0.5)

    assert result.x == 0.3
    assert result.y == 0.4
    assert result.z == -0.5


def test_coordinate_space_values_are_stable() -> None:
    assert CoordinateSpace.CANONICAL_WORLD.value == "canonical_world"
    assert CoordinateSpace.IMAGE_PIXELS.value == "image_pixels"
