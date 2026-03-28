from flask import Flask, render_template, jsonify
import pyodbc
import pandas as pd

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

# ==============================
# ROUTES
# ==============================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/query", methods=["POST"])
def run_query():
    from flask import request, jsonify

    data = request.json

    group_by = data.get("group_by")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    artist = data.get("artist")
    song = data.get("song")
    min_plays = data.get("min_plays", 0)
    sort_by = data.get("sort_by", "plays")

    where_clauses = ["DatetimePlayed BETWEEN ? AND ?"]
    params = [start_date, end_date]

    if artist:
        where_clauses.append("a.ArtistName LIKE ?")
        params.append(f"%{artist}%")

    if song:
        where_clauses.append("so.SongName LIKE ?")
        params.append(f"%{song}%")

    where_sql = " AND ".join(where_clauses)

    # =========================
    # SELECT + GROUPING
    # =========================

    if group_by == "artist":
        select_clause = "a.ArtistName AS label, COUNT(*) AS plays"
        group_clause = "GROUP BY a.ArtistName"

    elif group_by == "song":
        select_clause = "so.SongName AS label, COUNT(*) AS plays"
        group_clause = "GROUP BY so.SongName"

    elif group_by == "day":
        select_clause = "CAST(DatetimePlayed AS DATE) AS label, COUNT(*) AS plays"
        group_clause = "GROUP BY CAST(DatetimePlayed AS DATE)"

    else:
        return jsonify({"error": "Invalid group_by"}), 400

    query = f"""
    SELECT * FROM (
        SELECT {select_clause}
        FROM tbl_Scrobble s
        JOIN tbl_Song so ON s.Song_FK = so.ID
        JOIN tbl_Artist a ON so.Artist_FK = a.ID
        WHERE {where_sql}
        {group_clause}
    ) q
    WHERE plays >= ?
    ORDER BY {sort_by} DESC
    """

    params.append(min_plays)

    df = pd.read_sql(query, conn, params=params)
    return df.to_json(orient="records")

@app.route("/api/advanced")
def advanced_stats():
    query = """
    SELECT 
        COUNT(*) AS total_scrobbles,
        COUNT(DISTINCT Song_FK) AS unique_songs,
        COUNT(DISTINCT Artist_FK) AS unique_artists
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON s.Song_FK = so.ID
    """
    df = pd.read_sql(query, conn)
    return df.to_json(orient="records")

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
        group_sql = "GROUP BY a.ArtistName"

    elif select == "album":
        select_sql = "al.AlbumName"
        group_sql = "GROUP BY al.AlbumName"

    elif select == "song":
        select_sql = "so.SongName"
        group_sql = "GROUP BY so.SongName"

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
    SELECT {select_sql} AS label, {metric_sql} AS value
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

if __name__ == "__main__":
    app.run(debug=True)