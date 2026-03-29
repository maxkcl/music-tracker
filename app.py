from flask import Flask, render_template, request, jsonify
import pyodbc
import pandas as pd
from db import get_connection

app = Flask(__name__)

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

@app.route("/api/query-builder", methods=["POST"])
def query_builder():
    from flask import request, jsonify

    data = request.json

    select = data.get("select")
    metric = data.get("metric")
    operator = data.get("operator")
    value = data.get("value")

    # =========================
    # SELECT FIELD MAPPING
    # =========================

    if select == "artist":
        select_sql = "a.ArtistName"
        image_sql = "a.ImageURL"
        group_sql = "GROUP BY a.ArtistName, a.ImageURL"

    elif select == "album":
        select_sql = "al.AlbumName"
        image_sql = "al.ImageURL"
        group_sql = "GROUP BY al.AlbumName, al.ImageURL"

    elif select == "song":
        select_sql = "so.SongName"
        image_sql = "al.ImageURL"
        group_sql = "GROUP BY so.SongName, al.ImageURL"

    elif select == "day":
        select_sql = "CAST(DatetimePlayed AS DATE)"
        group_sql = "GROUP BY CAST(DatetimePlayed AS DATE)"

    elif select == "month":
        select_sql = "FORMAT(DatetimePlayed, 'yyyy-MM')"
        group_sql = "GROUP BY FORMAT(DatetimePlayed, 'yyyy-MM')"

    elif select == "year":
        select_sql = "YEAR(DatetimePlayed)"
        group_sql = "GROUP BY YEAR(DatetimePlayed)"

    else:
        return jsonify({"error": "Invalid select"}), 400

    # =========================
    # METRIC MAPPING
    # =========================

    if metric == "plays":
        metric_sql = "COUNT(*)"

    elif metric == "songs":
        metric_sql = "COUNT(DISTINCT so.ID)"

    elif metric == "albums":
        metric_sql = "COUNT(DISTINCT al.ID)"

    else:
        return jsonify({"error": "Invalid metric"}), 400

    # =========================
    # FINAL QUERY
    # =========================

    query = f"""
    SELECT {select_sql} AS label, {image_sql} AS ImageURL, {metric_sql} AS value
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON s.Song_FK = so.ID
    JOIN tbl_Artist a ON so.Artist_FK = a.ID
    LEFT JOIN tbl_Album al ON so.Album_FK = al.ID
    {group_sql}
    HAVING {metric_sql} {operator} ?
    ORDER BY value DESC
    """

    df = pd.read_sql(query, conn, params=[value])
    return df.to_json(orient="records")

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

            # Check for duplicate (case-sensitive, excluding self)
            cur.execute("""
                SELECT 1 FROM tbl_Song
                WHERE SongName COLLATE Latin1_General_CS_AS = ?
                AND Artist_FK = ?
                AND ID != ?
            """, new_name, artist_id, song_id)

            if cur.fetchone():
                return {"status": "error", "message": "Song with that name already exists"}

            # Safe to update
            cur.execute("""
                UPDATE tbl_Song
                SET SongName = ?
                WHERE ID = ?
            """, new_name, song_id)

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
                INSERT INTO tbl_NameFixes (Type, OldName, NewName)
                VALUES ('artist', ?, ?)
            """, old_name, new_name)

        conn.commit()
        return {"status": "ok"}

    except Exception as e:
        print("❌ APPLY FIX ERROR:", e)
        conn.rollback()
        return {"status": "error", "message": str(e)}

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    app.run(debug=True)