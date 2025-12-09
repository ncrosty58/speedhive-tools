import pytest

from speedhive_tools.utils.track_records import parse_track_record_text


@pytest.mark.parametrize(
    "text,expected",
    [
        ("New Track Record (1:17.870) for IT7 by Bob Cross.",
         {"classification": "IT7", "lap_time": "1:17.870", "driver": "Bob Cross"}),
        ("New Class Record (1:17.129) for IT7 by [2] Kevin Fandozzi in Chevrolet C5 Corvette",
         {"classification": "IT7", "lap_time": "1:17.129", "driver": "Kevin Fandozzi", "marque": "Chevrolet C5 Corvette"}),
        ("This is not relevant text", None),
        ("New Track Record (63.004) for T4 by Jane Doe", {"classification": "T4", "lap_time": "63.004", "driver": "Jane Doe"}),
        ("New Track Record (1:03.004) for P2 by Alejandro Dellatorre in 1984 SRF Enterprises.",
         {"classification": "P2", "lap_time": "1:03.004", "driver": "Alejandro Dellatorre", "marque": "1984 SRF Enterprises"}),
    ],
)
def test_parse_track_record_text(text, expected):
    parsed = parse_track_record_text(text)
    if expected is None:
        assert parsed is None
        return
    assert parsed is not None
    for k, v in expected.items():
        assert parsed.get(k) == v
    # lap_time_seconds should parse to a float
    assert isinstance(parsed.get("lap_time_seconds"), (float, type(None)))
