import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo

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

from sqlalchemy import text
from db import engine

# ==============================
# CACHE (IMPORTANT)
# ==============================

artist_cache = {}
album_cache = {}
song_cache = {}
name_fix_cache = {}

# ==============================
# GET OR CREATE FUNCTIONS
# ==============================

def get_last_timestamp(conn):

    row = conn.execute(
        text("""
            SELECT MAX(DatetimePlayed)
            AS MaxDate
            FROM tbl_Scrobble
        """)
    ).fetchone()

    if row and row.MaxDate:
        eastern_dt = row.MaxDate.replace(
            tzinfo=ZoneInfo("America/New_York")
        )

        utc_dt = eastern_dt.astimezone(
            ZoneInfo("UTC")
        )

        return int(utc_dt.timestamp())

    return None
    
def get_earliest_timestamp(conn):

    row = conn.execute(
        text("""
            SELECT MIN(DatetimePlayed)
            AS MinDate
            FROM tbl_Scrobble
        """)
    ).fetchone()

    if row and row.MinDate:
        eastern_dt = row.MinDate.replace(
            tzinfo=ZoneInfo("America/New_York")
        )

        utc_dt = eastern_dt.astimezone(
            ZoneInfo("UTC")
        )

        return int(utc_dt.timestamp())

    return None

def get_or_create_artist(conn, name):

    if not name:
        return None

    name = name.strip()

    if name in artist_cache:
        return artist_cache[name]

    row = conn.execute(
        text("""
            SELECT ID
            FROM tbl_Artist
            WHERE ArtistName = :name
        """),
        {"name": name}
    ).fetchone()

    if row:
        artist_id = row.ID

    else:
        row = conn.execute(
            text("""
                INSERT INTO tbl_Artist (ArtistName)
                OUTPUT INSERTED.ID
                VALUES (:name)
            """),
            {"name": name}
        ).fetchone()

        artist_id = row.ID

    artist_cache[name] = artist_id

    return artist_id

def get_or_create_album(conn, name, artist_id):
    if not name:
        return None

    name = name.strip()
    key = (name, artist_id)

    if key in album_cache:
        return album_cache[key]

    row = conn.execute(
        text("""
            SELECT ID
            FROM tbl_Album
            WHERE AlbumName = :name AND Artist_FK = :artist_id
        """),
        {"name": name, "artist_id": artist_id}
    ).fetchone()

    if row:
        album_id = row.ID
    else:
        row = conn.execute(
            text("""
                INSERT INTO tbl_Album (AlbumName, Artist_FK)
                OUTPUT INSERTED.ID
                VALUES (:name, :artist_id)
            """),
            {"name": name, "artist_id": artist_id}
        ).fetchone()

        album_id = row.ID

    album_cache[key] = album_id
    return album_id

def get_or_create_song(conn, name, artist_id, album_id):
    if not name:
        return None

    name = name.strip()
    key = (name, artist_id, album_id)

    if key in song_cache:
        return song_cache[key]

    print(
        f"LOOKUP: [{repr(name)}] "
        f"artist={artist_id} "
        f"album={album_id}"
    )

    row = conn.execute(
        text("""
            SELECT ID
            FROM tbl_Song
            WHERE SongName = :name AND Artist_FK = :artist_id AND Album_FK = :album_id
        """),
        {"name": name, "artist_id": artist_id, "album_id": album_id}
    ).fetchone()
    print("LOOKUP RESULT:", row)
    if row:
        song_id = row.ID
    else:
        print(
            f"INSERTING: [{name}] "
            f"artist={artist_id} "
            f"album={album_id}"
        )
        row = conn.execute(
            text("""
                INSERT INTO tbl_Song (SongName, Artist_FK, Album_FK)
                OUTPUT INSERTED.ID
                VALUES (:name, :artist_id, :album_id)
            """),
            {"name": name, "artist_id": artist_id, "album_id": album_id}
        ).fetchone()

        song_id = row.ID

    song_cache[key] = song_id
    return song_id

def flush_batch(conn, batch):

    if not batch:
        return

    conn.execute(
        text("""
            INSERT INTO tbl_Scrobble
            (Song_FK, DatetimePlayed)
            VALUES (:song_id, :played)
        """),
        [
            {
                "song_id": row[0],
                "played": row[1]
            }
            for row in batch
        ]
    )

    batch.clear()

# ==============================
# SPELLING FIXES
# ==============================

