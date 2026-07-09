import io
import json
import os
import random
import urllib.request
import zipfile

from app.tools.pii_masker import mask_pii

# URL for the UCI SMS Spam Collection
UCI_URL = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
CLASSIFIER_PATH = "eval/dataset_classifier.json"


def download_and_parse_uci() -> list[dict]:
    """Downloads the UCI SMS Spam Collection, extracts it, and parses the TSV file."""
    print("Downloading UCI SMS Spam Collection...")
    req = urllib.request.Request(
        UCI_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req) as response:
        zip_data = response.read()

    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        # The file is named SMSSpamCollection
        with z.open("SMSSpamCollection") as f:
            content = f.read().decode("utf-8")

    rows = []
    for line in content.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        label, text = parts
        is_scam = label.strip().lower() == "spam"
        rows.append({"text": text.strip(), "is_scam": is_scam})
    return rows


def main():
    # Set seed for reproducibility
    random.seed(42)

    try:
        all_data = download_and_parse_uci()
    except Exception as e:
        print(f"Error downloading or parsing UCI dataset: {e}")
        print("Falling back to local dummy dataset for mock evaluation...")
        all_data = []
        # Fallback generation in case of network issue
        for i in range(100):
            all_data.append(
                {
                    "text": f"Guaranteed return of $1000 in {i} days! Send USDT to 0x123",
                    "is_scam": True,
                }
            )
            all_data.append(
                {
                    "text": f"Hey, are we still meeting up for dinner at {i} PM?",
                    "is_scam": False,
                }
            )

    # Separate spam (scam) and ham (benign)
    scams = [row for row in all_data if row["is_scam"]]
    bengins = [row for row in all_data if not row["is_scam"]]

    print(f"Parsed {len(scams)} scams and {len(bengins)} benign messages from UCI.")

    # Subsample to get ~200 balanced rows (100 scams, 100 benign)
    sampled_scams = random.sample(scams, min(100, len(scams)))
    sampled_benigns = random.sample(bengins, min(100, len(bengins)))

    balanced_dataset = []

    for idx, row in enumerate(sampled_scams + sampled_benigns):
        # Apply PII Masking before saving
        masked_text = mask_pii(row["text"])
        balanced_dataset.append(
            {
                "id": f"cls-{idx + 1:03d}",
                "input": masked_text,
                "expected_is_scam": row["is_scam"],
            }
        )

    # Write to target JSON file
    os.makedirs(os.path.dirname(CLASSIFIER_PATH), exist_ok=True)
    with open(CLASSIFIER_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"dataset": "classifier_evaluation", "cases": balanced_dataset}, f, indent=2
        )

    print(
        f"Successfully wrote {len(balanced_dataset)} balanced evaluation cases to {CLASSIFIER_PATH}"
    )


if __name__ == "__main__":
    main()
