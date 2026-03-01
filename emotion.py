from transformers import pipeline
import google.generativeai as genai

# Load the HuggingFace emotion detection model
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base"
)

# Configure Gemini
genai.configure(api_key="AIzaSyAWvwRRKd7Fd3btdz1yqyVidqS_mJwcXvQ")
gemini = genai.GenerativeModel("gemini-2.0-flash")

def detect_emotion(text):
    result = emotion_classifier(text)
    emotion = result[0]["label"]
    return emotion

def get_gemini_tag(text, emotion):
    prompt = f"""
    The user said: "{text}"
    The detected emotion is: {emotion}

    Based on the user's specific context and emotion, return ONE Last.fm music tag
    that best describes the music they need right now.

    Rules:
    - Return ONLY the tag, nothing else (e.g. "lo-fi" or "sad indie" or "workout")
    - The tag must be a real Last.fm music tag
    - Be specific to the user's context, not just the emotion
    - Examples: "study", "heartbreak", "workout", "rainy day", "party", "lo-fi"
    """
    response = gemini.generate_content(prompt)
    return response.text.strip()

def get_emotion_data(text):
    emotion = detect_emotion(text)
    tag = get_gemini_tag(text, emotion)

    return {
        "emotion": emotion,
        "tag": tag
    }

if __name__ == "__main__":
    test = get_emotion_data("I feel anxious about my exam tomorrow")
    print(test)
