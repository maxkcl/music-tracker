import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from db import get_connection

# This script fetches and inserts scrobbling data into the SQL database.

# ==============================
# CONFIG
# ==============================

API_KEY = "71f072d72138772aa0561012523d3e4f"
USERNAME = "maxkcl"

BASE_URL = "http://ws.audioscrobbler.com/2.0/"

# ==============================
# DB SETUP
# ==============================

conn, cur = get_connection()
cur.fast_executemany = True

# ==============================
# CACHE (IMPORTANT)
# ==============================

artist_cache = {}
album_cache = {}
song_cache = {}
name_fix_cache = {}

# ==============================
# HELPERS
# ==============================

def update_daily_stats():
    # Load SQL from file
    with open("SQL/DB_MusicTracker_DML.sql", "r") as f:
        sql_script = f.read()
    try:
        cur.execute(sql_script)
        conn.commit()
        print("We did it joe daily stats updated successfully.")
    except Exception as e:
        print("Error updating daily stats:", e)

# ==============================
# GET OR CREATE FUNCTIONS
# ==============================

def get_or_create_artist(name):
    if not name:
        return None

    name = name.strip()

    if name in artist_cache:
        return artist_cache[name]

    cur.execute("""
        SELECT ID
        FROM tbl_Artist
        WHERE ArtistName = ?
    """, name)

    row = cur.fetchone()

    if row:
        artist_id = row[0]
    else:
        cur.execute("""
            INSERT INTO tbl_Artist (ArtistName)
            OUTPUT INSERTED.ID
            VALUES (?)
        """, name)

        artist_id = cur.fetchone()[0]

    artist_cache[name] = artist_id
    return artist_id


def get_or_create_album(name, artist_id):
    if not name:
        return None

    name = name.strip()
    key = (name, artist_id)

    if key in album_cache:
        return album_cache[key]

    cur.execute("""
        SELECT ID
        FROM tbl_Album
        WHERE AlbumName = ? AND Artist_FK = ?
    """, name, artist_id)

    row = cur.fetchone()

    if row:
        album_id = row[0]
    else:
        cur.execute("""
            INSERT INTO tbl_Album (AlbumName, Artist_FK)
            OUTPUT INSERTED.ID
            VALUES (?, ?)
        """, name, artist_id)

        album_id = cur.fetchone()[0]

    album_cache[key] = album_id
    return album_id


def get_or_create_song(name, artist_id, album_id):
    if not name:
        return None

    name = name.strip()
    key = (name, artist_id, album_id)

    if key in song_cache:
        return song_cache[key]

    cur.execute("""
        SELECT ID
        FROM tbl_Song
        WHERE SongName = ? AND Artist_FK = ? AND Album_FK = ?
    """, name, artist_id, album_id)

    row = cur.fetchone()

    if row:
        song_id = row[0]
    else:
        cur.execute("""
            INSERT INTO tbl_Song (SongName, Artist_FK, Album_FK)
            OUTPUT INSERTED.ID
            VALUES (?, ?, ?)
        """, name, artist_id, album_id)

        song_id = cur.fetchone()[0]

    song_cache[key] = song_id
    return song_id

def get_last_timestamp():
    cur.execute("""
        SELECT MAX(DatetimePlayed)
        FROM tbl_Scrobble
    """)

    row = cur.fetchone()

    if row and row[0]:
        eastern_dt = row[0].replace(tzinfo=ZoneInfo("America/New_York"))
        utc_dt = eastern_dt.astimezone(ZoneInfo("UTC"))
        return int(utc_dt.timestamp())  # convert to UNIX
    return None

def get_earliest_timestamp():
    cur.execute("""
        SELECT MIN(DatetimePlayed)
        FROM tbl_Scrobble
    """)

    row = cur.fetchone()

    if row and row[0]:
        eastern_dt = row[0].replace(tzinfo=ZoneInfo("America/New_York"))
        utc_dt = eastern_dt.astimezone(ZoneInfo("UTC"))
        return int(utc_dt.timestamp())
    return None

def flush_batch(batch):
    if not batch:
        return

    try:
        cur.executemany("""
            INSERT INTO tbl_Scrobble (Song_FK, DatetimePlayed)
            VALUES (?, ?)
        """, batch)
    except Exception as e:
        # fallback: insert individually to skip duplicates
        for row in batch:
            try:
                cur.execute("""
                    INSERT INTO tbl_Scrobble (Song_FK, DatetimePlayed)
                    VALUES (?, ?)
                """, row)
            except:
                pass

    batch.clear()

# ==============================
# SPELLING FIXES
# ==============================

def apply_name_fixes(artist_name, song_name):
    key = (artist_name, song_name)

    if key in name_fix_cache:
        return name_fix_cache[key]

    original_artist = artist_name
    original_song = song_name

    # Artist fix
    cur.execute("""
        SELECT NewName FROM tbl_NameFixes
        WHERE Type = 'artist' AND OldName = ?
    """, artist_name)

    row = cur.fetchone()
    if row:
        artist_name = row[0]

    # Song fix
    cur.execute("""
        SELECT NewName FROM tbl_NameFixes
        WHERE Type = 'song'
        AND OldName = ?
        AND (ArtistContext IS NULL OR ArtistContext = ?)
    """, song_name, artist_name)

    row = cur.fetchone()
    if row:
        song_name = row[0]

    name_fix_cache[key] = (artist_name, song_name)
    return artist_name, song_name

