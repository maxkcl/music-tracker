from flask import Flask, render_template, request, jsonify
import pyodbc
import pandas as pd
import subprocess
from db import get_connection
from fetch import apply_name_fixes

app = Flask(__name__)

API_KEY = "71f072d72138772aa0561012523d3e4f"
USERNAME = "maxkcl"

BASE_URL = "http://ws.audioscrobbler.com/2.0/"

# ==============================
# DB CONNECTION
# ==============================

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MKCL\MSSQLSERVER01;"
    "DATABASE=DB_MusicTracker;"
    "Trusted_Connection=yes;"
)

conn, cur = get_connection()

# ==============================
# ROUTES
# ==============================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/songlist_page")
def songlist_page():
    return render_template("songlist.html")

@app.route("/sheetscup_page")
def sheetscup_page():
    return render_template("sheetscup.html")

@app.route("/big16_page")
def big16_page():
    return render_template("big16.html")

@app.route("/sgv_page")
def sgv_page():
    return render_template("sgv.html")

# ==============================
# QUERY BUILDER
# ==============================

@app.route("/api/query-builder", methods=["POST"])
def query_builder():
    from flask import request, jsonify

    data = request.json
    select = data.get("select")
    metric = data.get("metric")
    operator = data.get("operator")
    value = data.get("value")
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not all([select, metric, operator, value is not None]):
        return jsonify({"error": "Missing required parameters"}), 400

    # -----------------------------
    # METRIC SQL
    # -----------------------------
    if metric == "plays":
        metric_sql = "COUNT(*)"
    elif metric == "songs":
        metric_sql = "COUNT(DISTINCT so.ID)"
    elif metric == "albums":
        metric_sql = "COUNT(DISTINCT al.ID)"
    else:
        return jsonify({"error": "Invalid metric"}), 400

    scrobble_params = []
    day_params = []

    scrobble_date_filter = ""
    day_date_filter = ""

    if start_date and end_date:
        scrobble_date_filter = "WHERE s.DatetimePlayed >= ? AND s.DatetimePlayed < DATEADD(DAY, 1, ?)"
        day_date_filter = "WHERE DayDate BETWEEN ? AND ?"

        scrobble_params.extend([start_date, end_date])
        day_params.extend([start_date, end_date])

    elif start_date:
        scrobble_date_filter = "WHERE s.DatetimePlayed >= ?"
        day_date_filter = "WHERE DayDate >= ?"

        scrobble_params.append(start_date)
        day_params.append(start_date)

    elif end_date:
        scrobble_date_filter = "WHERE s.DatetimePlayed < DATEADD(DAY, 1, ?)"
        day_date_filter = "WHERE DayDate <= ?"

        scrobble_params.append(end_date)
        day_params.append(end_date)

    # -----------------------------
    # Build SQL query per select type
    # -----------------------------
    if select == "song":
        params = scrobble_params + [value]
        query = f"""
        SELECT so.SongName AS name,
               a.ArtistName AS ArtistName,
               al.AlbumName AS AlbumName,
               {metric_sql} AS value
        FROM tbl_Scrobble s
        JOIN tbl_Song so ON s.Song_FK = so.ID
        JOIN tbl_Artist a ON so.Artist_FK = a.ID
        LEFT JOIN tbl_Album al ON so.Album_FK = al.ID
        {scrobble_date_filter}
        GROUP BY so.SongName, a.ArtistName, al.AlbumName
        HAVING {metric_sql} {operator} ?
        ORDER BY value DESC
        """
    elif select == "album":
        params = scrobble_params + [value]
        query = f"""
        SELECT al.AlbumName AS name,
               a.ArtistName AS ArtistName,
               {metric_sql} AS value
        FROM tbl_Scrobble s
        JOIN tbl_Song so ON s.Song_FK = so.ID
        JOIN tbl_Artist a ON so.Artist_FK = a.ID
        LEFT JOIN tbl_Album al ON so.Album_FK = al.ID
        {scrobble_date_filter}
        GROUP BY al.AlbumName, a.ArtistName
        HAVING {metric_sql} {operator} ?
        ORDER BY value DESC
        """
    elif select == "artist":
        params = scrobble_params + [value]
        query = f"""
        SELECT a.ArtistName AS name,
               {metric_sql} AS value
        FROM tbl_Scrobble s
        JOIN tbl_Song so ON s.Song_FK = so.ID
        JOIN tbl_Artist a ON so.Artist_FK = a.ID
        {scrobble_date_filter}
        GROUP BY a.ArtistName
        HAVING {metric_sql} {operator} ?
        ORDER BY value DESC
        """
    elif select == "day":
        params = day_params + [value]
        query = f"""
        SELECT DayDate AS name,
               NumPlays AS value
        FROM tbl_Day
        WHERE 1=1
        {day_date_filter.replace("WHERE", "AND")}
        AND NumPlays {operator} ?
        ORDER BY value DESC
        """
    elif select == "month":
        params = day_params + [value]
        query = f"""
        SELECT FORMAT(DayDate, 'yyyy-MM') AS name,
               SUM(NumPlays) AS value
        FROM tbl_Day
        {day_date_filter}
        GROUP BY FORMAT(DayDate, 'yyyy-MM')
        HAVING SUM(NumPlays) {operator} ?
        ORDER BY value DESC
        """
    elif select == "year":
        params = day_params + [value]
        query = f"""
        SELECT YEAR(DayDate) AS name,
               SUM(NumPlays) AS value
        FROM tbl_Day
        {day_date_filter}
        GROUP BY YEAR(DayDate)
        HAVING SUM(NumPlays) {operator} ?
        ORDER BY value DESC
        """
    else:
        return jsonify({"error": "Invalid select"}), 400

    # -----------------------------
    # Execute query
    # -----------------------------
    import pandas as pd
    print("QUERY:\n", query)
    print("PARAMS:", params)
    try:
        df = pd.read_sql(query, conn, params=params)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # -----------------------------
    # Map to JS-friendly keys
    # -----------------------------
    results = []
    for _, row in df.iterrows():
        item = {
            "name": str(row.get("name", "")),
            "value": int(row.get("value", 0))
        }

        # Add artist/album where applicable
        if select in ("song", "album"):
            item["artist"] = str(row.get("ArtistName", ""))
        if select == "song":
            item["album"] = str(row.get("AlbumName", ""))

        results.append(item)

    return jsonify(results)

