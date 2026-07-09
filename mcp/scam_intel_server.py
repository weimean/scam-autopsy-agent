import os
import sqlite3

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("scam-intel")

# Database initialization
os.makedirs("data", exist_ok=True)
db_path = "data/scam_intel.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

# Ensure the tactics table exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS tactics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    lever TEXT NOT NULL,
    description TEXT NOT NULL,
    example_masked TEXT NOT NULL,
    UNIQUE(name, category)
)
""")
conn.commit()

# Seed data from specs/02_taxonomy.md
SEED_TACTICS = [
    (
        "guaranteed_returns",
        "crypto_investment",
        "unrealistic_returns",
        "promises risk-free outsized profit",
        "lock in 300% in a week, zero risk",
    ),
    (
        "withdrawal_fee_trap",
        "crypto_investment",
        "commitment",
        "lets you 'win' then demands a fee to withdraw",
        "pay [[AMOUNT]] release fee to unlock your balance",
    ),
    (
        "deadline_pressure",
        "phishing",
        "urgency",
        "short fuse to stop you verifying",
        "account suspended in 24h — verify now",
    ),
    (
        "account_verify_link",
        "phishing",
        "authority",
        "poses as the bank + a lookalike link",
        "confirm your details at [[URL]]",
    ),
    (
        "you_have_won",
        "prize_lottery",
        "scarcity",
        "unclaimed prize you never entered for",
        "claim your [[AMOUNT]] before it expires",
    ),
    (
        "release_fee",
        "prize_lottery",
        "reciprocity",
        "small fee to release big winnings",
        "pay [[AMOUNT]] processing to receive [[AMOUNT]]",
    ),
    (
        "love_bomb",
        "romance",
        "liking",
        "rapid intense affection to lower guard",
        "I've never felt this way, you're my soulmate",
    ),
    (
        "crisis_ask",
        "romance",
        "urgency",
        "sudden emergency needing money",
        "customs is holding my package, send [[AMOUNT]]",
    ),
    (
        "dont_tell_anyone",
        "romance",
        "isolation",
        "discourages outside advice",
        "our bank wouldn't understand, keep this between us",
    ),
    (
        "infected_device",
        "tech_support",
        "fear",
        "fake infection to force remote access",
        "your device is compromised, install [[APP]]",
    ),
    (
        "inheritance_beneficiary",
        "advance_fee",
        "authority",
        "official-sounding windfall story",
        "you are the beneficiary of [[AMOUNT]], send fees",
    ),
    (
        "urgent_wire_change",
        "impersonation_bec",
        "authority",
        "posing as boss/vendor to redirect payment",
        "new bank details, wire today, keep confidential",
    ),
]
cursor.executemany(
    "INSERT OR IGNORE INTO tactics (name, category, lever, description, example_masked) VALUES (?, ?, ?, ?, ?)",
    SEED_TACTICS,
)
conn.commit()


@mcp.tool()
def query_tactics(category: str) -> list[dict]:
    """Query tactics from the database by category."""
    cursor.execute(
        "SELECT id, name, category, lever, description, example_masked FROM tactics WHERE category = ?",
        (category,),
    )
    rows = cursor.fetchall()
    keys = ["id", "name", "category", "lever", "description", "example_masked"]
    return [dict(zip(keys, r, strict=False)) for r in rows]


@mcp.tool()
def add_tactic(
    name: str, category: str, lever: str, description: str, example_masked: str
) -> dict:
    """Add a new tactic to the database with dedup on (name, category)."""
    try:
        cursor.execute(
            "INSERT INTO tactics (name, category, lever, description, example_masked) VALUES (?, ?, ?, ?, ?)",
            (name, category, lever, description, example_masked),
        )
        conn.commit()
        return {"added": True, "reason": "Tactic added successfully."}
    except sqlite3.IntegrityError:
        return {
            "added": False,
            "reason": f"Tactic with name '{name}' and category '{category}' already exists.",
        }


@mcp.tool()
def get_stats() -> dict:
    """Get total count of tactics and breakdown by category."""
    cursor.execute("SELECT COUNT(*) FROM tactics")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT category, COUNT(*) FROM tactics GROUP BY category")
    by_category = dict(cursor.fetchall())
    return {"total": total, "by_category": by_category}


if __name__ == "__main__":
    mcp.run(transport="stdio")
