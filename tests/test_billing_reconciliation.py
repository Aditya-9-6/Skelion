from datetime import date

import pytest

from skelion_agent.billing_reconciliation import calculate_proration


def test_proration_is_signed_and_rounds_to_paise():
    assert calculate_proration(
        10000, 20000, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 16)
    ) == 5000
    assert calculate_proration(
        20000, 10000, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 16)
    ) == -5000


def test_proration_rejects_empty_period():
    with pytest.raises(ValueError):
        calculate_proration(
            1, 2, date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 1)
        )