# ==============================
# SPELLING FIXES
# ==============================

@app.route("/artists")
def get_artists():
    cur.execute("""
        SELECT ID, ArtistName
        FROM tbl_Artist
        ORDER BY ArtistName
    """)

    rows = cur.fetchall()

    return [{"id": r[0], "name": r[1]} for r in rows]

@app.route("/songs")
def get_songs():
    artist_id = request.args.get("artist_id")

    cur.execute("""
        SELECT SongName
        FROM tbl_Song
        WHERE Artist_FK = ?
        ORDER BY SongName
    """, artist_id)

    rows = cur.fetchall()

    return jsonify([r[0] for r in rows])

@app.route("/apply_fix", methods=["POST"])
def apply_fix():
    data = request.json

    artist_id = int(data.get("artist_id"))
    song = data.get("song")
    new_name = data.get("new_name")

    if not artist_id or not new_name:
        return {"status": "error", "message": "Missing fields"}, 400

    try:
        # Get artist name
        cur.execute("SELECT ArtistName FROM tbl_Artist WHERE ID = ?", artist_id)
        artist_row = cur.fetchone()

        if not artist_row:
            return {"status": "error", "message": "Artist not found"}

        artist_name = artist_row[0]

        if song:
            # 🎵 SONG FIX

            # Get current song ID
            cur.execute("""
                SELECT ID FROM tbl_Song
                WHERE SongName = ? AND Artist_FK = ?
            """, song, artist_id)

            row = cur.fetchone()
            if not row:
                return {"status": "error", "message": "Song not found"}

            song_id = row[0]
            old_name = song

            # Check for duplicate (case-sensitive, excluding self)
            cur.execute("""
                SELECT ID FROM tbl_Song
                WHERE SongName COLLATE Latin1_General_CS_AS = ?
                AND Artist_FK = ?
                AND ID != ?
            """, new_name, artist_id, song_id)
            dup = cur.fetchone()
            if dup:
                duplicate_id = dup[0]

                # Merge: update all scrobbles to point to the new name
                cur.execute("""
                    UPDATE tbl_Scrobble
                    SET Song_FK = ?
                    WHERE Song_FK = ?
                """, (duplicate_id, song_id))
                cur.execute(f"""
                    UPDATE tbl_Day
                    SET TopSong_FK = ?
                    WHERE TopSong_FK = ?
                """, (duplicate_id, song_id))
                cur.execute(f"""
                    UPDATE tbl_RedirectSong
                    SET Redirect_FK = ?
                    WHERE Redirect_FK = ?
                """, (duplicate_id, song_id))

                # Delete the old song row
                cur.execute("""
                    DELETE FROM tbl_Song
                    WHERE ID = ?
                """, (song_id,))

                # Save mapping in tbl_RedirectSong
                cur.execute("""
                    INSERT INTO tbl_RedirectSong (OldName, Artist_FK, Redirect_FK)
                    VALUES (?, ?, ?)
                """, (old_name, artist_id, duplicate_id))
            else:
                # Safe to update
                cur.execute("""
                    UPDATE tbl_Song
                    SET SongName = ?
                    WHERE ID = ?
                """, new_name, song_id)

                # ✅ Save mapping
                cur.execute("""
                    INSERT INTO tbl_RedirectSong (OldName, Artist_FK, Redirect_FK)
                    VALUES (?, ?, ?)
                """, (old_name, artist_id, song_id))

        else:
            # 🎤 ARTIST FIX

            # Check if artist exists
            cur.execute("""
                SELECT ArtistName FROM tbl_Artist
                WHERE ID = ?
            """, artist_id)

            row = cur.fetchone()
            if not row:
                return {"status": "error", "message": "Artist not found"}

            old_name = row[0]

            # Case-sensitive duplicate check (exclude current artist)
            cur.execute("""
                SELECT 1 FROM tbl_Artist
                WHERE ArtistName COLLATE Latin1_General_CS_AS = ?
                AND ID != ?
            """, new_name, artist_id)

            if cur.fetchone():
                return {"status": "error", "message": "Artist with that name already exists"}

            # ✅ Update artist name
            cur.execute("""
                UPDATE tbl_Artist
                SET ArtistName = ?
                WHERE ID = ?
            """, new_name, artist_id)

            if cur.rowcount == 0:
                return {"status": "error", "message": "Update failed"}

            # ✅ Save mapping
            cur.execute("""
                INSERT INTO tbl_RedirectArtist (OldName, Redirect_FK)
                VALUES (?, ?)
            """, old_name, artist_id)

        conn.commit()
        return {"status": "ok"}

    except Exception as e:
        print("❌ APPLY FIX ERROR:", e)
        conn.rollback()
        return {"status": "error", "message": str(e)}

