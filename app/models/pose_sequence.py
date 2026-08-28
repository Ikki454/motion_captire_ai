"""Level 1 pose data across a whole video: person tracks and their sequence."""

from dataclasses import dataclass, field
from pathlib import Path

from app.math.coordinates import CoordinateSpace
from app.models.keypoints import RawPose
from app.models.pose import PoseFrame


@dataclass
class PersonTrack:
    """One person's pose across a video.

    ``frames`` (Level 1, canonical) and ``raw_frames`` (Level 0, detector
    native) are both sparse and aligned: a missing frame index means no
    detection for that frame -- an explicit gap, never a silently
    interpolated pose.

    ``raw_frames`` retains the immutable detector output, including any 3D
    world landmarks (``RawPose.world_points``). Those are kept verbatim --
    not converted to the canonical coordinate space, and not treated as a
    real 3D reconstruction.
    """

    track_id: str
    frames: dict[int, PoseFrame] = field(default_factory=dict)
    raw_frames: dict[int, RawPose] = field(default_factory=dict)
    depth_source: str = "none"
    label: str = ""
    space: CoordinateSpace = CoordinateSpace.IMAGE_PIXELS

    def pose_at(self, frame_index: int) -> PoseFrame | None:
        """Return the pose at ``frame_index``, or ``None`` when not detected."""

        return self.frames.get(frame_index)

    def has_detection(self, frame_index: int) -> bool:
        """Return whether a pose was detected at ``frame_index``."""

        return frame_index in self.frames

    def detected_indices(self) -> list[int]:
        """Return the sorted frame indices that have a detected pose."""

        return sorted(self.frames)

    @property
    def detection_count(self) -> int:
        """Return how many frames have a detected pose."""

        return len(self.frames)


@dataclass
class PoseSequence:
    """All pose tracks detected for one video."""

    video_path: Path
    frame_count: int
    fps: float
    width: int
    height: int
    tracks: dict[str, PersonTrack] = field(default_factory=dict)
    active_track_id: str | None = None

    def add_track(self, track: PersonTrack, *, make_active: bool = False) -> None:
        """Add ``track`` to the sequence, optionally making it the active one."""

        self.tracks[track.track_id] = track

        if make_active or self.active_track_id is None:
            self.active_track_id = track.track_id

    @property
    def active_track(self) -> PersonTrack | None:
        """Return the track the UI currently works with, if any."""

        if self.active_track_id is None:
            return None

        return self.tracks.get(self.active_track_id)

    def active_pose_at(self, frame_index: int) -> PoseFrame | None:
        """Return the active track's pose at ``frame_index``, if detected."""

        track = self.active_track

        return track.pose_at(frame_index) if track is not None else None