# ==============================
# SYNC FUNCTION
# ==============================

def sync():
    batch = []
    affected_dates = set()
    BATCH_SIZE = 500
    page = 1

    last_ts = get_last_timestamp()
    print("Last timestamp:", last_ts)

    seen_ts = set()  # track timestamps processed in this sync

    while True:
        print(f"Fetching page {page}...")

        params = {
            "method": "user.getrecenttracks",
            "user": USERNAME,
            "api_key": API_KEY,
            "format": "json",
            "limit": 200,
            "page": page
        }

        if last_ts:
            params["from"] = last_ts - 5

        # Request
        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            data = response.json()
        except Exception as e:
            print("Request failed:", e)
            break

        # Handle errors
        if "error" in data:
            print(f"Last.fm error {data['error']}: {data['message']}")
            break

        tracks = data.get("recenttracks", {}).get("track", [])

        if not tracks:
            print("No new tracks")
            break

        # Sort by timestamp descending (newest first)
        valid_tracks = []
        for t in tracks:
            if isinstance(t, dict) and "date" in t and "uts" in t["date"]:
                valid_tracks.append(t)
        tracks = sorted(valid_tracks, key=lambda x: int(x["date"]["uts"]), reverse=True)

        new_rows = 0

        for t in tracks:
            # Skip currently playing
            if "@attr" in t and t["@attr"].get("nowplaying"):
                continue

            try:
                timestamp = int(t["date"]["uts"])
            except (KeyError, TypeError):
                continue

            # Skip duplicates or already synced
            if timestamp in seen_ts or (last_ts and timestamp <= last_ts):
                continue

            seen_ts.add(timestamp)

            try:
                artist_name = t["artist"]["#text"] if isinstance(t["artist"], dict) else str(t["artist"])
                song_name = t["name"]
                album_name = t["album"]["#text"] if isinstance(t["album"], dict) else str(t["album"])
                artist_name, song_name = apply_name_fixes(artist_name, song_name)
            except KeyError:
                continue

            dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York")).replace(tzinfo=None)

            artist_id = get_or_create_artist(artist_name)
            album_id = get_or_create_album(album_name, artist_id)
            song_id = get_or_create_song(song_name, artist_id, album_id)

            batch.append((song_id, dt))
            new_rows += 1
            affected_dates.add(dt.date())

            if len(batch) >= BATCH_SIZE:
                flush_batch(batch)
                conn.commit()
                batch.clear()

        # If no new rows were added on this page, stop fetching
        if new_rows == 0:
            print("Reached already synced data or no valid new tracks")
            break

        page += 1
        time.sleep(0.25)

    # Flush any remaining batch
    flush_batch(batch)
    conn.commit()

    # Update tbl_Day for all affected dates
    update_daily_stats()

    print("Sync complete")

def backfill_older():
    batch = []
    BATCH_SIZE = 500

    earliest_ts = get_earliest_timestamp()
    print("Earliest timestamp:", earliest_ts)

    page = 1

    while True:
        print(f"Backfilling page {page}...")

        params = {
            "method": "user.getrecenttracks",
            "user": USERNAME,
            "api_key": API_KEY,
            "format": "json",
            "limit": 200,
            "page": page
        }

        if earliest_ts:
            params["to"] = earliest_ts

        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            data = response.json()
        except Exception as e:
            print("Request failed:", e)
            break

        if "error" in data:
            print(f"Last.fm error {data['error']}: {data['message']}")
            break

        tracks = data.get("recenttracks", {}).get("track", [])

        if not tracks:
            print("No older tracks left")
            break

        inserted = 0

        for t in tracks:
            if isinstance(t, str):
                continue
            if "@attr" in t and t["@attr"].get("nowplaying"):
                continue

            try:
                artist_name = t["artist"]["#text"]
                song_name = t["name"]
                album_name = t["album"]["#text"]
                timestamp = int(t["date"]["uts"])
            except KeyError:
                continue

            # Stop if we somehow overlap
            if earliest_ts and timestamp >= earliest_ts:
                continue

            dt = datetime.utcfromtimestamp(timestamp)

            artist_id = get_or_create_artist(artist_name)
            album_id = get_or_create_album(album_name, artist_id)
            song_id = get_or_create_song(song_name, artist_id, album_id)

            batch.append((song_id, dt))
            inserted += 1

            if len(batch) >= BATCH_SIZE:
                flush_batch(batch)
                conn.commit()

        print(f"Inserted {inserted} older rows")

        page += 1
        time.sleep(0.25)

    flush_batch(batch)
    conn.commit()
    print("Backfill complete")

def full_sync():
    print("Running incremental sync...")
    sync()

    # print("Running backfill...")
    # backfill_older()

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    full_sync()