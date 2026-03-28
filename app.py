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

if __name__ == "__main__":
    app.run(debug=True)