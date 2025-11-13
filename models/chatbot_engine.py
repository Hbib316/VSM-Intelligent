# models/chatbot_engine.py
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import re
from flask import Flask, request, jsonify  # add jsonify here
class VSMChatbot:
    """Chatbot intelligent avec mémoire et analyse d'historique"""
    
    def __init__(self, db_path="vsm_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Créer les tables pour l'historique et la connaissance"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Table des analyses passées
        c.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_name TEXT,
                lead_time REAL,
                va_ratio REAL,
                total_cost REAL,
                nb_steps INTEGER,
                bottleneck_step TEXT,
                alerts_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table des étapes historiques (pour tendances)
        c.execute('''
            CREATE TABLE IF NOT EXISTS step_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER,
                step_name TEXT,
                cycle_time REAL,
                wait_time REAL,
                cost REAL,
                value_added BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (analysis_id) REFERENCES analyses(id)
            )
        ''')
        
        # Base de connaissances VSM/Lean
        c.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE,
                response TEXT,
                category TEXT
            )
        ''')
        
        # Pré-remplir la base de connaissances
        knowledge = [
            ("takt time", 
             "Le Takt Time = Temps disponible / Demande client. C'est le rythme auquel vous devez produire pour satisfaire la demande. Voulez-vous calculer le vôtre ?",
             "lean"),
            ("kanban",
             "Kanban = système visuel de gestion de flux. Limite le WIP (Work In Progress). Idéal pour réduire les stocks tampons détectés dans votre VSM.",
             "lean"),
            ("smed",
             "SMED (Single Minute Exchange of Die) = réduire temps de changement série < 10 min. Applicable sur vos étapes avec temps setup élevés.",
             "lean"),
            ("5s",
             "5S = Seiri, Seiton, Seiso, Seiketsu, Shitsuke. Méthode d'organisation pour réduire gaspillages. Recommandé sur postes à faible VA ratio.",
             "lean"),
            ("poka yoke",
             "Poka-Yoke = dispositif anti-erreur. Évite défauts à la source. À implémenter sur étapes critiques de votre processus.",
             "qualité"),
            ("oee",
             "OEE (Overall Equipment Effectiveness) = Disponibilité × Performance × Qualité. Mesurez-le sur vos goulots d'étranglement.",
             "kpi"),
            ("jit",
             "Just-In-Time = produire ce qui est nécessaire, quand c'est nécessaire. Réduit stocks. Nécessite VSM optimisé.",
             "lean")
        ]
        
        for kw, resp, cat in knowledge:
            c.execute('INSERT OR IGNORE INTO knowledge_base (keyword, response, category) VALUES (?, ?, ?)',
                     (kw, resp, cat))
        
        conn.commit()
        conn.close()
    
    def save_analysis(self, analysis_data: Dict[str, Any]):
        """Sauvegarder une analyse pour historique"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        summary = analysis_data.get('summary', {})
        alerts = analysis_data.get('alerts', [])
        
        # Identifier le goulot (étape avec plus grand wait_time ou pred_wait)
        steps = analysis_data.get('steps', [])
        bottleneck = max(steps, key=lambda s: s.get('wait_time', 0)) if steps else None
        bottleneck_name = bottleneck['name'] if bottleneck else None
        
        c.execute('''
            INSERT INTO analyses 
            (process_name, lead_time, va_ratio, total_cost, nb_steps, bottleneck_step, alerts_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            summary.get('process'),
            summary.get('lead_time'),
            summary.get('va_ratio'),
            sum(s.get('cost', 0) for s in steps),
            len(steps),
            bottleneck_name,
            json.dumps(alerts)
        ))
        
        analysis_id = c.lastrowid
        
        # Sauvegarder chaque étape
        for step in steps:
            c.execute('''
                INSERT INTO step_history 
                (analysis_id, step_name, cycle_time, wait_time, cost, value_added)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                analysis_id,
                step.get('name'),
                step.get('cycle_time'),
                step.get('wait_time'),
                step.get('cost'),
                step.get('value_added')
            ))
        
        conn.commit()
        conn.close()
        
        return analysis_id
    
    def get_response(self, user_message: str) -> str:
        """Générer une réponse intelligente basée sur contexte"""
        msg_lower = user_message.lower()
        
        # 1. Recherche dans la base de connaissances
        knowledge_response = self._search_knowledge(msg_lower)
        if knowledge_response:
            return knowledge_response
        
        # 2. Requêtes sur l'historique
        if any(word in msg_lower for word in ['historique', 'passé', 'tendance', 'évolution']):
            return self._get_history_insights()
        
        if any(word in msg_lower for word in ['meilleur', 'pire', 'comparaison']):
            return self._get_comparison()
        
        if 'goulot' in msg_lower or 'bottleneck' in msg_lower:
            return self._get_bottleneck_analysis()
        
        if 'coût' in msg_lower or 'économie' in msg_lower:
            return self._get_cost_analysis()
        
        if 'amélioration' in msg_lower or 'recommandation' in msg_lower:
            return self._get_recommendations()
        
        # 3. Questions calculatoires
        if 'takt' in msg_lower and ('calculer' in msg_lower or 'calcul' in msg_lower):
            return self._help_takt_calculation()
        
        # 4. Réponse par défaut enrichie
        return self._default_response()
    
    def _search_knowledge(self, query: str) -> str:
        """Chercher dans la base de connaissances"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT keyword, response FROM knowledge_base')
        for keyword, response in c.fetchall():
            if keyword in query:
                conn.close()
                return f"💡 {response}"
        
        conn.close()
        return None
    
    def _get_history_insights(self) -> str:
        """Analyser les tendances historiques"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT 
                COUNT(*) as nb_analyses,
                AVG(lead_time) as avg_lead,
                AVG(va_ratio) as avg_va,
                MIN(lead_time) as best_lead,
                MAX(lead_time) as worst_lead
            FROM analyses
            WHERE timestamp >= datetime('now', '-30 days')
        ''')
        
        row = c.fetchone()
        conn.close()
        
        if not row or row[0] == 0:
            return "📊 Aucun historique disponible. Lancez quelques analyses pour voir les tendances !"
        
        nb, avg_lead, avg_va, best, worst = row
        
        trend = "amélioration 📈" if best < avg_lead * 0.8 else "stable 📊"
        
        return f"""📊 **Analyse Historique (30 derniers jours)**
        
• {nb} analyses effectuées
• Lead time moyen: {avg_lead:.1f}h
• VA ratio moyen: {avg_va:.1f}%
• Meilleure performance: {best:.1f}h
• Performance actuelle: {worst:.1f}h
• Tendance: {trend}

💡 Recommandation: {"Continuez sur cette lancée !" if trend == "amélioration 📈" else "Analysez les étapes NVA récurrentes."}"""
    
    def _get_comparison(self) -> str:
        """Comparer l'analyse actuelle avec historique"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Dernière analyse
        c.execute('''
            SELECT lead_time, va_ratio, bottleneck_step 
            FROM analyses 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        current = c.fetchone()
        
        # Moyenne historique
        c.execute('''
            SELECT AVG(lead_time), AVG(va_ratio)
            FROM analyses
            WHERE id < (SELECT MAX(id) FROM analyses)
        ''')
        avg = c.fetchone()
        conn.close()
        
        if not current or not avg[0]:
            return "❌ Pas assez de données pour comparaison. Effectuez plus d'analyses."
        
        lead_diff = ((current[0] - avg[0]) / avg[0]) * 100
        va_diff = current[1] - avg[1]
        
        status = "✅ Meilleure" if lead_diff < 0 else "⚠️ Moins bonne"
        
        return f"""📊 **Comparaison avec Historique**

