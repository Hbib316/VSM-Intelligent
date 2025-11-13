# >VSM Intelligent - Plateforme d'Optimisation Lean Manufacturing

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![Scikit-learn](https://img.shields.io/badge/ML-Scikit--learn-orange.svg)

**Application web intelligente de Value Stream Mapping (VSM) avec Machine Learning pour l'optimisation des processus de production.**


## 🎯 Vue d'ensemble

VSM Intelligent est une plateforme d'analyse **Value Stream Mapping** nouvelle génération qui combine :

-  **Modélisation de processus** avec gestion de dépendances
-  **Machine Learning** pour prédire goulots d'étranglement
-  **Visualisations temps réel** (graphiques interactifs)
-  **Chatbot intelligent** avec mémoire et base de connaissances Lean
-  **Analyse historique** et comparaisons de performances

### Problème Résolu

Dans l'industrie , **identifier les goulots d'étranglement** coûte du temps et de l'argent. Cette application :

- Réduit le **lead time** de 15-25%
- Augmente le **VA ratio** de 10-15 points
- Détecte automatiquement les **étapes critiques**
- Propose des **recommandations Lean** personnalisées

---

## ✨ Fonctionnalités

### 🏭 Modélisation de Processus

- **Interface drag & drop** pour créer des étapes
- **Gestion de dépendances** (séquentielles/parallèles)
- **Calcul automatique** des temps d'attente par tri topologique
- Support des attributs : cycle time, coût, valeur ajoutée (VA/NVA)

### 🤖 Intelligence Artificielle

| Modèle | Fonction | Algorithme |
|--------|----------|------------|
| **Régression** | Prédire wait_time anormaux | Random Forest Regressor |
| **Classification** | Détecter étapes critiques | Random Forest Classifier |
| **Features** | cycle_time, cost, value_added, dependencies | - |

### 📊 Analyse & KPIs

- **Lead Time** total du processus
- **VA Ratio** (% temps à valeur ajoutée)
- **Temps d'attente** cumulés
- **Coût total** par processus
- **Alertes ML** (goulots prédits)

### 💬 Chatbot Intelligent

Nouveau : Chatbot avec **mémoire SQLite** et base de connaissances !

**Capacités :**
- 📈 Analyse de tendances historiques (30 jours)
- 🔍 Identification goulots récurrents
- 💰 Suivi évolution des coûts
- 📚 Base de connaissances Lean (Kanban, SMED, 5S, Poka-Yoke, etc.)
- 🎯 Recommandations personnalisées

**Exemples de questions :**
```
User: "Montre-moi l'historique"
Bot: 📊 12 analyses effectuées | Lead time moyen: 18.5h | Tendance: amélioration 📈

User: "Quel est mon goulot ?"
Bot: 🚨 Étape "Soudure" identifiée 5x | Actions: SMED, vérifier capacité...

User: "C'est quoi le takt time ?"
Bot: ⏱️ Takt Time = Temps Dispo / Demande Client | [Calculateur interactif]
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│            Frontend (Vanilla JS)                │
│  - Interface builder étapes                     │
│  - Chart.js visualisations                      │
│  - Chatbot UI                                   │
└─────────────┬───────────────────────────────────┘
              │ REST API
┌─────────────▼───────────────────────────────────┐
│          Backend Flask (Python)                 │
│  ┌─────────────────────────────────────────┐   │
│  │ VSMAnalyzer                             │   │
│  │  - Tri topologique dépendances          │   │
│  │  - Calcul lead time/VA ratio            │   │
│  └─────────────────┬───────────────────────┘   │
│                    │                             │
│  ┌─────────────────▼───────────────────────┐   │
│  │ MLAnalyzer (Scikit-learn)               │   │
│  │  - RandomForestRegressor (wait_time)    │   │
│  │  - RandomForestClassifier (critical)    │   │
│  └─────────────────┬───────────────────────┘   │
│                    │                             │
│  ┌─────────────────▼───────────────────────┐   │
│  │ VSMChatbot (SQLite)                     │   │
│  │  - Historique analyses                  │   │
│  │  - Base connaissances Lean              │   │
│  │  - Recommandations intelligentes        │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│         Base de Données SQLite                  │
│  - analyses (historique VSM)                    │
│  - step_history (tendances étapes)              │
│  - knowledge_base (termes Lean)                 │
└─────────────────────────────────────────────────┘
```


## 📖 Utilisation

### 1. Créer un Processus

1. Cliquez sur **"+ Ajouter Étape"**
2. Remplissez les champs :
   - **Nom** : ex. "Soudure châssis"
   - **Cycle Time** : temps opératoire (heures)
   - **Coût** : coût de l'étape ($)
   - **VA** : cochez si valeur ajoutée
   - **Dépendances** : étapes préalables (séparées par virgules)

**Exemple :**
```
Étape 1: Découpe (cycle: 2h, coût: 500$, VA: ✓, deps: -)
Étape 2: Soudure (cycle: 4h, coût: 1200$, VA: ✓, deps: Découpe)
Étape 3: Contrôle (cycle: 1h, coût: 300$, VA: ✗, deps: Soudure)
Étape 4: Peinture (cycle: 3h, coût: 800$, VA: ✓, deps: Contrôle)
```

### 2. Analyser

Cliquez sur **"📊 Analyser le Processus VSM"**

**Résultats obtenus :**
- Lead time planifié (avec dépendances)
- VA ratio calculé
- Graphique wait_time vs cycle_time
- Alertes ML (goulots prédits)
- Rapport avec recommandations

### 3. Interagir avec le Chatbot

**Questions utiles :**
```
"Montre-moi l'historique"
"Quel est mon goulot ?"
"Compare avec le passé"
"Analyse des coûts"
"C'est quoi le kanban ?"
"Calcule le takt time"
```

---


## 🛠️ Technologies

### Backend
- **Flask** 2.3+ : Framework web Python
- **Scikit-learn** 1.3+ : Machine Learning (Random Forest)
- **Pandas** : Manipulation de données
- **SQLite3** : Base de données embarquée

### Frontend
- **Vanilla JavaScript** (ES6+)
- **Chart.js** 4.0+ : Visualisations interactives
- **CSS3** : Gradients, animations

### Algorithmes
- **Tri Topologique** (Kahn's algorithm) : Ordonnancement dépendances
- **Random Forest Regressor** : Prédiction wait_time
- **Random Forest Classifier** : Détection étapes critiques

---

