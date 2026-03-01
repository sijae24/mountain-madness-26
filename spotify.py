import requests
import random
from emotion import get_emotion_data

LASTFM_API_KEY = "1be977045d82a3b04f3e89d6ddfbf356"
LASTFM_BASE_URL = "http://ws.audioscrobbler.com/2.0/"

def get_top_artists_for_tag(tag):
    # Fetch artists from a random page so results vary every run
    page = random.randint(1, 10)
    response = requests.get(LASTFM_BASE_URL, params={
        "method": "tag.gettopartists",
        "tag": tag,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "page": page,
        "limit": 20
    })
    data = response.json()
    artists = data.get("topartists", {}).get("artist", [])
    return [a["name"] for a in artists]

def get_top_track_for_artist(artist):
    # Get top track for a given artist
    response = requests.get(LASTFM_BASE_URL, params={
        "method": "artist.gettoptracks",
        "artist": artist,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": 5
    })
    data = response.json()
    tracks = data.get("toptracks", {}).get("track", [])
    if not tracks:
        return None
    # Pick a random track from top 5 for more variety
    track = random.choice(tracks)
    return {
        "name": track["name"],
        "artist": artist,
        "url": track["url"],
        "tag": track["tag"]
    }

def get_recommendations(text):
    # Step 1: Get emotion and tag from emotion.py
    emotion_data = get_emotion_data(text)
    emotion = emotion_data["emotion"]
    tag = emotion_data["tag"]

    # Step 2: Get pool of artists for this emotion tag
    artists = get_top_artists_for_tag(tag)
    if not artists:
        return {"emotion": emotion, "tracks": []}

    # Step 3: Pick 3 random different artists
    selected_artists = random.sample(artists, min(3, len(artists)))

    # Step 4: Get one track from each artist
    tracks = []
    for artist in selected_artists:
        track = get_top_track_for_artist(artist)
        if track:
            tracks.append(track)

    return {
        "emotion": emotion,
        "tracks": tracks
    }

if __name__ == "__main__":
    result = get_recommendations("I got full marks on my test")
    print("Detected emotion:", result["emotion"])
    print("\nRecommended songs:")
    for track in result["tracks"]:
        print(f"- {track['name']} by {track['artist']}")
        print(f"  {track['url']}")
        

