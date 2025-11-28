import os
import io
import uuid
from itertools import cycle
from flask import Flask, request, send_file, jsonify
from PIL import Image
import requests

app = Flask(__name__)

REMOVE_BG_KEYS = [os.getenv(f"REMOVE_BG_KEY_{i}") for i in range(1, 21)]
REMOVE_BG_KEYS = [k for k in REMOVE_BG_KEYS if k]
key_cycle = cycle(REMOVE_BG_KEYS)
REMOVE_BG_API_URL = "https://api.remove.bg/v1.0/removebg"

STATIC_FOLDER = os.path.join(os.path.dirname(__file__), "static")
BACKGROUND_PATH = os.path.join(STATIC_FOLDER, "custom_background.jpg")
os.makedirs(STATIC_FOLDER, exist_ok=True)

def remove_background(image_bytes):
    for _ in range(len(REMOVE_BG_KEYS)):
        api_key = next(key_cycle)
        try:
            response = requests.post(
                REMOVE_BG_API_URL,
                files={"image_file": ("image.png", image_bytes, "image/png")},
                data={"size": "auto"},
                headers={"X-Api-Key": api_key},
                timeout=15
            )
            if response.status_code == 200:
                return io.BytesIO(response.content)
            elif response.status_code == 402:
                continue
            else:
                raise Exception(f"Remove.bg API error: {response.status_code} {response.text}")
        except requests.RequestException:
            continue
    raise Exception("All API keys exhausted or failed.")

def blend_with_background(fg_bytes):
    fg_image = Image.open(fg_bytes).convert("RGBA")
    if os.path.exists(BACKGROUND_PATH):
        bg_image = Image.open(BACKGROUND_PATH).convert("RGBA").resize(fg_image.size)
        combined = Image.alpha_composite(bg_image, fg_image)
        final = combined.convert("RGB")
    else:
        final = fg_image.convert("RGB")
    out_bytes = io.BytesIO()
    final.save(out_bytes, format="JPEG")
    out_bytes.seek(0)
    return out_bytes

@app.route("/api/process", methods=["POST"])
def process_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    try:
        img_bytes = io.BytesIO(file.read())
        removed_bg_bytes = remove_background(img_bytes)
        final_bytes = blend_with_background(removed_bg_bytes)
        return send_file(final_bytes, mimetype="image/jpeg", as_attachment=True,
                         download_name=f"glider-{uuid.uuid4().hex}.jpg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/hello")
def hello():
    return jsonify({"message": "API is live ✅"}), 200

if __name__ == "__main__":
    app.run(debug=True)
