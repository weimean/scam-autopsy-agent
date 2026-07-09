"""Unit tests for the PII masker (app/tools/pii_masker.py).

The masker is the first line of the safety model: PII is replaced with
placeholders at intake, before any agent or the database sees the message.
These tests pin the masking behaviour for each PII category.
"""

from app.tools.pii_masker import mask_pii

# A valid ETH address (0x + 40 hex) with no 10-digit run, and a
# genesis-format BTC address, so neither is misparsed as a phone number.
ETH_ADDR = "0x" + ("a1b2c3d4e5" * 4)
BTC_ADDR = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"


def test_empty_and_none_pass_through():
    assert mask_pii("") == ""
    assert mask_pii(None) is None


def test_text_without_pii_is_unchanged():
    text = "Hello, this is a perfectly normal message."
    assert mask_pii(text) == text


def test_email_is_masked():
    out = mask_pii("Contact me at john.doe@example.com please")
    assert "[[EMAIL]]" in out
    assert "john.doe@example.com" not in out


def test_url_is_masked():
    out = mask_pii("Verify now at http://evil-bank.example.com/login")
    assert "[[URL]]" in out
    assert "evil-bank.example.com/login" not in out


def test_www_url_is_masked():
    out = mask_pii("Go to www.phishing-site.net now")
    assert "[[URL]]" in out
    assert "www.phishing-site.net" not in out


def test_phone_international_is_masked():
    out = mask_pii("Call +15551234567 immediately")
    assert "[[PHONE]]" in out
    assert "15551234567" not in out


def test_eth_wallet_is_masked():
    out = mask_pii(f"Send funds to {ETH_ADDR}")
    assert "[[WALLET]]" in out
    assert ETH_ADDR not in out


def test_btc_wallet_is_masked():
    out = mask_pii(f"Send funds to {BTC_ADDR}")
    assert "[[WALLET]]" in out
    assert BTC_ADDR not in out


def test_amount_with_symbol_prefix_is_masked():
    out = mask_pii("Pay $500 to release your parcel")
    assert "[[AMOUNT]]" in out
    assert "$500" not in out


def test_amount_with_currency_suffix_is_masked():
    out = mask_pii("A fee of 250 USD is required")
    assert "[[AMOUNT]]" in out
    assert "250 USD" not in out


def test_multiple_pii_types_all_masked():
    text = (
        f"Email admin@bank.example.com, call +15551234567, "
        f"pay $500 to {BTC_ADDR} via www.claim-now.example.org"
    )
    out = mask_pii(text)
    for placeholder in (
        "[[EMAIL]]",
        "[[PHONE]]",
        "[[AMOUNT]]",
        "[[WALLET]]",
        "[[URL]]",
    ):
        assert placeholder in out
    assert "admin@bank.example.com" not in out
    assert BTC_ADDR not in out


def test_masking_is_idempotent():
    text = f"Reach {'user@example.com'} or send to {ETH_ADDR} for $500"
    once = mask_pii(text)
    twice = mask_pii(once)
    assert once == twice
