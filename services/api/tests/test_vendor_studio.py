from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.schemas import QuoteWrite, VendorWrite


def test_vendor_provenance_and_unknown_evidence_are_explicit():
    vendor = VendorWrite(
        name="Garden Hall", category="venue", provenance="demo_seeded", source_label="Demo dataset"
    )
    assert vendor.provenance == "demo_seeded"
    assert vendor.availability_evidence is None
    quote = QuoteWrite(vendor_id=uuid4(), amount_minor=125000, issued_on=date(2030, 1, 1))
    assert quote.provenance == "user_provided"
    assert quote.availability_evidence is None


def test_quote_dates_and_demo_label_validation():
    with pytest.raises(ValidationError):
        QuoteWrite(
            vendor_id=uuid4(),
            amount_minor=1,
            issued_on=date(2030, 2, 1),
            valid_until=date(2030, 1, 1),
        )
