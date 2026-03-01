from transformers import pipeline
from google import genai
import requests

# Load the HuggingFace emotion detection model
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base"
)

# Configure Gemini
client = genai.Client(api_key="AIzaSyA2F8n4_Ne-ENQ2VHi8Vxr26--aRPJI60o")

LASTFM_API_KEY = "1be977045d82a3b04f3e89d6ddfbf356"
LASTFM_BASE_URL = "http://ws.audioscrobbler.com/2.0/"

def fetch_lastfm_top_tags():
    # Step 1: Fetch top 100 tags from Last.fm
    response = requests.get(LASTFM_BASE_URL, params={
        "method": "chart.gettoptags",
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": 100
    })
    data = response.json()
    tags = data.get("tags", {}).get("tag", [])
    all_tags = [t["name"].lower() for t in tags]

    # Step 2: Ask Gemini to filter out meta-tags
    prompt = f"""
    From this list of Last.fm tags, return ONLY the ones that are genuine
    music genres or moods (e.g. rock, happy, sad, ambient, jazz, electronic).

    Remove any personal bookmark or meta tags like "favorites", "seen live",
    "awesome", "loved", "to listen", "beautiful", "owned", etc.

    Tags: {", ".join(all_tags)}

    Return ONLY a comma-separated list of the valid music tags, nothing else.
    """
    filter_response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    filtered = [t.strip().lower() for t in filter_response.text.split(",")]

    # Only keep tags that were in the original Last.fm list
    filtered = [t for t in filtered if t in all_tags]
    return filtered

# Fetch and filter tags once at startup
print("Fetching and filtering tags from Last.fm...")
VALID_TAGS = fetch_lastfm_top_tags()
print(f"Loaded {len(VALID_TAGS)} music tags: {VALID_TAGS}")

def detect_emotion(text):
    result = emotion_classifier(text)
    emotion = result[0]["label"]
    return emotion

def get_gemini_tag(text, emotion):
    prompt = f"""
    The user said: "{text}"
    The detected emotion is: {emotion}

    Choose the ONE most fitting tag from this exact list:
    {", ".join(VALID_TAGS)}

    Rules:
    - Return ONLY the tag exactly as written in the list above, nothing else
    - Pick the tag that best matches the user's specific context and emotion
    - Do not invent new tags, only use tags from the list
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    tag = response.text.strip().lower()
    # Safety fallback in case Gemini still returns something invalid
    if tag not in VALID_TAGS:
        tag = "happy" if emotion == "joy" else "sad" if emotion == "sadness" else "rock"
    return tag

def get_emotion_data(text):
    emotion = detect_emotion(text)
    tag = get_gemini_tag(text, emotion)

    return {
        "emotion": emotion,
        "tag": tag
    }

if __name__ == "__main__":
    test = get_emotion_data("I'm pumped for the gym")
    print(test)
