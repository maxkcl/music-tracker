from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

import pandas as pd
import time
import math

from sqlalchemy import text

from db import (
    engine,
    run_query,
    run_multi,
    run_execute,
    run_snapshot_transaction,
    replace_na
)

from fetch import (apply_name_fixes, sync)

app = Flask(__name__)
CORS(app)


API_KEY = "71f072d72138772aa0561012523d3e4f"
USERNAME = "maxkcl"

BASE_URL = "http://ws.audioscrobbler.com/2.0/"

# ==============================
# DB Connection
# ==============================
#region DB Connection

from sqlalchemy import text
from db import engine

#endregion

# ==============================
# HELPERS
# ==============================
#region Helpers

def safe_int(x):
    import math
    return int(x) if x is not None and not math.isnan(x) else 0

def safe_float(x):
    import math
    return float(x) if x is not None and not math.isnan(x) else 0.0

#endregion

# ==============================
# ROUTES
# ==============================
#region Routes

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

@app.route("/team_page")
def team_page():
    return render_template("team.html")

@app.route("/artist/<int:artist_id>")
def artist_page(artist_id):
    return render_template("artist.html", artist_id=artist_id)

@app.route("/song/<int:song_id>")
def song_page(song_id):
    return render_template("song.html", song_id=song_id)

#endregion

# ==============================
# ARTIST / SONG PAGE CACHING
# ==============================
#region Page Cache

ARTIST_CACHE = {}
SONG_CACHE = {}
CACHE_TTL_SECONDS = 60 * 10 # 10 minutes

def get_cached_artist(artist_id):
    entry = ARTIST_CACHE.get(artist_id)

    if entry:
        data, ts = entry
        if time.time() - ts < CACHE_TTL_SECONDS:
            return data

    return None

def set_cached_artist(artist_id, data):
    ARTIST_CACHE[artist_id] = (data, time.time())

def get_cached_song(song_id):
    import time
    entry = SONG_CACHE.get(song_id)
    if entry:
        data, ts = entry
        if time.time() - ts < CACHE_TTL_SECONDS:
            return data
    return None

def set_cached_song(song_id, data):
    import time
    SONG_CACHE[song_id] = (data, time.time())

#endregion

# ============================== ** REVAMP NEEDED **
# QUERY BUILDER
# ==============================
#region Query Builder

# This function is a mess and needs to be revamped completely.
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
    print("QUERY:\n", query)
    print("PARAMS:", params)
    try:
        df = run_query(query, params=params)
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

#endregion

# ==============================
# SPELLING FIXES
# ==============================
#region Spelling Fixes

@app.route("/artists")
def get_artists():
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT ID, ArtistName
                    FROM tbl_Artist
                    ORDER BY ArtistName
                """)
            ).fetchall()

        return [{"id": row.ID, "name": row.ArtistName} for row in rows]

    except Exception as e:
        print(e)

        return {"error": str(e)}, 500

@app.route("/songs")
def get_songs():
    artist_id = request.args.get("artist_id")

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT SongName
                FROM tbl_Song
                WHERE Artist_FK = :artist_id
                ORDER BY SongName
            """),
            {"artist_id": artist_id}
        ).fetchall()

    return jsonify([row.SongName for row in rows])

