import requests
import base64
import time
from db import get_connection

# ==============================
# CONFIG
# ==============================

SPOTIFY_CLIENT_ID = "ed8815fbf93b4b18b7b12e88906509b4"
SPOTIFY_CLIENT_SECRET = "2d831e9fb8b4419fbb302ffd2a9c1386"

# ==============================
# DB SETUP
# ==============================

conn, cur = get_connection()

# ==============================
# CACHE
# ==============================

spotify_cache = {}

# ==============================
# FUNCTIONS
# ==============================

def get_spotify_token():
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={"grant_type": "client_credentials"},
        timeout=10
    )

    data = response.json()

    if "access_token" not in data:
        raise Exception(f"Spotify auth failed: {data}")

    return data["access_token"]

def get_spotify_artist_image(artist_name, token):
    url = "https://api.spotify.com/v1/search"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "q": artist_name,
        "type": "artist",
        "limit": 1
    }

    res = requests.get(url, headers=headers, params=params, timeout=10)

    # Check for token expiration
    if res.status_code == 401:
        return "TOKEN_EXPIRED"

    # Handle rate limit
    if res.status_code == 429:
        retry_after = int(res.headers.get("Retry-After", 1))
        print(f"⏳ Rate limited. Sleeping {retry_after}s")
        time.sleep(retry_after)
        return None

    try:
        data = res.json()
    except:
        print(f"⚠️ Invalid JSON for {artist_name}")
        return None

    items = data.get("artists", {}).get("items", [])

    if items and items[0].get("images"):
        return items[0]["images"][0]["url"]

    return None

def backfill_artist_images():
    token = get_spotify_token()
    token_time = time.time()

    cur.execute("""
        SELECT ID, ArtistName
        FROM tbl_Artist
        WHERE ImageURL IS NULL
    """)

    artists = cur.fetchall()

    print(f"Found {len(artists)} artists to update")

    token = get_spotify_token()

    for i, (artist_id, name) in enumerate(artists, start=1):

        print(f"[{i}/{len(artists)}] Fetching: {name}")

        image = get_spotify_artist_image(name, token)

        # If token expired → refresh and retry
        if image == "TOKEN_EXPIRED":
            print("🔄 Token expired. Refreshing...")
            token = get_spotify_token()
            image = get_spotify_artist_image(name, token)

        if image:
            cur.execute("""
                UPDATE tbl_Artist
                SET ImageURL = ?
                WHERE ID = ?
            """, image, artist_id)

        if i % 50 == 0:
            conn.commit()

        time.sleep(0.1)  # avoid rate limits

    conn.commit()
    print("🎉 Artist image backfill complete")

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    backfill_artist_images()