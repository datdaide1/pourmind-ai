from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.schemas import Recommendation, RecommendationResponse, TasteProfile


def snapshot():
    return {
        "version_number": 1,
        "name": "House Highball",
        "source": "house",
        "ingredients": [{"display_name": "Whisky", "amount": 45, "unit": "ml"}],
        "flavor_profile": {
            "taxonomy_version": "flavor-v1",
            "dimensions": {
                "sweet": 0.1,
                "sour": 0.2,
                "bitter": 0.2,
                "spirituous": 0.8,
                "fruity": 0.1,
                "herbal": 0.1,
                "spicy": 0.0,
                "smoky": 0.0,
            },
            "provenance": ["curated"],
        },
    }


def component(name, score, weight):
    return {
        "score": score,
        "weight": weight,
        "evidence_count": 2,
        "explanation_key": name,
    }


def recommendation(**overrides):
    values = {
        "name": "House Highball",
        "source": "house",
        "candidate_recipe_snapshot": snapshot(),
        "match_score": 82,
        "confidence_score": 40,
        "confidence_label": "low",
        "components": {
            "flavor": component("flavor_similarity", 80, 0.30),
            "base_spirit": component("base_spirit_affinity", 85, 0.25),
            "strength": component("strength_fit", 75, 0.15),
            "ingredients": component("ingredient_affinity", 80, 0.15),
            "feedback": component("feedback_pattern", 70, 0.10),
            "novelty": component("novelty_fit", 65, 0.05),
        },
        "evidence_count": 2,
        "caveats": ["Early suggestion"],
    }
    values.update(overrides)
    return values


def test_taste_profile_has_version_confidence_and_evidence():
    profile = TasteProfile(
        patron_id=uuid4(),
        eligible_experience_count=2,
        confidence_score=40,
        confidence_label="low",
        computed_at=datetime.now(UTC),
    )
    assert profile.profile_version == "taste-v1"
    assert profile.eligible_experience_count == 2


def test_recommendation_has_versioned_breakdown_evidence_and_caveats():
    item = Recommendation(**recommendation())
    assert item.scoring_version == "match-v1"
    assert item.components.flavor.evidence_count == 2
    assert item.caveats == ["Early suggestion"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"match_score": -1},
        {"match_score": 101},
        {"components": {"flavor": component("flavor", 80, 1.0)}},
        {"source": "made_up"},
    ],
)
def test_recommendation_rejects_invalid_score_components_or_source(overrides):
    with pytest.raises(ValidationError):
        Recommendation(**recommendation(**overrides))


def test_response_rejects_mismatched_scoring_versions():
    with pytest.raises(ValidationError, match="scoring_version"):
        RecommendationResponse(
            patron_id=uuid4(),
            profile_version="taste-v1",
            scoring_version="match-v2",
            recommendations=[recommendation()],
        )


def test_breakdown_rejects_weights_that_do_not_sum_to_one():
    invalid_components = recommendation()["components"]
    invalid_components["novelty"] = component("novelty_fit", 65, 0.10)
    with pytest.raises(ValidationError, match="weights must sum to 1"):
        Recommendation(**recommendation(components=invalid_components))