# This function takes in raw artist, album, and song name data.
# It returns corrected names consistent with the database.
# Ex. Artist: Chyl -> CHYL.
# Album is based on SONG. Ex. SLANDER - Anywhere (Album: Anywhere (feat. shYbeast, PLYA)) -> SLANDER - Anywhere (Album: Anywhere)
# Song: Not Who I Used to Be (feat. Joey Fleming) -> Not Who I Used to Be
def apply_name_fixes(conn, artist_name, album_name, song_name):

    # ----------------------------
    # Cache
    # ----------------------------
    key = (artist_name, album_name, song_name)

    if key in name_fix_cache:
        return name_fix_cache[key]

    # ----------------------------
    # Artist ID
    # ----------------------------
    row = conn.execute(
        text("""
            SELECT ID
            FROM tbl_Artist
            WHERE ArtistName = :name
        """),
        {"name": song_name}
    ).fetchone()

    artist_id = int(row.ID) if row else None

    # ----------------------------
    # Artist redirect
    # ----------------------------
    row = conn.execute(
        text("""
        SELECT A.ID, A.ArtistName
        FROM tbl_RedirectArtist RA
        LEFT JOIN tbl_Artist A ON A.ID = RA.Redirect_FK
        WHERE RA.OldName = :name
    """),
    {"name": artist_name}
    ).fetchone()

    if row:
        artist_id = int(row.ID)
        artist_name = row.ArtistName

    # ----------------------------
    # Album redirect
    # ----------------------------
    row = conn.execute(
        text("""
        SELECT A.AlbumName
        FROM tbl_RedirectAlbum RA
        JOIN tbl_Album A ON A.ID = RA.Redirect_FK
        WHERE RA.OldName = :album
        AND RA.SongName = :song
        AND (RA.Artist_FK IS NULL OR RA.Artist_FK = :artist_id)
    """),
    {"album": album_name, "song": song_name, "artist_id": artist_id}
    ).fetchone()

    if row:
        album_name = row.AlbumName

    # ----------------------------
    # Song redirect
    # ----------------------------
    row = conn.execute(
        text("""
        SELECT S.SongName
        FROM tbl_RedirectSong RS
        LEFT JOIN tbl_Song S ON S.ID = RS.Redirect_FK
        WHERE RS.OldName = :song
        AND (RS.Artist_FK IS NULL OR RS.Artist_FK = :artist_id)
    """),
    {"song": song_name, "artist_id": artist_id}
    ).fetchone()

    if row:
        song_name = row.SongName

    # ----------------------------
    # Cache result
    # ----------------------------
    result = (artist_name, album_name, song_name)

    name_fix_cache[key] = result

    return result

# ==============================
# SYNC FUNCTION
# ==============================

# This function fetches data from last.fm API and pushes it into the database.
def sync():

    batch = []
    affected_dates = set()
    BATCH_SIZE = 500
    page = 1

    seen_ts = set()

    try:
        with engine.begin() as conn:

            last_ts = get_last_timestamp(conn)

            print("Last timestamp:", last_ts)

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

                try:
                    response = requests.get(
                        BASE_URL,
                        params=params,
                        timeout=10
                    )

                    response.raise_for_status()

                    data = response.json()

                except Exception as e:
                    print("Request failed:", e)
                    break

                if "error" in data:
                    print(
                        f"Last.fm error {data['error']}: "
                        f"{data['message']}"
                    )
                    break

                tracks = (
                    data.get("recenttracks", {})
                        .get("track", [])
                )

                if not tracks:
                    print("No new tracks")
                    break

                valid_tracks = [
                    t
                    for t in tracks
                    if (
                        isinstance(t, dict)
                        and "date" in t
                        and "uts" in t["date"]
                    )
                ]

                tracks = sorted(
                    valid_tracks,
                    key=lambda x: int(x["date"]["uts"]),
                    reverse=True
                )

                new_rows = 0

                for t in tracks:

                    if ("@attr" in t and t["@attr"].get("nowplaying")):
                        continue

                    try:
                        timestamp = int(t["date"]["uts"])
                    except (KeyError, TypeError):
                        continue

                    if (timestamp in seen_ts or (last_ts and timestamp <= last_ts)):
                        continue

                    seen_ts.add(timestamp)

                    try:

                        artist_name = (
                            t["artist"]["#text"]
                            if isinstance(
                                t["artist"],
                                dict
                            )
                            else str(t["artist"])
                        )

                        song_name = t["name"]

                        album_name = (
                            t["album"]["#text"]
                            if isinstance(
                                t["album"],
                                dict
                            )
                            else str(t["album"])
                        )

                        artist_name, album_name, song_name = (
                            apply_name_fixes(
                                conn,
                                artist_name,
                                album_name,
                                song_name
                            )
                        )

                    except KeyError:
                        continue

                    dt = (
                        datetime
                        .fromtimestamp(
                            timestamp,
                            tz=ZoneInfo("UTC")
                        )
                        .astimezone(
                            ZoneInfo(
                                "America/New_York"
                            )
                        )
                        .replace(tzinfo=None)
                    )

                    artist_id = get_or_create_artist(
                        conn,
                        artist_name
                    )

                    album_id = get_or_create_album(
                        conn,
                        album_name,
                        artist_id
                    )

                    song_id = get_or_create_song(
                        conn,
                        song_name,
                        artist_id,
                        album_id
                    )

                    batch.append((song_id, dt))

                    new_rows += 1

                    affected_dates.add(dt.date())

                    if len(batch) >= BATCH_SIZE:

                        flush_batch(conn, batch)

                if new_rows == 0:
                    print(
                        "Reached already synced data "
                        "or no valid new tracks"
                    )
                    break

                page += 1

                time.sleep(0.25)

            if batch:
                flush_batch(conn, batch)
    
    except Exception as e:
        print(f"Sync failed: {e}")
        raise

    print("Sync complete")

    return affected_dates

def backfill_older():
    batch = []
    BATCH_SIZE = 500
    with engine.begin() as conn:
        earliest_ts = get_earliest_timestamp(conn)
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
                    flush_batch(conn, batch)
                    conn.commit()

            print(f"Inserted {inserted} older rows")

            page += 1
            time.sleep(0.25)

    flush_batch(conn, batch)
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