"""
TODO(bootcamper): write the tests for ``src/waypoint_utils.py`` in here.

The example below covers files that parse fine: with and without ``home``,
and files with comments and blank lines in them. The rest is yours:

- Bad data: a file whose top level isn't a mapping, waypoints missing
  ``lat``, ``lon``, or ``alt``, values that aren't numbers, YAML that
  doesn't parse, and a file that isn't there.
- Out of range: latitudes past +/-90 and longitudes past +/-180 get
  rejected.
- Nothing to work with: an empty file, an empty ``waypoints`` list, and
  ``sort_clockwise_sweep`` given a list of 0 or 1 waypoints.
- ``east_north_coordinate_offset_m``: offsets you worked out yourself,
  compared with ``pytest.approx``. Never use ``==`` on meters.
- Ordering: with no ``home``, ``sort_clockwise_sweep`` goes clockwise
  starting from north.
- With a ``home``: the order starts in home's direction instead, and goes
  back to starting at north if home is right on top of the centroid.
- Two waypoints in the same direction: the closer one comes first.
- Parsing gives you frozen ``Coordinate`` objects that can't be changed.

Graded by ``warg run utils grade-tests``: pass on the real code, 90% branch
coverage, and fail on every broken copy in ``grader/mutants/``.
"""

import pytest

from src.types import Coordinate
from src.waypoint_utils import (
    east_north_coordinate_offset_m,
    parse_waypoints_file,
    sort_clockwise_sweep,
)

# The helper and the test below are given to you.


def write_to_tmp_waypoints_file(tmp_path, text):
    """Write ``text`` to a YAML file and hand back its path.

    ``tmp_path`` is a pytest fixture: a fresh empty directory per test.
    """
    path = tmp_path / "waypoints.yaml"
    path.write_text(text)
    return path


