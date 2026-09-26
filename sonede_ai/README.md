# SONEDE AI Backend — Classification de réclamations (catégorie + urgence)

Petit service Flask + scikit-learn qui prend un texte de réclamation (français,
arabe, tunisien en caractères latins ou arabes — mélangés ou non) et prédit :

- **catégorie** (coupure, fuite, qualité de l'eau, pression, facturation, ...)
- **urgence** (faible / moyenne / haute / critique)

Utilisé pour :
1. Auto-classifier les réclamations soumises en texte libre côté app mobile.
2. Alimenter le chatbot en intention détectée (au lieu des mots-clés côté Flutter).

## Installation

```bash
cd sonede_ai
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## Entraîner le modèle (première fois, ou après avoir accumulé du feedback)

```bash
python train_model.py
```

Cela lit `data/sonede_complaints_dataset.csv` (+ `data/feedback_log.csv` si des
corrections vérifiées existent), entraîne les modèles, et sauvegarde tout dans
`model/`. Un rapport d'évaluation est écrit dans `model/evaluation_report.txt`.

## Lancer l'API

```bash
python app.py
```

Le serveur démarre sur `http://localhost:5000` (ou l'IP de votre machine sur
le réseau local, utile pour tester depuis un téléphone / émulateur).

## Endpoints

### `GET /health`
Vérifie que l'API tourne et liste les classes connues.

### `POST /predict`
```json
{ "texte": "Deuxième coupure cette semaine sans préavis" }
```
Réponse :
```json
{
  "categorie": "coupure_non_signalee",
  "categorie_confidence": 0.42,
  "urgence": "haute",
  "urgence_confidence": 0.51,
  "toutes_categories": { "...": "probabilité de chaque catégorie" }
}
```

### `POST /feedback`
Enregistre une correction humaine (par ex. un agent SONEDE qui corrige une
mauvaise prédiction). **N'affecte pas le modèle immédiatement** — voir
"Comment fonctionne l'auto-apprentissage" ci-dessous.
```json
{
  "texte": "...",
  "categorie_corrigee": "fuite_visible",
  "urgence_corrigee": "haute",
  "verified": true
}
```

### `POST /retrain`
Relance l'entraînement (dataset + feedback vérifié) et recharge les modèles
en mémoire sans redémarrer le serveur.

## Comment fonctionne "l'auto-apprentissage" (et ses limites)

Vous avez demandé un modèle qui "auto-apprend". Il faut être transparent sur
ce que ça veut dire concrètement ici, et pourquoi ce n'est **pas** un vrai
apprentissage en temps réel automatique :

- **Ce qui est fait** : chaque correction confirmée par un humain (`verified:
  true`) est stockée dans `data/feedback_log.csv`. Un appel à `/retrain` (ou
  `python train_model.py`) réentraîne le modèle sur dataset original + tout le
  feedback accumulé. Le modèle s'améliore donc progressivement au fil du
  temps, à intervalles que vous contrôlez (ex. une tâche planifiée chaque nuit,
  ou un bouton "Ré-entraîner" dans un futur back-office admin).

- **Ce qui n'est PAS fait, volontairement** : le modèle ne se met **pas** à
  jour tout seul à chaque message reçu. Un vrai "online learning" sans
  supervision humaine est risqué en production : n'importe qui pourrait
  soumettre des messages pour délibérément fausser les catégories/urgences
  (empoisonnement de données), et une seule requête malveillante ou une
  faute de frappe répétée pourrait dégrader tout le modèle. Le flux
  `/feedback` → validation humaine → `/retrain` est la manière standard et
  sûre de faire "évoluer" un modèle de ce type en production.

- **Limite de taille de dataset** : 320 exemples pour 10 catégories, c'est
  correct pour un prototype (F1 catégorie ≈ 0.98 sur ce jeu de test — les
  catégories ont un vocabulaire très distinct), mais l'urgence est plus
  subjective et obtient un score plus modeste (F1 ≈ 0.63). Plus vous
  accumulez de vrais signalements (via `/feedback`), plus la précision sur
  l'urgence s'améliorera avec le temps.

## Intégration avec l'app Flutter

Remplacez la logique de mots-clés dans `chatbot_engine.dart` par un appel HTTP
à `/predict`, par exemple avec le package `http` :

```dart
final response = await http.post(
  Uri.parse('http://VOTRE_IP:5000/predict'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({'texte': userMessage}),
);
final data = jsonDecode(response.body);
// data['categorie'], data['urgence'], data['categorie_confidence'], ...
```

Sur émulateur Android, `localhost` de votre PC correspond à `10.0.2.2`. Sur un
téléphone physique, utilisez l'IP locale de votre machine (ex. `192.168.1.x`)
et assurez-vous que le téléphone est sur le même réseau Wi-Fi.

Vous pouvez aussi utiliser directement `/predict` dans `new_complaint_screen.dart`
pour pré-remplir automatiquement la catégorie détectée avant que l'utilisateur
choisisse manuellement dans le menu déroulant.

## Structure du projet

```
sonede_ai/
├── app.py                      # API Flask
├── train_model.py              # Script d'entraînement
├── preprocessing.py            # Nettoyage de texte partagé (train + serve)
├── requirements.txt
├── data/
│   ├── sonede_complaints_dataset.csv
│   └── feedback_log.csv        # Corrections accumulées (vide au départ)
└── model/                      # Généré par train_model.py
    ├── vectorizer.joblib
    ├── category_model.joblib
    ├── urgency_model.joblib
    ├── category_encoder.joblib
    ├── metadata.json
    └── evaluation_report.txt
```
