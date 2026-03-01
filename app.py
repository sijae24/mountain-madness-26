from flask import Flask, request, jsonify
from spotify import get_recommendations
from emotion import get_emotion_data

app = Flask(__name__)


@app.route('/')
def home():
    return jsonify({"message": "Music recommendation API is running"})


@app.route('/emotion', methods=['POST'])
def emotion():
    """
    Detect emotion from text.
    Body: { "text": "I feel great today" }
    Returns: { "emotion": "joy", "tag": "happy" }
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field in request body"}), 400

    result = get_emotion_data(data["text"])
    return jsonify(result)


@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Get song recommendations based on text input.
    Body: { "text": "I'm pumped for the gym" }
    Returns: { "emotion": "joy", "tracks": [...] }
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field in request body"}), 400

    result = get_recommendations(data["text"])
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
