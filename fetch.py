import requests
import pyodbc
from datetime import datetime

# This script fetches and inserts scrobbling data into the SQL database.

# ==============================
# CONFIG
# ==============================

API_KEY = "71f072d72138772aa0561012523d3e4f"
USERNAME = "maxkcl"

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MKCL\MSSQLSERVER01;"
    "DATABASE=DB_MusicTracker;"
    "Trusted_Connection=yes;"
)
cur = conn.cursor()

# ==============================
# CACHE
# ==============================

artist_cache = {}
album_cache = {}
song_cache = {}

def preload_cache():
    print("Preloading cache...")

    cur.execute("SELECT ID, ArtistName FROM tbl_Artist")
    for row in cur.fetchall():
        artist_cache[row[1]] = row[0]

    cur.execute("SELECT ID, AlbumName, Artist_FK FROM tbl_Album")
    for row in cur.fetchall():
        album_cache[(row[1], row[2])] = row[0]

    cur.execute("SELECT ID, SongName, Artist_FK, Album_FK FROM tbl_Song")
    for row in cur.fetchall():
        song_cache[(row[1], row[2], row[3])] = row[0]

    print(f"Cached {len(artist_cache)} artists, {len(album_cache)} albums, {len(song_cache)} songs")

# ==============================
# DB HELPERS (CACHED)
# ==============================

def get_or_create_artist(name):
    if name in artist_cache:
        return artist_cache[name]

    cur.execute("SELECT ID FROM tbl_Artist WHERE ArtistName = ?", name)
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
    key = (name, artist_id)

    if key in album_cache:
        return album_cache[key]

    cur.execute("""
        SELECT ID FROM tbl_Album 
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
    key = (name, artist_id, album_id)

    if key in song_cache:
        return song_cache[key]

    cur.execute("""
        SELECT ID FROM tbl_Song
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


def scrobble_exists(song_id, timestamp):
    cur.execute("""
        SELECT 1 FROM tbl_Scrobble
        WHERE Song_FK = ? AND DatetimePlayed = ?
    """, song_id, timestamp)
    return cur.fetchone() is not None


def insert_scrobble(song_id, timestamp):
    cur.execute("""
        INSERT INTO tbl_Scrobble (Song_FK, DatetimePlayed)
        VALUES (?, ?)
    """, song_id, timestamp)

# ==============================
# LAST.FM API
# ==============================

def get_recent_tracks(page=1):
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "user.getRecentTracks",
        "user": USERNAME,
        "api_key": API_KEY,
        "format": "json",
        "limit": 200,
        "page": page
    }
    return requests.get(url, params=params).json()

# ==============================
# MAIN SYNC LOGIC
# ==============================

def sync():
    preload_cache()

    page = 1
    total_inserted = 0
    stop = False

    while not stop:
        print(f"Fetching page {page}...")
        data = get_recent_tracks(page)

        tracks = data["recenttracks"]["track"]

        if not tracks:
            break

        for t in tracks:
            # Skip "now playing"
            if "@attr" in t:
                continue

            artist_name = t["artist"]["#text"]
            album_name = t["album"]["#text"]
            track_name = t["name"]
            timestamp = datetime.fromtimestamp(int(t["date"]["uts"]))

            artist_id = get_or_create_artist(artist_name)
            album_id = get_or_create_album(album_name, artist_id)
            song_id = get_or_create_song(track_name, artist_id, album_id)

            # Incremental stop condition
            if scrobble_exists(song_id, timestamp):
                print("Reached existing scrobble. Stopping sync.")
                stop = True
                break

            insert_scrobble(song_id, timestamp)
            total_inserted += 1

        conn.commit()
        page += 1

    print(f"Done. Inserted {total_inserted} new scrobbles.")

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    sync()