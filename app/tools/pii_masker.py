import re

# Regex patterns for PII masking
EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_REGEX = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b\+?\d{10,13}\b"
)
URL_REGEX = re.compile(
    r"\bhttps?://[^\s/$.?#].[^\s]*|\bwww\.[^\s]+|\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}/[^\s]*"
)
ETH_REGEX = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
BTC_REGEX = re.compile(
    r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|\bbc1[ac-hj-np-z02-9]{11,71}\b"
)
AMOUNT_REGEX = re.compile(
    r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:USD|USDT|USDC|EUR|GBP|BTC|ETH|\$|€|£)\b|"
    r"(?:\$|€|£|USDT|USDC)\s*\d+(?:,\d{3})*(?:\.\d+)?\b"
)


def mask_pii(text: str) -> str:
    """Masks sensitive PII patterns (emails, phones, URLs, crypto wallets, amounts) with placeholders."""
    if not text:
        return text

    text = EMAIL_REGEX.sub("[[EMAIL]]", text)
    text = PHONE_REGEX.sub("[[PHONE]]", text)
    text = URL_REGEX.sub("[[URL]]", text)
    text = ETH_REGEX.sub("[[WALLET]]", text)
    text = BTC_REGEX.sub("[[WALLET]]", text)
    text = AMOUNT_REGEX.sub("[[AMOUNT]]", text)

    return text