# Song duplicate merger
@app.route("/api/song-duplicates")
def get_song_duplicates():
    import pandas as pd

    query = """
    SELECT 
        so.SongName,
        so.Artist_FK,
        a.ArtistName,
        COUNT(s.ID) AS total_plays,
        COUNT(DISTINCT so.ID) AS versions
    FROM tbl_Song so
    JOIN tbl_Artist a ON so.Artist_FK = a.ID
    LEFT JOIN tbl_Scrobble s ON s.Song_FK = so.ID
    GROUP BY so.SongName, so.Artist_FK, a.ArtistName
    HAVING COUNT(DISTINCT so.ID) > 1
    ORDER BY total_plays DESC
    """

    df = pd.read_sql(query, conn)
    return jsonify(df.to_dict(orient="records"))

@app.route("/api/song-duplicates/details")
def get_duplicate_details():
    song = request.args.get("song")
    artist_fk = request.args.get("artist_fk")

    query = """
    SELECT 
        so.ID,
        so.SongName,
        al.AlbumName,
        COUNT(s.ID) AS plays
    FROM tbl_Song so
    LEFT JOIN tbl_Album al ON so.Album_FK = al.ID
    LEFT JOIN tbl_Scrobble s ON s.Song_FK = so.ID
    WHERE so.SongName = ? AND so.Artist_FK = ?
    GROUP BY so.ID, so.SongName, al.AlbumName
    ORDER BY plays DESC
    """

    import pandas as pd
    df = pd.read_sql(query, conn, params=[song, artist_fk])

    return jsonify(df.to_dict(orient="records"))