{status} que la moyenne !

• Lead time actuel: {current[0]:.1f}h ({lead_diff:+.1f}% vs moyenne)
• VA ratio actuel: {current[1]:.1f}% ({va_diff:+.1f}pts vs moyenne)
• Goulot actuel: {current[2] or "Non identifié"}

💡 {"Excellent travail d'optimisation !" if lead_diff < -10 else "Focalisez sur la réduction des temps NVA."}"""
    
    def _get_bottleneck_analysis(self) -> str:
        """Analyser les goulots récurrents"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT bottleneck_step, COUNT(*) as occurrences
            FROM analyses
            WHERE bottleneck_step IS NOT NULL
            GROUP BY bottleneck_step
            ORDER BY occurrences DESC
            LIMIT 3
        ''')
        
        bottlenecks = c.fetchall()
        conn.close()
        
        if not bottlenecks:
            return "✅ Aucun goulot identifié dans l'historique !"
        
        response = "🚨 **Goulots d'Étranglement Récurrents**\n\n"
        for step, count in bottlenecks:
            response += f"• {step}: {count}x identifié comme goulot\n"
        
        response += f"\n💡 Actions recommandées sur '{bottlenecks[0][0]}':\n"
        response += "1. Analyse SMED pour réduire temps setup\n"
        response += "2. Vérifier capacité machine/opérateur\n"
        response += "3. Envisager parallélisation ou buffer stratégique"
        
        return response
    
    def _get_cost_analysis(self) -> str:
        """Analyser l'évolution des coûts"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT 
                DATE(timestamp) as date,
                SUM(total_cost) as daily_cost
            FROM analyses
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        ''')
        
        costs = c.fetchall()
        conn.close()
        
        if not costs:
            return "💰 Aucune donnée de coût disponible."
        
        response = "💰 **Analyse Coûts (7 derniers jours)**\n\n"
        total = sum(c[1] for c in costs)
        avg = total / len(costs)
        
        for date, cost in costs:
            response += f"• {date}: ${cost:,.0f}\n"
        
        response += f"\n📊 Coût moyen/jour: ${avg:,.0f}"
        response += f"\n💡 Potentiel d'économie (10% VA): ${avg*0.1:,.0f}/jour"
        
        return response
    
    def _get_recommendations(self) -> str:
        """Recommandations personnalisées basées sur l'historique"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Dernière analyse
        c.execute('''
            SELECT va_ratio, lead_time, alerts_json
            FROM analyses
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            return "❌ Effectuez une analyse d'abord pour recevoir des recommandations."
        
        va_ratio, lead_time, alerts_json = row
        alerts = json.loads(alerts_json)
        
        recommendations = ["🎯 **Recommandations Personnalisées**\n"]
        
        if va_ratio < 30:
            recommendations.append("⚠️ URGENT: VA ratio très faible (<30%)")
            recommendations.append("→ Éliminer activités NVA (transport, attente, stocks)")
            recommendations.append("→ Appliquer méthode 5S sur postes critiques")
        
        if lead_time > 20:
            recommendations.append("\n⏱️ Lead time élevé détecté")
            recommendations.append("→ Réduire lots de production (flux tiré)")
            recommendations.append("→ Implémenter Kanban entre étapes")
        
        if len(alerts) > 3:
            recommendations.append("\n🚨 Nombreuses alertes ML")
            recommendations.append("→ Audit approfondi des étapes critiques")
            recommendations.append("→ Formation opérateurs sur standard work")
        
        recommendations.append("\n📚 Méthodes Lean applicables:")
        recommendations.append("• VSM futur state (vision cible)")
        recommendations.append("• Kaizen quotidien (amélioration continue)")
        recommendations.append("• PDCA sur goulots identifiés")
        
        return "\n".join(recommendations)
    
    def _help_takt_calculation(self) -> str:
        """Aider au calcul du Takt Time"""
        return """⏱️ **Calculateur Takt Time**

