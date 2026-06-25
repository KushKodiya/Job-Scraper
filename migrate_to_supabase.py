"""One-time migration script: SQLite jobs.db -> Supabase"""
import sqlite3
import pickle
import io
import os
from dotenv import load_dotenv
from supabase import create_client


class _SafeUnpickler(pickle.Unpickler):
    """Unpickler that refuses to resolve any global/class. The legacy `tags`
    column only ever stored plain lists of strings, which unpickle from native
    opcodes without any GLOBAL reference — so blocking find_class entirely keeps
    valid data loadable while neutralizing the arbitrary-code-execution risk of
    pickle.loads on a swapped/tampered jobs.db file.
    """

    def find_class(self, module, name):
        raise pickle.UnpicklingError(
            f"Refusing to unpickle disallowed global {module}.{name}"
        )


def safe_pickle_loads(blob):
    """Deserialize a legacy tags blob, returning [] if it isn't a plain list."""
    result = _SafeUnpickler(io.BytesIO(blob)).load()
    return result if isinstance(result, list) else []

# Load env from src/.env
load_dotenv(dotenv_path="src/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_KEY in src/.env first")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
conn = sqlite3.connect("jobs.db")
cursor = conn.cursor()

# Migrate jobs
cursor.execute("SELECT id, company, title, location, url, posted_at, found_at, tags FROM jobs")
rows = cursor.fetchall()
print(f"Found {len(rows)} jobs to migrate...")

batch = []
for row in rows:
    job_id, company, title, location, url, posted_at, found_at, tags_blob = row
    # Deserialize PickleType tags (restricted unpickler — see _SafeUnpickler)
    try:
        tags = safe_pickle_loads(tags_blob) if tags_blob else []
    except Exception:
        tags = []

    batch.append({
        "id": job_id,
        "company": company,
        "title": title,
        "location": location,
        "url": url,
        "tags": tags
    })

    # Insert in batches of 100
    if len(batch) >= 100:
        supabase.table("jobs").upsert(batch).execute()
        print(f"  Inserted {len(batch)} jobs...")
        batch = []

if batch:
    supabase.table("jobs").upsert(batch).execute()
    print(f"  Inserted {len(batch)} jobs...")

print(f"Migrated {len(rows)} jobs.")

# Migrate subscriptions
cursor.execute("SELECT id, user_id, interest FROM subscriptions")
subs = cursor.fetchall()
print(f"Found {len(subs)} subscriptions to migrate...")

sub_batch = []
for sub_id, user_id, interest in subs:
    sub_batch.append({
        "id": sub_id,
        "user_id": user_id,
        "interest": interest
    })

if sub_batch:
    supabase.table("subscriptions").upsert(sub_batch).execute()

print(f"Migrated {len(subs)} subscriptions.")

conn.close()
print("Migration complete!")
