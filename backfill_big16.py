import pyodbc
import pandas as pd
import re
from db import get_connection

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MKCL\MSSQLSERVER01;"
    "DATABASE=DB_MusicTracker;"
    "Trusted_Connection=yes;"
)

conn, cur = get_connection()

# 1. Load CSV
df = pd.read_csv("big16.csv")

# 2. Melt
df_long = df.melt(
    id_vars=["Song Name", "Artist"],
    var_name="Month",
    value_name="Rank"
).dropna(subset=["Rank"])

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\(feat.*?\)", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()

# 3. Normalize
df_long["song_norm"] = df_long["Song Name"].apply(normalize)
df_long["artist_norm"] = df_long["Artist"].apply(normalize)

# 4. Load songs from DB
songs = pd.read_sql("""
SELECT so.ID, so.SongName, so.Artist_FK, a.ArtistName
FROM tbl_Song so
JOIN tbl_Artist a ON a.ID = so.Artist_FK
""", conn)

songs["song_norm"] = songs["SongName"].apply(normalize)
songs["artist_norm"] = songs["ArtistName"].apply(normalize)

# Match logic
def find_song_id(row, cur):
    """
    Returns a tuple (song_id, reason)
    reason is None if exact match found, otherwise a string explaining why unmatched.
    """
    song_name = row["Song Name"]
    artist_name = row["Artist"]

    cur.execute("""
        SELECT so.ID
        FROM tbl_Song so
        JOIN tbl_Artist a ON so.Artist_FK = a.ID
        WHERE so.SongName = ? AND a.ArtistName = ?
    """, (song_name, artist_name))
    
    result = cur.fetchone()
    
    if result:
        return result[0], None  # matched!
    
    # Check if artist exists at all
    cur.execute("SELECT ID FROM tbl_Artist WHERE ArtistName = ?", (artist_name,))
    artist = cur.fetchone()
    if not artist:
        return None, "Artist not found"
    
    # Artist exists, song does not
    return None, "Song not found for artist"

# 6. Build month map
months = pd.read_sql("SELECT ID, MonthDate FROM tbl_Month", conn)
month_map = dict(zip(months["MonthDate"].astype(str), months["ID"]))

# =========================
# GET OR CREATES
# =========================
def get_or_create_album(name, artist_id):
    if not name:
        return None

    name = name.strip()

    cur.execute("""
        SELECT ID
        FROM tbl_Album
        WHERE AlbumName = ? AND Artist_FK = ?
    """, (name, artist_id))

    row = cur.fetchone()

    if row:
        album_id = row[0]
    else:
        cur.execute("""
            INSERT INTO tbl_Album (AlbumName, Artist_FK)
            OUTPUT INSERTED.ID
            VALUES (?, ?)
        """, (name, artist_id))

        album_id = cur.fetchone()[0]

    return album_id

def get_or_create_song(name, artist_id, album_id):
    if not name:
        return None

    name = name.strip()

    cur.execute("""
        SELECT ID
        FROM tbl_Song
        WHERE SongName = ? AND Artist_FK = ? AND Album_FK = ?
    """, (name, artist_id, album_id))

    row = cur.fetchone()

    if row:
        song_id = row[0]
    else:
        cur.execute("""
            INSERT INTO tbl_Song (SongName, Artist_FK, Album_FK)
            OUTPUT INSERTED.ID
            VALUES (?, ?, ?)
        """, (name, artist_id, album_id))

        song_id = cur.fetchone()[0]

    return song_id

# =========================
# INTERACTIVE HELPER
# =========================

def prompt_for_song(row, artist_id):
    print("\n--- NEW SONG DETECTED ---")
    print(f"Song:   {row['Song Name']}")
    print(f"Artist: {row['Artist']}")
    print(f"Month:  {row['Month']} | Rank: {row['Rank']}")

    # Ask for album (REQUIRED)
    album_name = input("Enter album name (required): ").strip()

    while not album_name:
        album_name = input("Album cannot be empty. Enter album name: ").strip()

    # Create / get album
    album_id = get_or_create_album(album_name, artist_id)

    # Create / get song
    song_id = get_or_create_song(row["Song Name"], artist_id, album_id)

    print(f"✔ Created song ID {song_id} under album '{album_name}'\n")

    return song_id

# =========================
# 🔥 7. INSERT LOOP HERE
# =========================

unmatched_log = []

for _, row in df_long.iterrows():
    song_id, reason = find_song_id(row, cur)

    if not song_id:
        # We now CREATE instead of skipping

        # Get artist_id (you said all artists now exist 👍)
        cur.execute("SELECT ID FROM tbl_Artist WHERE ArtistName = ?", (row["Artist"],))
        artist_row = cur.fetchone()

        if not artist_row:
            print(f"❌ Unexpected: artist missing {row['Artist']}")
            continue

        artist_id = artist_row[0]

        # 🔥 PROMPT USER
        song_id = prompt_for_song(row, artist_id)

    month_id = month_map[row["Month"]]
    rank = int(row["Rank"])
    pts = 17 - rank

    cur.execute("""
        INSERT INTO tbl_Big16 (Month_FK, Song_FK, Rank, Points)
        VALUES (?, ?, ?, ?)
    """, (int(month_id), int(song_id), int(rank), pts))

# =========================
# 8. EXPORT LOGS
# =========================

if unmatched_log:
    pd.DataFrame(unmatched_log).to_csv("unmatched_songs.csv", index=False)

# 9. Commit (optional during testing)
conn.commit()