@app.route("/api/song-duplicates/merge", methods=["POST"])
def merge_duplicates():
    data = request.get_json()

    song_name = data.get("song_name")
    artist_id = int(data.get("artist_id"))
    canon_id = int(data.get("canon_id"))
    song_ids = [int(sid) for sid in data.get("song_ids")]
    
    if not all([canon_id, song_name, artist_id]):
        return {"status": "error", "message": "Missing parameters"}, 400

    try:
        # Remove canonical ID
        duplicate_ids = [sid for sid in song_ids if sid != canon_id]

        if canon_id in duplicate_ids:
            return jsonify({"error": "Canonical ID included in delete set"}), 400

        placeholders = ",".join("?" * len(duplicate_ids))

        # Update ONLY duplicate IDs
        cur.execute(f"""
            UPDATE tbl_Scrobble
            SET Song_FK = ?
            WHERE Song_FK IN ({placeholders})
        """, [canon_id] + duplicate_ids)
        cur.execute(f"""
            UPDATE tbl_Day
            SET TopSong_FK = ?
            WHERE TopSong_FK IN ({placeholders})
        """, [canon_id] + duplicate_ids)
        cur.execute(f"""
            UPDATE tbl_RedirectSong
            SET Redirect_FK = ?
            WHERE Redirect_FK IN ({placeholders})
        """, [canon_id] + duplicate_ids)

        # Delete ONLY those
        cur.execute(f"""
            DELETE FROM tbl_Song
            WHERE ID IN ({placeholders})
        """, duplicate_ids)

        # Save mapping in tbl_RedirectSong
        cur.execute("""
            INSERT INTO tbl_RedirectSong (OldName, Artist_FK, Redirect_FK)
            VALUES (?, ?, ?)
        """, (song_name, artist_id, canon_id))

        conn.commit()
        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ APPLY FIX ERROR:", e)
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)})

# ==============================
# SONG LIST
# ==============================

@app.route("/api/songlist")
def get_songlist():
    import pandas as pd

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    params = []
    date_filter = ""

    if start_date and end_date:
        date_filter = """
        WHERE s.DatetimePlayed >= ? 
        AND s.DatetimePlayed < DATEADD(DAY, 1, ?)
        """
        params.extend([start_date, end_date])
    elif start_date:
        date_filter = "WHERE s.DatetimePlayed >= ?"
        params.append(start_date)

    elif end_date:
        date_filter = "WHERE s.DatetimePlayed < DATEADD(DAY, 1, ?)"
        params.append(end_date)

    query = f"""
    SELECT 
        so.SongName AS name,
        a.ArtistName AS artist,
        al.AlbumName AS album,
        MIN(s.DatetimePlayed) AS first_played,
        MAX(s.DatetimePlayed) AS last_played,
        COUNT(*) AS value
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON s.Song_FK = so.ID
    JOIN tbl_Artist a ON so.Artist_FK = a.ID
    LEFT JOIN tbl_Album al ON so.Album_FK = al.ID
    {date_filter}
    GROUP BY so.SongName, a.ArtistName, al.AlbumName
    ORDER BY value DESC
    """

    df = pd.read_sql(query, conn, params=params)

    results = []
    for _, row in df.iterrows():
        results.append({
            "name": str(row["name"]),
            "artist": str(row["artist"]),
            "album": str(row["album"]) if row["album"] else "",
            "first_played": row["first_played"].isoformat() if row["first_played"] else "",
            "last_played": row["last_played"].isoformat() if row["last_played"] else "",
            "value": int(row["value"])
        })

    return jsonify(results)

# ==============================
# SHEETS CUP
# ==============================

@app.route("/api/sheetscup")
def get_sheetscup():
    import pandas as pd

    query = """
    WITH MonthlyRanks AS (
        SELECT 
            YEAR(s.DatetimePlayed) AS yr,
            MONTH(s.DatetimePlayed) AS mn,
            a.ArtistName AS artist,
            COUNT(*) AS plays,
            ROW_NUMBER() OVER (
                PARTITION BY YEAR(s.DatetimePlayed), MONTH(s.DatetimePlayed)
                ORDER BY COUNT(*) DESC
            ) AS rn
        FROM tbl_Scrobble s
        JOIN tbl_Song so ON so.ID = s.Song_FK
        JOIN tbl_Artist a ON a.ID = so.Artist_FK
        WHERE s.DatetimePlayed >= '2020-12-01'
        GROUP BY 
            YEAR(s.DatetimePlayed),
            MONTH(s.DatetimePlayed),
            a.ArtistName
    )
    SELECT yr, mn, artist, plays
    FROM MonthlyRanks
    WHERE rn <= 50
    ORDER BY yr, mn, plays DESC
    """

    df = pd.read_sql(query, conn)

    return jsonify(df.to_dict(orient="records"))

