from flask import Flask, render_template, request, jsonify
import pyodbc
import pandas as pd
import subprocess
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

            # Find Artist Name
            cur.execute("""
                SELECT ArtistName FROM tbl_Artist
                WHERE ID = ?
                """, artist_id)
            artist_context = cur.fetchone()[0]

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

                # Delete the old song row
                cur.execute("""
                    DELETE FROM tbl_Song
                    WHERE ID = ?
                """, (song_id,))

                # Save mapping in NameFixes
                cur.execute("""
                    INSERT INTO tbl_NameFixes (Type, OldName, NewName, ArtistContext)
                    VALUES ('song', ?, ?, ?)
                """, (old_name, new_name, artist_context))
            else:
                # Safe to update
                cur.execute("""
                    UPDATE tbl_Song
                    SET SongName = ?
                    WHERE ID = ?
                """, new_name, song_id)

                # ✅ Save mapping
                cur.execute("""
                    INSERT INTO tbl_NameFixes (Type, OldName, NewName, ArtistContext)
                    VALUES ('song', ?, ?, ?)
                """, (old_name, new_name, artist_context))

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
                INSERT INTO tbl_NameFixes (Type, OldName, NewName, ArtistContext)
                VALUES ('artist', ?, ?, NULL)
            """, old_name, new_name)

        conn.commit()
        return {"status": "ok"}

    except Exception as e:
        print("❌ APPLY FIX ERROR:", e)
        conn.rollback()
        return {"status": "error", "message": str(e)}

# ==============================
# SONG LIST
# ==============================

@app.route("/songlist_page")
def songlist_page():
    return render_template("songlist.html")

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
# RUN
# ==============================

if __name__ == "__main__":
    app.run(debug=True)