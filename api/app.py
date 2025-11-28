import os
import uuid
import time
from io import BytesIO
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import requests
from itertools import cycle

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
STATIC_FOLDER = os.path.join(ROOT_DIR, "static")
BACKGROUND_PATH = os.path.join(STATIC_FOLDER, "custom_background.jpg")

REMOVE_BG_KEYS = [os.getenv(f"REMOVE_BG_KEY_{i}") for i in range(1, 21)]
REMOVE_BG_KEYS = [key for key in REMOVE_BG_KEYS if key]
key_cycle = cycle(REMOVE_BG_KEYS)
REMOVE_BG_API_URL = "https://api.remove.bg/v1.0/removebg"

def remove_background(file_storage):
    for _ in range(len(REMOVE_BG_KEYS)):
        current_key = next(key_cycle)
        try:
            file_storage.seek(0)
            response = requests.post(
                REMOVE_BG_API_URL,
                files={"image_file": (file_storage.filename, file_storage, file_storage.content_type)},
                data={"size": "auto"},
                headers={"X-Api-Key": current_key},
                timeout=20
            )
            if response.status_code == 200:
                return BytesIO(response.content)
            elif response.status_code == 402:
                continue
        except:
            continue
    raise Exception("All API keys exhausted or failed.")

def blend_with_background(fg_buf):
    fg = Image.open(fg_buf).convert("RGBA")
    bg = Image.open(BACKGROUND_PATH).convert("RGBA").resize(fg.size)
    combined = Image.alpha_composite(bg, fg)
    out_buf = BytesIO()
    combined.convert("RGB").save(out_buf, format="JPEG")
    out_buf.seek(0)
    return out_buf

@app.route("/api/process", methods=["POST"])
def process_image():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    if file.content_length and file.content_length > 2 * 1024 * 1024:
        return jsonify({"error": "Image must be under 2MB"}), 400

    try:
        removed_buf = remove_background(file)
        final_buf = blend_with_background(removed_buf)
        filename = f"{uuid.uuid4().hex}.jpg"
        return send_file(final_buf, mimetype="image/jpeg", download_name=filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/hello")
def hello():
    return jsonify({"message": "API is live ✅"}), 200

if __name__ == "__main__":
    app.run(debug=True)