# ==============================
# BIG 16
# ==============================

@app.route("/api/big16")
def get_big16():
    import pandas as pd

    query = """
    WITH Scrobbles AS (
    SELECT 
        Song_FK,
        YEAR(DatetimePlayed) AS Y,
        MONTH(DatetimePlayed) AS M,
        COUNT(*) AS ScrobbleCount
    FROM tbl_Scrobble
    GROUP BY 
        Song_FK,
        YEAR(DatetimePlayed),
        MONTH(DatetimePlayed)
    )

    SELECT 
        B.Rank,
        ISNULL(SC.ScrobbleCount, 0) AS Plays,
        S.SongName,
        A.ArtistName,
        M.MonthDate,
        M.Year,
        M.Month

    FROM tbl_Big16 B
    JOIN tbl_Month M ON M.ID = B.Month_FK
    JOIN tbl_Song S ON S.ID = B.Song_FK
    JOIN tbl_Artist A ON A.ID = S.Artist_FK

    LEFT JOIN Scrobbles SC
        ON SC.Song_FK = B.Song_FK
        AND SC.Y = M.Year
        AND SC.M = M.Month

    ORDER BY M.MonthDate, B.Rank
    """
    
    df = pd.read_sql(query, conn)

    return jsonify(df.to_dict(orient="records"))


# ==============================
# SGV
# ==============================
@app.route('/api/sgv-build-songs', methods=['GET'])
def build_song_ratings():
    """
    Builds weighted 1–99 song ratings using:
    - Big16 performance (points, appearances, first places)
    - Decayed scrobbles (time-weighted popularity)
    """

    import pandas as pd
    import numpy as np

    query = """
    WITH Big16Agg AS (
            SELECT 
                Song_FK,
                SUM(Points) AS TotalPoints,
                COUNT(*) AS Appearances,
                COUNT(CASE WHEN Rank = 1 THEN 1 END) AS FirstPlaces,
                SUM(
                    CASE
                        WHEN M.MonthDate >= DATEADD(day, -120, GETDATE())
                        THEN Points ELSE 0
                    END
                ) AS RecentPoints
            FROM tbl_Big16
            LEFT JOIN tbl_Month M ON M.ID = Month_FK
            GROUP BY Song_FK
        ),
        ScrobbleAgg AS (
            SELECT 
                Song_FK,
                COUNT(*) AS TotalScrobbles,
                SUM(
                    POWER(
                        0.5,
                        CAST(DATEDIFF(day, DatetimePlayed, GETDATE()) AS FLOAT) / 365.25
                    )
                ) AS DecayedScrobbles,
                SUM(
                    CASE
                        WHEN DatetimePlayed >= DATEADD(day, -60, GETDATE())
                        THEN 1 ELSE 0
                    END
                ) AS RecentScrobbles
            FROM tbl_Scrobble
            GROUP BY Song_FK
        )
        SELECT
            s.ID,
            s.SongName,
            a.ArtistName,
            al.AlbumName,
            ISNULL(b.TotalPoints, 0) AS TotalPoints,
            ISNULL(b.Appearances, 0) AS Appearances,
            ISNULL(b.FirstPlaces, 0) AS FirstPlaces,
            ISNULL(b.RecentPoints, 0) AS RecentPoints,
            ISNULL(sc.TotalScrobbles, 0) AS TotalScrobbles,
            ISNULL(sc.DecayedScrobbles, 0) AS DecayedScrobbles,
            ISNULL(sc.RecentScrobbles, 0) AS RecentScrobbles
        FROM tbl_Song s
        LEFT JOIN Big16Agg b ON b.Song_FK = s.ID
        LEFT JOIN ScrobbleAgg sc ON sc.Song_FK = s.ID
        LEFT JOIN tbl_Artist a ON a.ID = s.Artist_FK
        LEFT JOIN tbl_Album al ON al.ID = s.Album_FK
    """

    df = pd.read_sql(query, conn)

    # ----------------------------
    # Safe normalization helper
    # ----------------------------
    
    def norm(x):
        return (x - x.min()) / (x.max() - x.min() + 1e-9)

    # ----------------------------
    # Normalize features
    # ----------------------------

    df["base"] = np.log1p(df["DecayedScrobbles"])

    df["legacy"] = (
        df["TotalPoints"] * 0.6 +
        df["FirstPlaces"] * 2 +
        np.log1p(df["TotalScrobbles"]) * 0.4
    )

    df["recency"] = (
        np.log1p(df["RecentScrobbles"]) * 4.5 +
        df["RecentPoints"] * 2 +
        df["FirstPlaces"] * 0.7
    )

    df["base_n"] = norm(df["base"])
    df["base_rating"] = 50 + df["base_n"] * 35

    df["legacy_n"] = norm(df["legacy"])
    df["recency_n"] = norm(df["recency"])

    # ----------------------------
    # Weighted scoring model
    # ----------------------------
    
    df["score"] = (
        df["base_rating"] * 0.5 +
        df["legacy_n"] * 0.9 +
        df["recency_n"] * 8
    )

    # ----------------------------
    # Convert to 1–99 rating
    # ----------------------------

    df["rating"] = (df["score"] ** 1.2)
    df["rating"] = df["rating"].clip(1, 99).round().astype(int)

    # ----------------------------
    # Sort for convenience
    # ----------------------------
    df = df.sort_values("rating", ascending=False)

    return df

