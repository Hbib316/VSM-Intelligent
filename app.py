from flask import Flask, render_template, request, jsonify, send_from_directory
import os, json
from models.vsm_analyzer import VSMAnalyzer
from models.chatbot_engine import VSMChatbot
from datetime import datetime

app = Flask(__name__, static_folder="static", template_folder="templates")

OUTPUT_FOLDER = "vsm_output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Instances
analyzer = VSMAnalyzer(enable_ai=True)
chatbot = VSMChatbot()  # ← NOUVEAU CHATBOT INTELLIGENT

@app.route("/")
def index():
    return render_template("index.html")

# Analyse complete du processus
@app.route("/api/analyze", methods=["POST"])
def analyze():
    payload = request.get_json()
    if not payload or "steps" not in payload:
        return jsonify({"error": "Aucune donnée d'étapes reçue"}), 400
    try:
        result = analyzer.analyze(payload)
        
        # ← NOUVEAU: Sauvegarder dans BDD pour historique chatbot
        chatbot.save_analysis(result)
        
        # sauvegarde pour preuve (optionnel)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = os.path.join(OUTPUT_FOLDER, f"vsm_{ts}.json")
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Analyse d'une étape seule
@app.route("/api/analyze_step", methods=["POST"])
def analyze_step():
    step = request.get_json()
    if not step:
        return jsonify({"error": "Aucune étape fournie"}), 400
    try:
        predicted = None
        if analyzer.ml:
            predicted = analyzer.ml.predict_wait_time(step)
        else:
            predicted = step.get("wait_time", 0)
        return jsonify({"step": step.get("name", "Étape"), "predicted_wait_time": predicted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ← NOUVEAU: Chatbot intelligent avec BDD
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    msg = data.get("message", "")
    
    if not msg:
        return jsonify({"response": "Envoyez un message non vide."})
    
    try:
        response = chatbot.get_response(msg)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"response": f"❌ Erreur: {str(e)}"})

# téléchargement de résultats
@app.route("/outputs/<path:filename>", methods=["GET"])
def outputs(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000)