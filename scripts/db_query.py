"""Interactive SQL query tool for the Azure PostgreSQL database."""

import asyncio
import sys

import asyncpg

DB_CONFIG = {
    "host": "voice-assistant-db.postgres.database.azure.com",
    "port": 5432,
    "user": "flex_voice_assistant_admin",
    "password": "R4K3soGTy2025xZ9",
    "database": "voiceassistant",
    "ssl": "require",
}

SAVED_QUERIES = {
    "1": ("Show all tables", "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"),
    "2": ("Last 5 command logs", "SELECT * FROM command_logs ORDER BY created_at DESC LIMIT 5;"),
    "3": ("All users", "SELECT * FROM users;"),
}


async def run_query(conn: asyncpg.Connection, sql: str):
    rows = await conn.fetch(sql)
    if not rows:
        print("(no rows)")
        return
    cols = list(rows[0].keys())
    col_widths = {c: len(c) for c in cols}
    str_rows = []
    for row in rows:
        str_row = {c: str(row[c]) for c in cols}
        for c in cols:
            col_widths[c] = max(col_widths[c], len(str_row[c]))
        str_rows.append(str_row)
    header = " | ".join(c.ljust(col_widths[c]) for c in cols)
    sep = "-+-".join("-" * col_widths[c] for c in cols)
    print(header)
    print(sep)
    for sr in str_rows:
        print(" | ".join(sr[c].ljust(col_widths[c]) for c in cols))
    print(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''})")


async def main():
    conn = await asyncpg.connect(**DB_CONFIG)
    print("Connected to Azure PostgreSQL.\n")
    print("Saved queries:")
    for key, (name, _) in SAVED_QUERIES.items():
        print(f"  [{key}] {name}")
    print("\nType a number for a saved query, enter custom SQL, or 'q' to quit.\n")

    while True:
        try:
            sql = input("sql> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not sql or sql.lower() == "q":
            break
        if sql in SAVED_QUERIES:
            name, sql = SAVED_QUERIES[sql]
            print(f"-- {name}")
            print(f"-- {sql}\n")
        try:
            await run_query(conn, sql)
        except Exception as e:
            print(f"ERROR: {e}")
        print()

    await conn.close()
    print("Bye.")


if __name__ == "__main__":
    asyncio.run(main())
