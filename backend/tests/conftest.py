import pytest


@pytest.fixture
def sample_travel_apply():
    return {
        "user_id": "test_user",
        "reason": "客户拜访",
        "destination": "上海",
        "origin": "北京",
        "start_date": "2026-03-10",
        "end_date": "2026-03-12",
    }
