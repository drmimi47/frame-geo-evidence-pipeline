from datetime import datetime, timezone

from image_evidence.inference import infer
from image_evidence.schema import ClaimedLocation, DiscoveryContext, SourceVideo


def _source(**kw) -> SourceVideo:
    return SourceVideo(
        youtube_id="abcdefghijk",
        source_url="https://www.youtube.com/watch?v=abcdefghijk",
        title="t",
        published_at=datetime(2023, 6, 1, tzinfo=timezone.utc),
        retrieved_via=("test",),
        **kw,
    )


def test_query_location_never_produces_coordinates():
    ctx = DiscoveryContext(run_id="r", query="Kyiv drone", location="Kyiv", rank=0)
    inf = infer(_source(), [ctx])
    assert len(inf.locations) == 1
    loc = inf.locations[0]
    assert loc.place_name == "Kyiv"
    assert loc.latitude is None and loc.longitude is None
    assert loc.confidence < 0.5
    assert loc.provenance.method == "discovery_query_context"


def test_uploader_geotag_is_top_candidate_with_provenance():
    src = _source(claimed_recording_location=ClaimedLocation(latitude=50.0, longitude=30.0))
    inf = infer(src, [DiscoveryContext(run_id="r", query="q", location="Kyiv", rank=0)])
    assert inf.locations[0].latitude == 50.0
    assert inf.locations[0].provenance.method == "youtube_recording_details_geotag"
    assert inf.locations[0].confidence < 1.0


def test_publication_date_is_only_an_upper_bound():
    inf = infer(_source(), [])
    (bound,) = inf.capture_date
    assert bound.value is None
    assert bound.latest.isoformat() == "2023-06-01"
    assert bound.earliest is None
