import sqlite3

def run():
    conn = sqlite3.connect('helios.db')
    cur = conn.cursor()

    def add_col(table, col, col_type, default):
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        if col not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type} DEFAULT {default}")
            print(f"Added {col} to {table}")

    add_col('organizations', 'purchased_tokens', 'INTEGER', '0')
    add_col('organizations', 'purchased_tokens_used', 'INTEGER', '0')
    add_col('organizations', 'autofix_tokens_total', 'INTEGER', '50000')
    add_col('organizations', 'autofix_tokens_used', 'INTEGER', '0')
    add_col('organizations', 'limit_enforcement_enabled', 'INTEGER', '1')
    add_col('organizations', 'window_5h_tokens_used', 'INTEGER', '0')
    add_col('organizations', 'window_5h_reset_at', 'TEXT', "'2026-10-24 00:00:00'")
    add_col('organizations', 'window_weekly_tokens_used', 'INTEGER', '0')
    add_col('organizations', 'window_weekly_reset_at', 'TEXT', "'2026-10-24 00:00:00'")
    add_col('chat_messages', 'tokens_consumed', 'INTEGER', '0')

    conn.commit()
    conn.close()
    print("MIGRATION_COMPLETED_CLEANLY")

if __name__ == '__main__':
    run()
