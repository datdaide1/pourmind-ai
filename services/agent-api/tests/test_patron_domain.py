from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.schemas import DrinkExperienceCreate, PatronCreate


NOW = datetime.now(UTC)


def test_patron_requires_privacy_notice_acknowledgement():
    patron = PatronCreate(
        display_name="Sam",
        notice_version="pilot-v1",
        notice_acknowledged_at=NOW,
    )
    assert patron.display_name == "Sam"

    with pytest.raises(ValidationError):
        PatronCreate(display_name="Sam")


@pytest.mark.parametrize("rating", [0, 6, 2.5])
def test_experience_rejects_out_of_range_or_non_integer_rating(rating):
    with pytest.raises(ValidationError):
        DrinkExperienceCreate(
            rating=rating,
            feedback_provenance="guest_stated",
            served_at=NOW,
            idempotency_key="request-1",
        )


def test_rating_or_feedback_requires_explicit_provenance():
    with pytest.raises(ValidationError, match="feedback_provenance"):
        DrinkExperienceCreate(
            rating=5,
            served_at=NOW,
            idempotency_key="request-1",
        )


def test_provenance_is_rejected_without_feedback_signal():
    with pytest.raises(ValidationError, match="requires a rating or feedback"):
        DrinkExperienceCreate(
            feedback_provenance="bartender_observed",
            served_at=NOW,
            idempotency_key="request-1",
        )
