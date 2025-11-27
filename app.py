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

    import time
    t0 = time.time()
    
    # Detect language unless overridden
    if lang_override:
        detected_lang, confidence = (lang_override, 1.0)
    else:
        detected_lang, confidence = spell_service.detect_language(text)
    
    t1 = time.time()

    # Determine cross-check languages
    cross_check_langs = []
    if detected_lang != "en":
        cross_check_langs.append("en")
    elif detected_lang == "en":
        # Suggest German if input is English, as requested by user scenario
        cross_check_langs.append("de")

    result = spell_service.process_text(text, mode=mode, lang=detected_lang, cross_check_langs=cross_check_langs)
    t2 = time.time()
    
    print(f"PERF: Total={(t2-t0)*1000:.1f}ms | Detect={(t1-t0)*1000:.1f}ms | Process={(t2-t1)*1000:.1f}ms | TextLen={len(text)}")
    
    return jsonify({
        "detected_lang": detected_lang,
        "confidence": confidence,
        "mode": mode,
        "tokens": result["tokens"]
    })

@app.route('/last_update')
def last_update():
    """Returns the maximum modification time of tracked files for auto-reload."""
    import os
    files_to_watch = [
        __file__,
        os.path.join(os.path.dirname(__file__), 'templates', 'index.html'),
        os.path.join(os.path.dirname(__file__), 'static', 'css', 'style.css'),
        os.path.join(os.path.dirname(__file__), 'static', 'js', 'main.js'),
        os.path.join(os.path.dirname(__file__), 'services', 'spell_service.py')
    ]
    
    max_mtime = 0
    for f in files_to_watch:
        if os.path.exists(f):
            max_mtime = max(max_mtime, os.path.getmtime(f))
            
    return jsonify({"timestamp": max_mtime})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
