from app.contracts.parsers import parse_currency


def test_currency_formats():
    assert parse_currency("$29").value == 29.0
    assert parse_currency("$29.00/mo").value == 29.0
    assert parse_currency("29 USD").value == 29.0
    assert parse_currency("€29").value == 29.0
    assert parse_currency("Free").value == 0.0
    assert parse_currency("").status == "absent"
    assert parse_currency(None).status == "absent"
    assert parse_currency("Contact sales").status == "malformed"