@app.route("/api/sgv-update-ratings", methods=["POST"])
def sgv_update_ratings():
    try:
        df = build_song_ratings()

        # ----------------------------
        # Create snapshot row
        # ----------------------------

        cur.execute("INSERT INTO tbl_SGVSnapshot DEFAULT VALUES")
        conn.commit()

        snapshot_id = cur.execute("SELECT SCOPE_IDENTITY()").fetchone()[0]

        # ----------------------------
        # Insert song data
        # ----------------------------

        rows = [
            (
                snapshot_id,
                int(row.ID),
                int(row.rating),
                int(row.TotalPoints),
                int(row.FirstPlaces),
                int(row.Appearances),
                int(row.TotalScrobbles),
                int(row.DecayedScrobbles),
                float(row.base_rating),
                float(row.legacy_n),
                float(row.recency_n)
            )
            for _, row in df.iterrows()
        ]

        cur.executemany("""
            INSERT INTO tbl_SGVSongs
            (Snapshot_FK, Song_FK, Rating, TP, N1s, MIC, Plays, DecayedPlays, BaseRating, LegacyScore, RecencyScore)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)

        conn.commit()

        return jsonify({"status": "success", "snapshot_id": snapshot_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sgv-get-ratings")
def get_latest_ratings():
    query = """
    WITH LatestSnapshot AS (
        SELECT MAX(ID) AS SnapshotID
        FROM tbl_SGVSnapshot
    )
    SELECT 
        s.SongName,
        a.ArtistName,
        r.Rating,
        r.TP,
        r.N1s,
        r.MIC,
        r.Plays,
        r.DecayedPlays
    FROM tbl_SGVSongs r
    JOIN LatestSnapshot ls ON r.Snapshot_FK = ls.SnapshotID
    JOIN tbl_Song s ON s.ID = r.Song_FK
    JOIN tbl_Artist a ON a.ID = s.Artist_FK
    ORDER BY r.Rating DESC
    """

    df = pd.read_sql(query, conn)
    return jsonify(df.to_dict(orient="records"))

# ==============================
# SYNC
# ==============================

@app.route('/run-fetch', methods=['POST'])
def run_fetch():
    try:
        result = subprocess.run(
            ['python', 'fetch.py'],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({'success': True, 'output': result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'success': False, 'error': e.stderr})

# ==============================
# NOW PLAYING BANNER
# ==============================

@app.route("/api/now-playing")
def now_playing():
    import requests

    params = {
        "method": "user.getrecenttracks",
        "user": USERNAME,
        "api_key": API_KEY,
        "format": "json",
        "limit": 1
    }

    try:
        res = requests.get(BASE_URL, params=params, timeout=5)
        data = res.json()

        track = data.get("recenttracks", {}).get("track", [])
        if not track:
            return {"playing": False}

        track = track[0]

        # Check if currently playing
        if "@attr" in track and track["@attr"].get("nowplaying"):
            artist_name, song_name = apply_name_fixes(track.get("artist", {}).get("#text"), track.get("name"))
            return {
                "playing": True,
                "song": song_name,
                "artist": artist_name,
                "album": track.get("album", {}).get("#text")
            }

        return {"playing": False}

    except Exception as e:
        print("Now playing error:", e)
        return {"playing": False}

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    app.run(debug=True)