# One test, three files. ``parametrize`` runs the test body once per
# ``(text, expected)`` pair, and ``ids`` names each run so a failure tells you
# which file broke.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            """
            home: {lat: 1, lon: 2, alt: 3}
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            """
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
              - {lat: 7, lon: 8, alt: 9}
            """,
            (None, [Coordinate(4, 5, 6), Coordinate(7, 8, 9)]),
        ),
        (
            """
            # a lap

            home: {lat: 1, lon: 2, alt: 3}

            waypoints:
              # first leg
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
    ],
    ids=["home-and-waypoints", "no-home", "comments-and-blank-lines"],
)
def test_parse_waypoints_file_success(tmp_path, text, expected):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == expected



# Invalid YAML and malformed waypoint data.


@pytest.mark.parametrize("text", ["- one\n- two\n", "42\n", "hello\n"])
def test_rejects_non_mapping_top_level(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError):
        parse_waypoints_file(path)


@pytest.mark.parametrize("missing", ["lat", "lon", "alt"])
def test_rejects_missing_waypoint_key(tmp_path, missing):
    values = {"lat": 1, "lon": 2, "alt": 3}
    del values[missing]
    text = "waypoints:\n  - " + "\n    ".join(
        f"{key}: {value}" for key, value in values.items()
    ) + "\n"
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError):
        parse_waypoints_file(path)


@pytest.mark.parametrize("entry", ["not a mapping", "null", "[]"])
def test_rejects_waypoint_that_is_not_mapping(tmp_path, entry):
    path = write_to_tmp_waypoints_file(
        tmp_path, f"waypoints:\n  - {entry}\n"
    )
    with pytest.raises(ValueError):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    "entry",
    [
        "{lat: nope, lon: 2, alt: 3}",
        "{lat: 1, lon: nope, alt: 3}",
        "{lat: 1, lon: 2, alt: nope}",
        "{lat: null, lon: 2, alt: 3}",
    ],
)
def test_rejects_non_numeric_coordinate_values(tmp_path, entry):
    path = write_to_tmp_waypoints_file(
        tmp_path, f"waypoints:\n  - {entry}\n"
    )
    with pytest.raises(ValueError):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    ("lat", "lon"),
    [(91, 0), (-91, 0), (0, 181), (0, -181)],
)
def test_rejects_coordinates_out_of_range(tmp_path, lat, lon):
    path = write_to_tmp_waypoints_file(
        tmp_path,
        f"waypoints:\n  - {{lat: {lat}, lon: {lon}, alt: 0}}\n",
    )
    with pytest.raises(ValueError):
        parse_waypoints_file(path)


def test_accepts_coordinates_at_range_boundaries(tmp_path):
    path = write_to_tmp_waypoints_file(
        tmp_path,
        "waypoints:\n"
        "  - {lat: 90, lon: 180, alt: 0}\n"
        "  - {lat: -90, lon: -180, alt: 0}\n",
    )
    _, waypoints = parse_waypoints_file(path)
    assert waypoints == [
        Coordinate(90, 180, 0),
        Coordinate(-90, -180, 0),
    ]


def test_rejects_invalid_yaml(tmp_path):
    path = write_to_tmp_waypoints_file(
        tmp_path, "waypoints: [this is not valid YAML"
    )
    with pytest.raises(ValueError):
        parse_waypoints_file(path)


def test_missing_file_raises_os_error(tmp_path):
    with pytest.raises(OSError):
        parse_waypoints_file(tmp_path / "missing.yaml")


def test_empty_file_returns_no_home_and_no_waypoints(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "")
    assert parse_waypoints_file(path) == (None, [])


def test_empty_waypoints_list_returns_empty_list(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: []\n")
    assert parse_waypoints_file(path) == (None, [])


def test_rejects_non_list_waypoints(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: not-a-list\n")
    with pytest.raises(ValueError):
        parse_waypoints_file(path)


def test_rejects_missing_alt_in_home(tmp_path):
    path = write_to_tmp_waypoints_file(
        tmp_path, "home: {lat: 1, lon: 2}\nwaypoints: []\n"
    )
    with pytest.raises(ValueError):
        parse_waypoints_file(path)


def test_parsed_coordinate_is_frozen(tmp_path):
    path = write_to_tmp_waypoints_file(
        tmp_path, "waypoints:\n  - {lat: 1, lon: 2, alt: 3}\n"
    )
    _, waypoints = parse_waypoints_file(path)
    with pytest.raises(AttributeError):
        waypoints[0].lat = 99


# East/north offsets. One degree of latitude is approximately
# R*pi/180 metres; longitude is scaled by cos(latitude).


def test_one_degree_offsets_at_equator():
    from math import cos, pi

    from src.constants import EARTH_RADIUS_M

    expected_north = EARTH_RADIUS_M * pi / 180
    expected_east = expected_north * cos(0.5 * pi / 180)
    east, north = east_north_coordinate_offset_m(0, 0, 1, 1)
    assert east == pytest.approx(expected_east, abs=0.01)
    assert north == pytest.approx(expected_north, abs=0.01)


def test_east_offset_is_scaled_at_60_degrees_latitude():
    from math import cos, pi

    from src.constants import EARTH_RADIUS_M

    east, _ = east_north_coordinate_offset_m(60, 0, 60, 1)
    expected = EARTH_RADIUS_M * pi / 180 * cos(60 * pi / 180)
    assert east == pytest.approx(expected, abs=0.01)


def test_north_offset_does_not_depend_on_longitude():
    from math import pi

    from src.constants import EARTH_RADIUS_M

    _, north = east_north_coordinate_offset_m(10, 20, 11, 20)
    assert north == pytest.approx(EARTH_RADIUS_M * pi / 180, abs=0.01)


# Sorting should start at north by default and proceed clockwise.


def test_sort_empty_list():
    assert sort_clockwise_sweep([]) == []


def test_sort_single_waypoint():
    waypoint = Coordinate(1, 2, 3)
    assert sort_clockwise_sweep([waypoint]) == [waypoint]


def test_sort_starts_north_and_goes_clockwise():
    north = Coordinate(1, 0, 0)
    east = Coordinate(0, 1, 0)
    south = Coordinate(-1, 0, 0)
    west = Coordinate(0, -1, 0)

    assert sort_clockwise_sweep([south, west, east, north]) == [
        north, east, south, west
    ]


def test_sort_wraps_from_west_back_to_north():
    north = Coordinate(1, 0, 0)
    west = Coordinate(0, -1, 0)
    east = Coordinate(0, 1, 0)

    assert sort_clockwise_sweep([west, east, north]) == [
        north, east, west
    ]


def test_home_sets_starting_direction():
    north = Coordinate(1, 0, 0)
    east = Coordinate(0, 1, 0)
    south = Coordinate(-1, 0, 0)
    west = Coordinate(0, -1, 0)
    home = Coordinate(0, 2, 0)

    assert sort_clockwise_sweep(
        [north, west, south, east], home
    ) == [east, south, west, north]


def test_home_at_centroid_falls_back_to_north():
    north = Coordinate(1, 0, 0)
    east = Coordinate(0, 1, 0)
    south = Coordinate(-1, 0, 0)
    west = Coordinate(0, -1, 0)
    home = Coordinate(0, 0, 0)

    assert sort_clockwise_sweep(
        [south, east, west, north], home
    ) == [north, east, south, west]


def test_same_bearing_closer_waypoint_comes_first():
    near_north = Coordinate(1, 0, 0)
    far_north = Coordinate(2, 0, 0)
    south = Coordinate(-3, 0, 0)

    assert sort_clockwise_sweep(
        [far_north, south, near_north]
    ) == [near_north, far_north, south]
