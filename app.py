from flask import Flask, render_template, request, jsonify, abort
from services.spell_service import SpellCheckerService

app = Flask(__name__)
spell_service = SpellCheckerService()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/check", methods=["POST"])
def check_spelling():
    # Accept form data or JSON body for flexibility
    payload = request.form or (request.get_json(silent=True) or {})
    text = payload.get("text")
    mode = payload.get("mode") or "balanced"
    # optional lang override (e.g., "en", "es", ...)
    lang_override = payload.get("lang")

    if not text or not text.strip():
        return jsonify({"error": "No text provided"}), 400

    if len(text) > 10000:
        abort(413, description="Input too large")

    # Detect language unless overridden
    if lang_override:
        detected_lang, confidence = (lang_override, 1.0)
    else:
        detected_lang, confidence = spell_service.detect_language(text)

    # Determine cross-check languages
    cross_check_langs = []
    if detected_lang != "en":
        cross_check_langs.append("en")
    elif detected_lang == "en":
        # Suggest German if input is English, as requested by user scenario
        cross_check_langs.append("de")

    result = spell_service.process_text(text, mode=mode, lang=detected_lang, cross_check_langs=cross_check_langs)
    
    return jsonify({
        "detected_lang": detected_lang,
        "confidence": confidence,
        "mode": mode,
        "corrected_text": result["corrected_text"],
        "suggestions": result["suggestions"]
    })

if __name__ == "__main__":
    # Disable the auto-reloader on Windows to avoid repeated restarts
    # triggered by changes in site-packages (language servers, editors).
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