Formule: Takt Time = Temps Disponible / Demande Client

Exemple:
• Temps dispo: 8h/jour × 60min = 480 min
• Demande: 240 véhicules/jour
• **Takt Time = 480 / 240 = 2 min/véhicule**

Votre processus doit produire 1 véhicule toutes les 2 minutes !

💡 Comparez ce Takt avec vos cycle times VSM. Si cycle > Takt = goulot garanti."""
    
    def _default_response(self) -> str:
        """Réponse par défaut avec suggestions"""
        return """🤖 **Je peux vous aider avec:**

📊 **Analyses:**
• "Montre-moi l'historique" - Tendances 30 derniers jours
• "Quel est mon goulot ?" - Analyse bottlenecks
• "Compare avec le passé" - Performance relative

💡 **Connaissances Lean:**
• Demandez sur: takt time, kanban, SMED, 5S, Poka-Yoke, OEE, JIT

💰 **Coûts:**
• "Analyse des coûts" - Évolution et économies potentielles

🎯 **Recommandations:**
• "Que dois-je améliorer ?" - Conseils personnalisés

Posez votre question ! 🚀"""


# Intégration dans app.py
def create_enhanced_chatbot_endpoint(app, analyzer):
    """Ajouter endpoint chatbot enrichi à Flask app"""
    chatbot = VSMChatbot()
    
    @app.route("/api/chat_enhanced", methods=["POST"])
    def chat_enhanced():
        data = request.get_json() or {}
        msg = data.get("message", "")
        
        if not msg:
            return jsonify({"response": "Envoyez un message non vide."})
        
        # Sauvegarder dernière analyse si fournie
        if "last_analysis" in data:
            chatbot.save_analysis(data["last_analysis"])
        
        response = chatbot.get_response(msg)
        return jsonify({"response": response})
    
    return chatbot