@app.route("/apply_fix", methods=["POST"])
def apply_fix():
    data = request.json

    artist_id = int(data.get("artist_id"))
    song = data.get("song")
    new_name = data.get("new_name")

    if not artist_id or not new_name:
        return {
            "status": "error",
            "message": "Missing fields"
        }, 400

    try:
        with engine.begin() as conn:
            # ----------------------------
            # Get artist
            # ----------------------------
            row = conn.execute(
                text("""
                    SELECT ArtistName
                    FROM tbl_Artist
                    WHERE ID = :artist_id
                """),
                {"artist_id": artist_id}
            ).fetchone()

            if not row:
                return {
                    "status": "error",
                    "message": "Artist not found"
                }

            artist_name = row.ArtistName

            # ==================================================
            # SONG FIX
            # ==================================================
            if song:
                row = conn.execute(
                    text("""
                        SELECT ID
                        FROM tbl_Song
                        WHERE SongName = :song
                        AND Artist_FK = :artist_id
                    """),
                    {
                        "song": song,
                        "artist_id": artist_id
                    }
                ).fetchone()

                if not row:
                    return {
                        "status": "error",
                        "message": "Song not found"
                    }

                song_id = row.ID

                dup = conn.execute(
                    text("""
                        SELECT ID
                        FROM tbl_Song
                        WHERE SongName COLLATE Latin1_General_CS_AS = :new_name
                        AND Artist_FK = :artist_id
                        AND ID != :song_id
                    """),
                    {
                        "new_name": new_name,
                        "artist_id": artist_id,
                        "song_id": song_id
                    }
                ).fetchone()

                # ----------------------------
                # Merge into existing song
                # ----------------------------
                if dup:
                    duplicate_id = dup.ID

                    conn.execute(
                        text("""
                            UPDATE tbl_Scrobble
                            SET Song_FK = :duplicate_id
                            WHERE Song_FK = :song_id
                        """),
                        {
                            "duplicate_id": duplicate_id,
                            "song_id": song_id
                        }
                    )
                    conn.execute(
                        text("""
                            UPDATE tbl_Day
                            SET TopSong_FK = :duplicate_id
                            WHERE TopSong_FK = :song_id
                        """),
                        {
                            "duplicate_id": duplicate_id,
                            "song_id": song_id
                        }
                    )
                    conn.execute(
                        text("""
                            UPDATE tbl_SGVSongs
                            SET Song_FK = :duplicate_id
                            WHERE Song_FK = :song_id
                        """),
                        {
                            "duplicate_id": duplicate_id,
                            "song_id": song_id
                        }
                    )
                    conn.execute(
                        text("""
                            DELETE FROM tbl_Song
                            WHERE ID = :song_id
                        """),
                        {
                            "song_id": song_id
                        }
                    )
                    conn.execute(
                        text("""
                            INSERT INTO tbl_RedirectSong (OldName, Artist_FK, Redirect_FK)
                            VALUES
                            (:old_name, :artist_id, :redirect_id)
                        """),
                        {
                            "old_name": song,
                            "artist_id": artist_id,
                            "redirect_id": duplicate_id
                        }
                    )

                # ----------------------------
                # Simple rename
                # ----------------------------
                else:
                    conn.execute(
                        text("""
                            UPDATE tbl_Song
                            SET SongName = :new_name
                            WHERE ID = :song_id
                        """),
                        {
                            "new_name": new_name,
                            "song_id": song_id
                        }
                    )
                    conn.execute(
                        text("""
                            INSERT INTO tbl_RedirectSong(OldName, Artist_FK, Redirect_FK)
                            VALUES
                            (:old_name, :artist_id, :song_id)
                        """),
                        {
                            "old_name": song,
                            "artist_id": artist_id,
                            "song_id": song_id
                        }
                    )

            # ==================================================
            # ARTIST FIX
            # ==================================================
            else:
                exists = conn.execute(
                    text("""
                        SELECT 1
                        FROM tbl_Artist
                        WHERE ArtistName COLLATE Latin1_General_CS_AS = :new_name
                        AND ID != :artist_id
                    """),
                    {
                        "new_name": new_name,
                        "artist_id": artist_id
                    }
                ).fetchone()

                if exists:
                    return {
                        "status": "error",
                        "message": "Artist already exists"
                    }

                conn.execute(
                    text("""
                        UPDATE tbl_Artist
                        SET ArtistName = :new_name
                        WHERE ID = :artist_id
                    """),
                    {
                        "new_name": new_name,
                        "artist_id": artist_id
                    }
                )
                conn.execute(
                    text("""
                        INSERT INTO tbl_RedirectArtist (OldName, Redirect_FK)
                        VALUES
                        (:old_name, :artist_id)
                    """),
                    {
                        "old_name": artist_name,
                        "artist_id": artist_id
                    }
                )

        return {
            "status": "ok"
        }

    except Exception as e:

        print("apply_fix failed:", e)

        return {
            "status": "error",
            "message": str(e)
        }, 500

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

    df = run_query(query)
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
    WHERE so.SongName = :song AND so.Artist_FK = :artist_fk
    GROUP BY so.ID, so.SongName, al.AlbumName
    ORDER BY plays DESC
    """

    df = run_query(query, params={"song": song, "artist_fk": artist_fk})

    return jsonify(df.to_dict(orient="records"))

from sqlalchemy import text

@app.route("/api/song-duplicates/merge", methods=["POST"])
def merge_duplicates():

    data = request.get_json()

    song_name = data.get("song_name")
    artist_id = int(data.get("artist_id"))
    canon_id = int(data.get("canon_id"))
    song_ids = [int(sid) for sid in data.get("song_ids", [])]

    if not all([song_name, artist_id, canon_id]):
        return jsonify({
            "status": "error",
            "message": "Missing parameters"
        }), 400

    duplicate_ids = [sid for sid in song_ids if sid != canon_id]

    if canon_id in duplicate_ids:
        return jsonify({"status": "error", "message": "Canonical ID included in delete set"}), 400

    try:

        with engine.begin() as conn:

            # --------------------------------
            # Canonical album
            # --------------------------------

            canon_album = conn.execute(
                text("""
                    SELECT Album_FK
                    FROM tbl_Song
                    WHERE ID = :canon_id
                """),
                {"canon_id": canon_id}
            ).fetchone()

            if not canon_album:
                return jsonify({
                    "status": "error",
                    "message": "Canonical song not found"
                }), 404

            canon_album_id = canon_album.Album_FK

            # --------------------------------
            # Duplicate album names
            # --------------------------------

            album_names = []

            if duplicate_ids:

                placeholders = ", ".join(
                    f":id{i}" for i in range(len(duplicate_ids))
                )

                params = {
                    f"id{i}": sid
                    for i, sid in enumerate(duplicate_ids)
                }

                album_rows = conn.execute(
                    text(f"""
                        SELECT DISTINCT a.AlbumName
                        FROM tbl_Song s
                        JOIN tbl_Album a
                            ON a.ID = s.Album_FK
                        WHERE s.ID IN ({placeholders})
                    """),
                    params
                ).fetchall()

                album_names = [row.AlbumName for row in album_rows]

            # --------------------------------
            # Merge duplicates
            # --------------------------------

            if duplicate_ids:

                placeholders = ", ".join(
                    f":id{i}" for i in range(len(duplicate_ids))
                )

                params = {
                    "canon_id": canon_id,
                    **{
                        f"id{i}": sid
                        for i, sid in enumerate(duplicate_ids)
                    }
                }

                conn.execute(
                    text(f"""
                        UPDATE tbl_Scrobble
                        SET Song_FK = :canon_id
                        WHERE Song_FK IN ({placeholders})
                    """),
                    params
                )

                conn.execute(
                    text(f"""
                        UPDATE tbl_Day
                        SET TopSong_FK = :canon_id
                        WHERE TopSong_FK IN ({placeholders})
                    """),
                    params
                )

                conn.execute(
                    text(f"""
                        UPDATE tbl_SGVSongs
                        SET Song_FK = :canon_id
                        WHERE Song_FK IN ({placeholders})
                    """),
                    params
                )

                conn.execute(
                    text(f"""
                        UPDATE tbl_RedirectSong
                        SET Redirect_FK = :canon_id
                        WHERE Redirect_FK IN ({placeholders})
                    """),
                    params
                )

                conn.execute(
                    text(f"""
                        UPDATE tbl_Big16
                        SET Song_FK = :canon_id
                        WHERE Song_FK IN ({placeholders})
                    """),
                    params
                )

                conn.execute(
                    text(f"""
                        DELETE FROM tbl_Song
                        WHERE ID IN ({placeholders})
                    """),
                    params
                )

            # --------------------------------
            # Song redirect
            # --------------------------------

            conn.execute(
                text("""
                    INSERT INTO tbl_RedirectSong
                    (
                        OldName,
                        Artist_FK,
                        Redirect_FK
                    )
                    VALUES
                    (
                        :song_name,
                        :artist_id,
                        :canon_id
                    )
                """),
                {
                    "song_name": song_name,
                    "artist_id": artist_id,
                    "canon_id": canon_id
                }
            )

            # --------------------------------
            # Album redirects
            # --------------------------------

            for album_name in album_names:

                conn.execute(
                    text("""
                        IF NOT EXISTS
                        (
                            SELECT 1
                            FROM tbl_RedirectAlbum
                            WHERE OldName = :album_name
                            AND SongName = :song_name
                            AND Artist_FK = :artist_id
                        )
                        BEGIN
                            INSERT INTO tbl_RedirectAlbum
                            (
                                OldName,
                                SongName,
                                Artist_FK,
                                Redirect_FK
                            )
                            VALUES
                            (
                                :album_name,
                                :song_name,
                                :artist_id,
                                :album_id
                            )
                        END
                    """),
                    {
                        "album_name": album_name,
                        "song_name": song_name,
                        "artist_id": artist_id,
                        "album_id": canon_album_id
                    }
                )

        return jsonify({"status": "ok"})

    except Exception as e:
        print("MERGE ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

#endregion

# ==============================
# SONG LIST
# ==============================
#region Song List

@app.route("/api/songlist")
def get_songlist():

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    params = {}
    date_filter = ""

    if start_date and end_date:

        date_filter = """
        WHERE s.DatetimePlayed >= :start_date
        AND s.DatetimePlayed < DATEADD(DAY, 1, :end_date)
        """

        params["start_date"] = start_date
        params["end_date"] = end_date

    elif start_date:

        date_filter = """
        WHERE s.DatetimePlayed >= :start_date
        """

        params["start_date"] = start_date

    elif end_date:

        date_filter = """
        WHERE s.DatetimePlayed < DATEADD(DAY, 1, :end_date)
        """

        params["end_date"] = end_date

    query = f"""
    SELECT
        so.ID AS songId,
        so.SongName AS name,
        a.ID AS artistId,
        a.ArtistName AS artist,
        al.ID AS albumId,
        al.AlbumName AS album,
        MIN(s.DatetimePlayed) AS first_played,
        MAX(s.DatetimePlayed) AS last_played,
        COUNT(*) AS value
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON s.Song_FK = so.ID
    JOIN tbl_Artist a ON so.Artist_FK = a.ID
    LEFT JOIN tbl_Album al ON so.Album_FK = al.ID
    {date_filter}
    GROUP BY
        so.ID,
        so.SongName,
        a.ID,
        a.ArtistName,
        al.ID,
        al.AlbumName
    ORDER BY value DESC
    """

    df = run_query(query, params=params)

    results = []

    for _, row in df.iterrows():

        results.append({
            "song_id": int(row["songId"]),
            "name": str(row["name"]),
            "artist_id": int(row["artistId"]),
            "artist": str(row["artist"]),
            "album_id": (
                int(row["albumId"])
                if pd.notna(row["albumId"])
                else ""
            ),
            "album": (
                str(row["album"])
                if pd.notna(row["album"])
                else ""
            ),
            "first_played": (
                row["first_played"].isoformat()
                if pd.notna(row["first_played"])
                else ""
            ),
            "last_played": (
                row["last_played"].isoformat()
                if pd.notna(row["last_played"])
                else ""
            ),
            "value": int(row["value"])
        })

    return jsonify(results)

#endregion

# ==============================
# SHEETS CUP
# ==============================
#region Sheets Cup

# This route fetches Sheets Cup data to display on its page.
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

    df = run_query(query)

    return jsonify(df.to_dict(orient="records"))

#endregion

# ==============================
# BIG 16
# ==============================
#region Big 16

# This route fetches Big 16 data to display on its page.
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
    
    df = run_query(query)

    return jsonify(df.to_dict(orient="records"))

@app.route("/api/big16/candidates")
def big16_candidates():

    year = int(request.args["year"])
    month = int(request.args["month"])

    query = """
    SELECT
        s.ID AS songId,
        s.SongName AS song,
        a.ID AS artistId,
        a.ArtistName AS artist,
        al.ID AS albumId,
        al.AlbumName AS album,
        COUNT(*) AS plays
    FROM tbl_Scrobble sc
    JOIN tbl_Song s ON sc.Song_FK = s.ID
    JOIN tbl_Artist a ON s.Artist_FK = a.ID
    JOIN tbl_Album al ON s.Album_FK = al.ID
    WHERE YEAR(sc.DatetimePlayed) = :year
    AND MONTH(sc.DatetimePlayed) = :month
    GROUP BY
        s.ID,
        s.SongName,
        a.ID,
        a.ArtistName,
        al.ID,
        al.AlbumName
    ORDER BY plays DESC
    """

    df = run_query(
        query,
        {
            "year": year,
            "month": month
        }
    )

    return jsonify(df.to_dict("records"))

@app.route("/api/big16/save", methods=["POST"])
def save_big16():

    data = request.json

    year = data["year"]
    month = data["month"]
    songs = data["songs"]

    with engine.begin() as conn:

        month_date = f"{year}-{month:02d}-01"

        row = conn.execute(
            text("""
                SELECT ID
                FROM tbl_Month
                WHERE Year = :year
                AND Month = :month
            """),
            {
                "year": year,
                "month": month
            }
        ).fetchone()

        if row:
            month_id = row.ID

            conn.execute(
                text("""
                    DELETE FROM tbl_Big16
                    WHERE Month_FK = :month_id
                """),
                {"month_id": month_id}
            )

        else:

            month_id = conn.execute(
                text("""
                    INSERT INTO tbl_Month
                    (
                        MonthDate,
                        Year,
                        Month
                    )
                    OUTPUT INSERTED.ID
                    VALUES
                    (
                        :month_date,
                        :year,
                        :month
                    )
                """),
                {
                    "month_date": month_date,
                    "year": year,
                    "month": month
                }
            ).scalar_one()

        rows = [
            {
                "month_id": month_id,
                "song_id": s["song_id"],
                "rank": s["rank"],
                "points": 17 - s["rank"]
            }
            for s in songs
        ]

        conn.execute(
            text("""
                INSERT INTO tbl_Big16
                (
                    Month_FK,
                    Song_FK,
                    Rank,
                    Points
                )
                VALUES
                (
                    :month_id,
                    :song_id,
                    :rank,
                    :points
                )
            """),
            rows
        )

    return {"status": "ok"}

#endregion

# ==============================
# SGV
# ==============================
#region SGV

# This function builds the ratings .
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

    df = run_query(query)

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

# This function updates the ratings of all songs based on statistics at time of sync.
@app.route("/api/sgv-update-ratings", methods=["POST"])
def sgv_update_ratings():
    try:
        df = build_song_ratings()

        # ----------------------------
        # Prepare rows
        # ----------------------------
        rows = [
            (
                # snapshot_id goes later
                safe_int(row.ID),
                safe_int(row.rating),
                safe_int(row.TotalPoints),
                safe_int(row.FirstPlaces),
                safe_int(row.Appearances),
                safe_int(row.TotalScrobbles),
                safe_int(row.DecayedScrobbles),
                safe_float(row.base_rating),
                safe_float(row.legacy_n),
                safe_float(row.recency_n)
            )
            for row in df.itertuples(index=False)
        ]

        # ----------------------------
        # Queries
        # ----------------------------
        insert_snapshot_sql = """
        INSERT INTO tbl_SGVSnapshot
        OUTPUT INSERTED.ID
        DEFAULT VALUES
        """

        insert_songs_sql = """
        INSERT INTO tbl_SGVSongs
        (
            Snapshot_FK,
            Song_FK,
            Rating,
            TP,
            N1s,
            MIC,
            Plays,
            DecayedPlays,
            BaseRating,
            LegacyScore,
            RecencyScore
        )
        VALUES
        (
            :snapshot_id,
            :song_id,
            :rating,
            :tp,
            :n1s,
            :mic,
            :plays,
            :decayed_plays,
            :base_rating,
            :legacy_score,
            :recency_score
        )
        """

        snapshot_id = run_snapshot_transaction(insert_snapshot_sql, insert_songs_sql, rows)

        return jsonify({"status": "success", "snapshot_id": snapshot_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# This function fetches the latest rating snapshot for all SGV songs.
@app.route("/api/sgv-get-ratings")
def get_latest_ratings():
    query = """
    SET NOCOUNT ON;

    DECLARE @LatestID INT;
    DECLARE @EarliestID INT;

    SELECT @LatestID = MAX(ID)
    FROM tbl_SGVSnapshot;

    SELECT @EarliestID = (
        SELECT TOP 1 ID
        FROM tbl_SGVSnapshot
        WHERE CreatedAt >= DATEADD(DAY, -43, GETDATE())
        ORDER BY CreatedAt ASC
    );

    SELECT 
        s.ID AS SongID,
        s.SongName,
        a.ID AS ArtistID,
        a.ArtistName,

        cur.Rating,
        cur.TP,
        cur.N1s,
        cur.MIC,
        cur.Plays,
        cur.DecayedPlays,

        prev.Rating AS PreviousRating,

        (cur.Rating - ISNULL(prev.Rating, cur.Rating)) AS RatingDiff

    FROM tbl_SGVSongs cur

    LEFT JOIN tbl_SGVSongs prev
        ON prev.Snapshot_FK = @EarliestID
        AND prev.Song_FK = cur.Song_FK

    JOIN tbl_Song s 
        ON s.ID = cur.Song_FK

    JOIN tbl_Artist a 
        ON a.ID = s.Artist_FK

    WHERE cur.Snapshot_FK = @LatestID

    ORDER BY cur.Rating DESC;
    """
    
    df = run_query(query)

    df = df.replace([float("inf"), float("-inf")], None)
    df = df.where(df.notnull(), None)

    return df.to_json(orient="records")

#endregion

# ==============================
# ARTIST PAGES
# ==============================
#region Artist Pages

# This function runs when the page is loaded and fetches ALL the
# data needed to display on the page.
@app.route("/api/artist/<int:artist_id>")
def get_artist(artist_id):

    cached = get_cached_artist(artist_id)
    if cached:
        return jsonify(cached)

    songs_query = """
    SET NOCOUNT ON;
    SELECT 
        s.ID,
        s.SongName,
        r.Rating,
        r.Plays,
        r.TP,
        r.N1s,
        r.MIC
    FROM tbl_Song s
    LEFT JOIN tbl_SGVSongs r 
        ON r.Song_FK = s.ID
    WHERE s.Artist_FK = :artist_id
    AND r.Snapshot_FK = (
        SELECT MAX(ID) FROM tbl_SGVSnapshot
    )
    ORDER BY r.Rating DESC
    """

    monthly_query = """
        WITH MonthlyPlays AS (
            SELECT 
                YEAR(s.DatetimePlayed) AS yr,
                MONTH(s.DatetimePlayed) AS mn,
                so.Artist_FK,
                COUNT(*) AS Plays
            FROM tbl_Scrobble s
            JOIN tbl_Song so ON so.ID = s.Song_FK
            GROUP BY 
                YEAR(s.DatetimePlayed),
                MONTH(s.DatetimePlayed),
                so.Artist_FK
        ),

        -- Rank artists per month
        MonthlyRanks AS (
            SELECT
                yr,
                mn,
                Artist_FK,
                Plays,
                RANK() OVER (
                    PARTITION BY yr, mn
                    ORDER BY Plays DESC
                ) AS PlaysRank
            FROM MonthlyPlays
        ),

        -- Top song per artist per month
        TopSongs AS (
            SELECT *
            FROM (
                SELECT 
                    YEAR(s.DatetimePlayed) AS yr,
                    MONTH(s.DatetimePlayed) AS mn,
                    so.Artist_FK,
                    so.ID AS SongID,
                    so.SongName,
                    COUNT(*) AS SongPlays,
                    ROW_NUMBER() OVER (
                        PARTITION BY YEAR(s.DatetimePlayed), MONTH(s.DatetimePlayed), so.Artist_FK
                        ORDER BY COUNT(*) DESC
                    ) AS rn
                FROM tbl_Scrobble s
                JOIN tbl_Song so ON so.ID = s.Song_FK
                GROUP BY 
                    YEAR(s.DatetimePlayed),
                    MONTH(s.DatetimePlayed),
                    so.Artist_FK,
                    so.ID,
                    so.SongName
            ) t
            WHERE rn = 1
        ),

        -- Big16 songs per artist per month
        Big16Agg AS (
            SELECT 
                m.Year AS yr,
                m.Month AS mn,
                so.Artist_FK,
                COUNT(*) AS Top16Count,
                STRING_AGG(
                    CAST(so.ID AS VARCHAR(20)) + '|' +
                    ISNULL(so.SongName, '') + '|' +
                    CAST(b.Rank AS VARCHAR(10)),
                    ';;'
                ) WITHIN GROUP (ORDER BY b.Rank ASC) AS Top16Songs
            FROM tbl_Big16 b
            JOIN tbl_Song so ON so.ID = b.Song_FK
            JOIN tbl_Month m ON m.ID = b.Month_FK
            GROUP BY 
                m.Year,
                m.Month,
                so.Artist_FK
        )

        SELECT 
            m.Year,
            m.Month,

            ISNULL(r.PlaysRank, NULL) AS PlaysRank,
            ISNULL(r.Plays, 0) AS Plays,

            ts.SongID AS TopSongID,
            ts.SongName AS TopSong,
            ts.SongPlays AS TopSongPlays,

            ISNULL(b.Top16Count, 0) AS Top16Count,
            ISNULL(b.Top16Songs, '') AS Top16Songs

        FROM tbl_Month m

        LEFT JOIN MonthlyRanks r
            ON r.yr = m.Year 
            AND r.mn = m.Month
            AND r.Artist_FK = :artist_id1

        LEFT JOIN TopSongs ts
            ON ts.yr = m.Year 
            AND ts.mn = m.Month
            AND ts.Artist_FK = :artist_id2

        LEFT JOIN Big16Agg b
            ON b.yr = m.Year 
            AND b.mn = m.Month
            AND b.Artist_FK = :artist_id3

        ORDER BY m.Year, m.Month
        """

    summary_query = """
        SET NOCOUNT ON;
        -- First scrobble (discovery)
        WITH FirstPlay AS (
            SELECT 
                so.Artist_FK,
                MIN(s.DatetimePlayed) AS FirstPlayed
            FROM tbl_Scrobble s
            JOIN tbl_Song so ON so.ID = s.Song_FK
            GROUP BY so.Artist_FK
        ),

        -- First big 16 month (discovery)
        FirstBig16 AS (
            SELECT 
                so.Artist_FK,
                MIN(m.MonthDate) AS FirstBig16Month
            FROM tbl_Big16 b
            JOIN tbl_Song so ON so.ID = b.Song_FK
            JOIN tbl_Month m ON m.ID = b.Month_FK
            GROUP BY so.Artist_FK
        ),

        -- Total plays per artist
        ArtistPlays AS (
            SELECT 
                so.Artist_FK,
                COUNT(*) AS TotalPlays
            FROM tbl_Scrobble s
            JOIN tbl_Song so ON so.ID = s.Song_FK
            GROUP BY so.Artist_FK
        ),

        -- Rank artists by plays
        PlayRanks AS (
            SELECT *,
                RANK() OVER (ORDER BY TotalPlays DESC) AS PlaysRank
            FROM ArtistPlays
        ),

        -- Big16 points per artist
        Big16Points AS (
            SELECT 
                so.Artist_FK,
                SUM(b.Points) AS TotalPoints
            FROM tbl_Big16 b
            JOIN tbl_Song so ON so.ID = b.Song_FK
            GROUP BY so.Artist_FK
        ),

        -- Rank by points
        PointRanks AS (
            SELECT *,
                RANK() OVER (ORDER BY TotalPoints DESC) AS PointsRank
            FROM Big16Points
        ),

        -- #1 songs + months
        Big16Wins AS (
            SELECT 
                so.Artist_FK,
                so.ID AS SongID,
                so.SongName,
                STRING_AGG(
                    FORMAT(m.MonthDate, 'MMM yyyy'),
                    ', '
                ) WITHIN GROUP (ORDER BY m.MonthDate ASC) AS WinMonths
            FROM tbl_Big16 b
            JOIN tbl_Song so ON so.ID = b.Song_FK
            JOIN tbl_Month m ON m.ID = b.Month_FK
            WHERE b.Rank = 1
            GROUP BY so.Artist_FK, so.ID, so.SongName
        ),

        Big16WinCounts AS (
            SELECT 
                so.Artist_FK,
                COUNT(*) AS WinCount
            FROM tbl_Big16 b
            JOIN tbl_Song so ON so.ID = b.Song_FK
            WHERE b.Rank = 1
            GROUP BY so.Artist_FK
        ),

        Big16WinRanks AS (
            SELECT *,
                RANK() OVER (ORDER BY WinCount DESC) AS WinRank
            FROM Big16WinCounts
        ),

        MonthlyArtistPlays AS (
            SELECT 
                YEAR(s.DatetimePlayed) AS yr,
                MONTH(s.DatetimePlayed) AS mn,
                so.Artist_FK,
                COUNT(*) AS Plays
            FROM tbl_Scrobble s
            JOIN tbl_Song so ON so.ID = s.Song_FK
            GROUP BY YEAR(s.DatetimePlayed), MONTH(s.DatetimePlayed), so.Artist_FK
        ),

        MonthlyLeaders AS (
            SELECT *
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY yr, mn
                        ORDER BY Plays DESC
                    ) AS rn
                FROM MonthlyArtistPlays
            ) x
            WHERE rn = 1
        ),

        MonthlyLeaderStats AS (
            SELECT 
                Artist_FK,
                COUNT(*) AS LeaderCount,
                MAX(Plays) AS BestMonthPlays,
                MAX(DATEFROMPARTS(yr, mn, 1)) AS BestMonthDate
            FROM MonthlyLeaders
            GROUP BY Artist_FK
        ),

        AggregatedWins AS (
            SELECT 
                Artist_FK,
                STRING_AGG(
                    CAST(SongID AS VARCHAR) + '|' +
                    SongName + '|' +
                    WinMonths,
                    ';;'
                ) AS Wins
            FROM Big16Wins
            GROUP BY Artist_FK
        )

        SELECT 
            a.ArtistName,
            fp.FirstPlayed,
            fb.FirstBig16Month,
            pr.TotalPlays,
            pr.PlaysRank,
            pt.TotalPoints,
            pt.PointsRank,
            bw.WinCount,
            bw.WinRank,
            ml.LeaderCount,
            ml.BestMonthPlays,
            ml.BestMonthDate,
            aw.Wins

        FROM tbl_Artist a

        LEFT JOIN FirstPlay fp ON fp.Artist_FK = a.ID
        LEFT JOIN FirstBig16 fb ON fb.Artist_FK = a.ID
        LEFT JOIN PlayRanks pr ON pr.Artist_FK = a.ID
        LEFT JOIN PointRanks pt ON pt.Artist_FK = a.ID
        LEFT JOIN Big16Wins w ON w.Artist_FK = a.ID
        LEFT JOIN Big16WinRanks bw ON bw.Artist_FK = a.ID
        LEFT JOIN MonthlyLeaderStats ml ON ml.Artist_FK = a.ID
        LEFT JOIN AggregatedWins aw ON aw.Artist_FK = a.ID

        WHERE a.ID = :artist_id

        GROUP BY 
            a.ArtistName,
            fp.FirstPlayed,
            fb.FirstBig16Month,
            pr.TotalPlays,
            pr.PlaysRank,
            pt.TotalPoints,
            pt.PointsRank,
            bw.WinCount,
            bw.WinRank,
            ml.LeaderCount,
            ml.BestMonthPlays,
            ml.BestMonthDate,
            aw.Wins
        """

    # Runs all SQL queries and returns in dfs.
    songs_df, monthly_df, summary_df = run_multi(
    [songs_query, monthly_query, summary_query],
        [
            {"artist_id": artist_id},
            {
                "artist_id1": artist_id,
                "artist_id2": artist_id,
                "artist_id3": artist_id
            },
            {"artist_id": artist_id}
        ]
    )

    # If artist is empty, don't bother!
    if summary_df.empty:
        return jsonify({"error": "Artist not found"}), 404

    # Replace NAs
    songs_df, monthly_df, summary_df = replace_na(songs_df), replace_na(monthly_df), replace_na(summary_df)

    response = {
        "songs": songs_df.to_dict("records"),
        "monthly": monthly_df.to_dict("records"),
        "summary": summary_df.to_dict("records")
    }

    set_cached_artist(artist_id, response)

    return jsonify(response)

#endregion

# ==============================
# SONG PAGES
# ==============================
#region Song Pages

# This function runs when the page is loaded and fetches ALL the
# data needed to display on the page.
@app.route("/api/song/<int:song_id>")
def get_song(song_id):
    
    cached = get_cached_song(song_id)
    if cached:
        return jsonify(cached)

    song_query = """
    SET NOCOUNT ON;
    SELECT 
        s.ID,
        s.SongName,
        a.ID AS ArtistID,
        a.ArtistName,
        al.ID AS AlbumID,
        al.AlbumName
    FROM tbl_Song s
    LEFT JOIN tbl_Artist a ON a.ID = s.Artist_FK
    LEFT JOIN tbl_Album Al ON Al.ID = S.Album_FK
    WHERE s.ID = :song_id1
    """

    summary_query = """
    SET NOCOUNT ON;

    WITH Plays AS (
        SELECT COUNT(*) AS Plays
        FROM tbl_Scrobble
        WHERE Song_FK = :song_id2
    ),

    Points AS (
        SELECT 
            SUM(Points) AS TPs,
            COUNT(CASE WHEN Rank = 1 THEN 1 END) AS N1s
        FROM tbl_Big16
        WHERE Song_FK = :song_id3
    ),

    Rating AS (
        SELECT TOP 1 *
        FROM tbl_SGVSongs
        WHERE Song_FK = ?
        ORDER BY Snapshot_FK DESC
    )

    SELECT 
        p.Plays,
        pt.TPs,
        pt.N1s,
        r.Rating,
        r.MIC,
        r.DecayedPlays
    FROM Plays p
    CROSS JOIN Points pt
    LEFT JOIN Rating r ON 1=1
    """

    monthly_query = """
    SET NOCOUNT ON;

    WITH MonthlyPlays AS (
        SELECT 
            YEAR(DatetimePlayed) AS yr,
            MONTH(DatetimePlayed) AS mn,
            COUNT(*) AS Plays
        FROM tbl_Scrobble
        WHERE Song_FK = :song_id1
        GROUP BY YEAR(DatetimePlayed), MONTH(DatetimePlayed)
    ),

    RankedSongs AS (
        SELECT 
            YEAR(s.DatetimePlayed) AS yr,
            MONTH(s.DatetimePlayed) AS mn,
            s.Song_FK,
            COUNT(*) AS Plays,
            RANK() OVER (
                PARTITION BY YEAR(s.DatetimePlayed), MONTH(s.DatetimePlayed)
                ORDER BY COUNT(*) DESC
            ) AS PlaysRank
        FROM tbl_Scrobble s
        GROUP BY 
            YEAR(s.DatetimePlayed), 
            MONTH(s.DatetimePlayed), 
            s.Song_FK
    ),

    MonthlyRanks AS (
        SELECT *
        FROM RankedSongs
        WHERE Song_FK = :song_id2
    ),

    Big16 AS (
        SELECT 
            m.Year AS yr,
            m.Month AS mn,
            b.Rank AS Big16Rank
        FROM tbl_Big16 b
        JOIN tbl_Month m ON m.ID = b.Month_FK
        WHERE b.Song_FK = :song_id3
    )

    SELECT 
        m.Year,
        m.Month,
        mp.Plays,
        mr.PlaysRank,
        b.Big16Rank,
        CASE 
            WHEN Big16Rank = 1 THEN 1
            ELSE 0
        END AS IsN1

    FROM tbl_Month m
    LEFT JOIN MonthlyPlays mp 
        ON mp.yr = m.Year AND mp.mn = m.Month
    LEFT JOIN MonthlyRanks mr 
        ON mr.yr = m.Year AND mr.mn = m.Month
    LEFT JOIN Big16 b
        ON b.yr = m.Year AND b.mn = m.Month
    ORDER BY m.Year, m.Month
    """

    # Run SQL queries and store in df
    song_df, summary_df, monthly_df = run_multi(
        [song_query, summary_query, monthly_query],
        [
            {"song_id": song_id},
            {"song_id1": song_id, "song_id2": song_id, "song_id3": song_id},
            {"song_id1": song_id, "song_id2": song_id, "song_id3": song_id}
        ]
    )

    # Check if there are results
    if song_df.empty:
        return jsonify({"error": "Song not found"}), 404

    # Replace NAs
    song_df, monthly_df, summary_df = replace_na(song_df), replace_na(monthly_df), replace_na(summary_df)

    # Convert to dictionary
    song = song_df.iloc[0].to_dict()
    summary = summary_df.iloc[0].to_dict() if not summary_df.empty else {}

    response = {
        "song": song,
        "summary": summary,
        "monthly": monthly_df.to_dict("records")
    }

    set_cached_song(song_id, response)

    return jsonify(response)

#endregion

# ==============================
# SYNC
# ==============================
#region Sync

@app.route('/run-fetch', methods=['POST'])
def run_fetch():
    try:
        sync()
        sgv_update_ratings()
        return {"success": True}

    except Exception as e:
        print(e)
        return {"success": False, "error": str(e)}

# This function updates tbl_Day and tbl_Month
def update_daily_stats():
    try:
        queries = [

            # ----------------------------
            # 1. Insert missing months
            # ----------------------------
            ("""
            INSERT INTO tbl_Month (MonthDate, Year, Month)
            SELECT MonthDate, Year, Month
            FROM (
                SELECT DISTINCT
                    DATEFROMPARTS(YEAR(s.DatetimePlayed), MONTH(s.DatetimePlayed), 1) AS MonthDate,
                    YEAR(s.DatetimePlayed) AS Year,
                    MONTH(s.DatetimePlayed) AS Month
                FROM tbl_Scrobble s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM tbl_Month m
                    WHERE m.Year = YEAR(s.DatetimePlayed)
                    AND m.Month = MONTH(s.DatetimePlayed)
                )
            ) x
            """, None),

            # ----------------------------
            # 2. Clear tbl_Day
            # ----------------------------
            ("DELETE FROM tbl_Day;", None),

            # ----------------------------
            # 3. Insert all days
            # ----------------------------
            ("""
            ;WITH AllDays AS (
                SELECT CAST('2020-12-03' AS DATE) AS DayDate
                UNION ALL
                SELECT DATEADD(DAY, 1, DayDate)
                FROM AllDays
                WHERE DayDate < CAST(GETDATE() AS DATE)
            )
            INSERT INTO tbl_Day (DayDate)
            SELECT DayDate
            FROM AllDays
            OPTION (MAXRECURSION 0);
            """, None),

            # ----------------------------
            # 4. Update total plays
            # ----------------------------
            ("""
            UPDATE d
            SET d.NumPlays = s.PlayCount
            FROM tbl_Day d
            JOIN (
                SELECT CAST(DatetimePlayed AS DATE) AS DayDate, COUNT(*) AS PlayCount
                FROM tbl_Scrobble
                GROUP BY CAST(DatetimePlayed AS DATE)
            ) s ON d.DayDate = s.DayDate;
            """, None),

            # ----------------------------
            # 5. Update top song
            # ----------------------------
            ("""
            ;WITH SongRank AS (
                SELECT 
                    CAST(s.DatetimePlayed AS DATE) AS DayDate,
                    so.ID,
                    COUNT(*) AS Plays,
                    ROW_NUMBER() OVER (
                        PARTITION BY CAST(s.DatetimePlayed AS DATE)
                        ORDER BY COUNT(*) DESC
                    ) AS rn
                FROM tbl_Scrobble s
                JOIN tbl_Song so ON s.Song_FK = so.ID
                GROUP BY CAST(s.DatetimePlayed AS DATE), so.ID
            )
            UPDATE d
            SET d.TopSong_FK = sr.ID,
                d.TopSongPlays = sr.Plays
            FROM tbl_Day d
            JOIN SongRank sr 
                ON d.DayDate = sr.DayDate 
                AND sr.rn = 1;
            """, None),

            # ----------------------------
            # 6. Update top artist
            # ----------------------------
            ("""
            ;WITH ArtistRank AS (
                SELECT 
                    CAST(s.DatetimePlayed AS DATE) AS DayDate,
                    a.ID,
                    COUNT(*) AS Plays,
                    ROW_NUMBER() OVER (
                        PARTITION BY CAST(s.DatetimePlayed AS DATE)
                        ORDER BY COUNT(*) DESC
                    ) AS rn
                FROM tbl_Scrobble s
                JOIN tbl_Song so ON s.Song_FK = so.ID
                JOIN tbl_Artist a ON so.Artist_FK = a.ID
                GROUP BY CAST(s.DatetimePlayed AS DATE), a.ID
            )
            UPDATE d
            SET d.TopArtist_FK = ar.ID,
                d.TopArtistPlays = ar.Plays
            FROM tbl_Day d
            JOIN ArtistRank ar 
                ON d.DayDate = ar.DayDate 
                AND ar.rn = 1;
            """, None),
        ]

        run_transaction(queries)

        print("✅ Daily stats + months updated successfully.")

    except Exception as e:
        print("❌ Error updating daily stats:", e)

#endregion

# ==============================
# NOW PLAYING BANNER
# ==============================
#region Now Playing Banner

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
        with engine.begin() as conn:
            res = requests.get(BASE_URL, params=params, timeout=5)
            data = res.json()

            track = data.get("recenttracks", {}).get("track", [])
            if not track:
                return {"playing": False}

            track = track[0]

            # Check if currently playing
            if "@attr" in track and track["@attr"].get("nowplaying"):

                try:
                    artist_name, album_name, song_name = apply_name_fixes(conn, track.get("artist", {}).get("#text"), track.get("album", {}).get("#text"), track.get("name"))

                    artist_id = 0
                    song_id = 0

                    row = conn.execute(
                        text("""
                            SELECT ID
                            FROM tbl_Artist
                            WHERE ArtistName = :name
                        """),
                        {"name": artist_name}
                        ).fetchone()
                        
                    if row:
                        artist_id = row.ID

                    row1 = conn.execute(
                        text("""
                            SELECT TOP 1 ID
                            FROM tbl_Song
                            WHERE Artist_FK = :artist_id
                            AND SongName = :name
                        """),
                        {"artist_id": artist_id, "name": song_name}
                        ).fetchone()

                    if row1:
                        song_id = row1.ID
                except Exception as e:
                    print("Now playing error:", e)
                
                return {
                    "playing": True,
                    "song_id": song_id,
                    "song": song_name,
                    "artist_id": artist_id,
                    "artist": artist_name,
                    "album": album_name
                }

            return {"playing": False}

    except Exception as e:
        print("Now playing error:", e)
        return {"playing": False}

#endregion

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    app.run(debug=True)