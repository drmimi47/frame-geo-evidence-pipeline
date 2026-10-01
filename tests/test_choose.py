from image_evidence.classify import choose, subject_score
from image_evidence.config import ClassificationConfig

CFG = ClassificationConfig()
FIELD = {"landscape": 0.9, "people": 0.05}
FACE = {"people": 0.9, "landscape": 0.05}
CAR = {"interior": 0.7, "street": 0.2}


def test_subject_score_prefers_places_over_people_and_interiors():
    assert subject_score(FIELD, CFG) > CFG.min_subject
    assert subject_score(FACE, CFG) < 0
    assert subject_score(CAR, CFG) < 0
    assert subject_score({"landscape": 0.6, "people": 0.3}, CFG) < CFG.min_subject  # people dominate half the shot


def test_choose_drops_unwanted_frames():
    scores = [FIELD, FACE, CAR, FIELD, FACE]
    assert choose([0, 10, 20, 30, 40], scores, CFG, limit=10) == [0, 3]


def test_choose_spreads_across_the_timeline():
    # a long run of great frames at the start shouldn't crowd out the rest
    times = [float(t) for t in range(10)] + [100.0, 200.0]
    scores = [{"landscape": 0.99}] * 10 + [{"landscape": 0.6}] * 2
    picked = choose(times, scores, CFG, limit=3)
    assert len(picked) == 3 and {10, 11} <= set(picked)
