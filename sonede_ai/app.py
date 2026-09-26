"""
API Flask pour le chatbot / classification automatique des réclamations SONEDE.

Endpoints :
    GET  /health               -> vérifie que l'API, les modèles et MongoDB sont OK
    POST /chat                 -> conversation guidée (langue -> localisation -> problème -> confirmation -> sauvegarde)
    GET  /complaints           -> liste des réclamations (écran "suivi des réclamations")
    GET  /complaints/<id>      -> détail d'une réclamation (écran "détail réclamation")
    POST /predict              -> {"texte": "..."} -> catégorie + urgence + confiances (usage direct / debug)
    POST /feedback             -> enregistre une correction humaine (pour ré-entraînement futur)
    POST /retrain              -> relance l'entraînement sur dataset + feedback vérifié, recharge les modèles
    POST /analyze_image        -> analyse une image via CLIP (base64) pour détecter un problème d'eau
    POST /label_unknown_word   -> log les mots inconnus pour étendre le dictionnaire

Lancer en local :
    python app.py

Variables d'environnement attendues : MONGO_URI, MONGO_DB_NAME (voir db.py).
"""
import csv
import os
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS

import classifier
import db
import dialogue_manager
import duplicate_checker
import vision_processor
from knowledge_base import rag
import learning

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEEDBACK_PATH = os.path.join(BASE_DIR, 'data', 'feedback_log.csv')
UNKNOWN_WORDS_PATH = os.path.join(BASE_DIR, 'data', 'unknown_words_log.csv')
AUTO_RETRAIN_THRESHOLD = 50

app = Flask(__name__)
CORS(app)  # autorise les appels depuis l'app Flutter (mobile / web) et Angular


def load_models():
    """Charge (ou recharge) les modèles ML, l'index FAQ, et prépare MongoDB."""
    classifier.load_models()
    n_faq = rag.build_index()
    try:
        vision_processor._load_model()
        print("[app] Vision (CLIP) préchargé.")
    except Exception as e:
        print(f"[app] Erreur chargement vision: {e}")
    try:
        import speech_to_text
        speech_to_text.load_model()
        print("[app] Speech-to-text préchargé.")
    except Exception as e:
        print(f"[app] Erreur chargement speech-to-text: {e}")
    duplicate_checker.reload()
    db.ensure_indexes()
    print(f'[app] Modèles chargés. Index FAQ : {n_faq} documents. Mongo prêt.')



@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok' if classifier.is_loaded() else 'models_not_loaded',
        'mongo': 'ok' if db.is_available() else 'unavailable',
        'categories': classifier.VALID_CATEGORIES,
        'urgences': classifier.VALID_URGENCIES,
    })


# ---------------------------------------------------------------------------
# Chat guidé (dialogue_manager)
# ---------------------------------------------------------------------------

@app.route('/chat', methods=['POST'])
def chat_route():
    """
    Body attendu :
    {
        "session_id": "..." (optionnel au 1er appel -- généré si absent),
        "message": "texte de l'utilisateur, dans n'importe quelle langue/derja",
        "image_base64": "..." (optionnel, pour l'analyse d'image),
        "audio_base64": "..." (optionnel, pour l'analyse vocale),
        "location": {"lat": 12.3, "lng": 45.6} (optionnel)
    }

    Réponse :
    {
        "session_id": "...",
        "reply": "message à afficher côté Flutter, dans la langue détectée",
        "state": "ASK_LOCATION" | "ASK_PROBLEM" | "CLARIFY_CATEGORY" |
                  "CONFIRM_DUPLICATE" | "CONFIRM_SUMMARY" | "DONE",
        "done": bool,
        "id_plainte": str | null   # rempli une fois la réclamation sauvegardée
    }
    """
    body = request.get_json(silent=True) or {}
    message = (body.get('message') or '').strip()
    session_id = body.get('session_id')
    user_id = body.get('user_id')
    image_base64 = body.get('image_base64')
    audio_base64 = body.get('audio_base64')
    location = body.get('location')

    # If audio is provided, transcribe it first
    if audio_base64:
        try:
            import speech_to_text
            transcribed = speech_to_text.transcribe(audio_base64)
            if transcribed:
                # Ignore the Flutter placeholder
                if not message or message == "🎤 Message vocal":
                    message = transcribed
                else:
                    message = f"{message} {transcribed}"
        except Exception as e:
            print(f"[app] Erreur pendant la transcription audio: {e}")

    if not message and not image_base64:
        return jsonify({'error': 'Le champ "message", "image_base64" ou "audio_base64" est requis.'}), 400

    if user_id and '@' in str(user_id):
        try:
            db_conn = db.get_db()
            email_clean = str(user_id).strip().lower()
            if not db_conn.users.find_one({'email': email_clean}):
                import re
                username = email_clean.split('@')[0]
                clean_name = re.sub(r'[\d_.]+', ' ', username).strip().title() or 'Citoyen SONEDE'
                db_conn.users.insert_one({
                    'fullName': clean_name,
                    'email': email_clean,
                    'role': 'CITIZEN',
                    'phone': '+216 20 000 000',
                    'governorate': 'Tunis',
                    'delegation': 'Centre',
                    'address': 'Tunisie',
                    'enabled': True,
                    'createdAt': datetime.now(timezone.utc),
                    'updatedAt': datetime.now(timezone.utc),
                })
        except Exception as e:
            print(f"[app] Erreur auto-sync citoyen: {e}")

    result = dialogue_manager.start_or_continue(
        session_id, message, image_base64=image_base64, location=location, user_id=user_id
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# Voice Assistant (Speech-to-Speech — dedicated accessibility endpoint)
# ---------------------------------------------------------------------------

@app.route('/voice_assistant', methods=['POST'])
def voice_assistant_route():
    """
    Dedicated endpoint for the voice assistant (Talkback) feature.
    Completely separate from /chat — designed for audio-only interaction.

    Body attendu :
    {
        "session_id": "..." (optionnel au 1er appel),
        "audio_base64": "..." (audio WAV encodé en base64),
        "user_id": "..." (optionnel, email de l'utilisateur)
    }

    Réponse :
    {
        "session_id": "...",
        "transcription": "ce que l'utilisateur a dit (texte)",
        "reply": "réponse textuelle du bot",
        "audio_base64": "...(réponse MP3 encodée en base64)...",
        "state": "...",
        "done": bool
    }
    """
    body = request.get_json(silent=True) or {}
    audio_base64 = body.get('audio_base64', '')
    session_id = body.get('session_id')
    user_id = body.get('user_id')

    if not audio_base64:
        return jsonify({'error': 'Le champ "audio_base64" est requis pour l\'assistant vocal.'}), 400

    # Step 1 — Speech-to-Text (transcribe audio)
    import speech_to_text
    transcription = ''
    try:
        transcription = speech_to_text.transcribe(audio_base64)
    except Exception as e:
        print(f"[voice_assistant] Erreur STT: {e}")

    if not transcription:
        import text_to_speech
        error_msg = "Désolé, je n'ai pas pu comprendre votre message vocal. Essayez de parler plus clairement."
        error_audio = text_to_speech.synthesize_to_base64(error_msg, "fr")
        return jsonify({
            'session_id': session_id or '',
            'transcription': '',
            'reply': error_msg,
            'audio_base64': error_audio,
            'state': 'CONVERSATION',
            'done': False,
        })

    # Step 2 — Dialogue Manager (process the transcribed text)
    result = dialogue_manager.start_or_continue(
        session_id, transcription, user_id=user_id, audio_only=True
    )

    reply_text = result.get('reply', '')
    result_session_id = result.get('session_id', session_id or '')

    # Step 3 — Determine language from the session
    session = db.get_session(result_session_id)
    lang = session.get('language', 'fr') if session else 'fr'

    # Step 4 — Text-to-Speech (synthesize response)
    import text_to_speech
    audio_response_b64 = ''
    if reply_text:
        try:
            audio_response_b64 = text_to_speech.synthesize_to_base64(reply_text, lang)
        except Exception as e:
            print(f"[voice_assistant] Erreur TTS: {e}")

    return jsonify({
        'session_id': result_session_id,
        'transcription': transcription,
        'reply': reply_text,
        'audio_base64': audio_response_b64,
        'state': result.get('state', ''),
        'done': result.get('done', False),
        'id_plainte': result.get('id_plainte'),
    })


# ---------------------------------------------------------------------------
# Réclamations (écrans détail / suivi côté Flutter, dashboard côté Angular)
# ---------------------------------------------------------------------------

@app.route('/complaints', methods=['GET'])
def list_complaints_route():
    """Filtres optionnels en query string : ?statut=nouveau&categorie=fuite_visible
    &gouvernorat=Sfax&delegation=Sfax%20Médina&limit=50"""
    filters = {}
    for field in ('statut', 'categorie', 'gouvernorat', 'delegation', 'user_email', 'technicien_email'):
        value = request.args.get(field)
        if value:
            filters[field] = value
    limit = int(request.args.get('limit', 50))

    complaints = db.list_complaints(filters=filters, limit=limit)
    return jsonify({'count': len(complaints), 'results': complaints})


@app.route('/complaints/<id_plainte>', methods=['GET'])
def get_complaint_route(id_plainte):
    complaint = db.get_complaint(id_plainte)
    if complaint is None:
        return jsonify({'error': f'Réclamation {id_plainte} introuvable.'}), 404
    return jsonify(complaint)


@app.route('/complaints/status', methods=['POST'])
def update_status_generic_route():
    """Generic status update endpoint called by status_manager.html and tech_dashboard.html."""
    body = request.get_json(silent=True) or {}
    id_plainte = body.get('id') or body.get('id_plainte') or body.get('complaint_id')
    new_status = body.get('status') or body.get('statut')
    if not id_plainte or not new_status:
        return jsonify({'error': 'id et statut requis'}), 400

    extra = {}
    for f in ('technicien_nom', 'technicien_email', 'technicien_tel'):
        if f in body:
            extra[f] = body[f]

    updated = db.update_complaint_status(id_plainte, new_status, extra)
    if not updated:
        return jsonify({'error': f'Réclamation {id_plainte} introuvable.'}), 404
    return jsonify({'status': 'ok', 'id': id_plainte, 'new_status': new_status})


@app.route('/complaints/assign', methods=['POST'])
def assign_technician_route():
    """Assign a technician to a complaint and update status to 'assignee'."""
    body = request.get_json(silent=True) or {}
    comp_id = body.get('complaint_id') or body.get('id')
    tech_email = body.get('technicien_email', '').strip()
    if not comp_id:
        return jsonify({'error': 'complaint_id requis'}), 400

    db_conn = db.get_db()
    extra_fields = {}
    new_status = 'assignee'

    if tech_email:
        tech = db_conn.users.find_one({'email': tech_email})
        if tech:
            extra_fields['technicien_email'] = tech_email
            extra_fields['technicien_nom'] = tech.get('fullName', tech_email)
            extra_fields['technicien_tel'] = tech.get('phone', '')
            extra_fields['technicien_gouv'] = tech.get('governorate', '')
        else:
            extra_fields['technicien_email'] = tech_email
    else:
        # Unassign
        extra_fields['technicien_email'] = None
        extra_fields['technicien_nom'] = None
        extra_fields['technicien_tel'] = None
        new_status = 'recue'

    updated = db.update_complaint_status(comp_id, new_status, extra_fields)
    return jsonify({'status': 'ok', 'complaint_id': comp_id, 'technicien_email': tech_email, 'new_status': new_status})


@app.route('/complaints/<id_plainte>/status', methods=['POST'])
def update_complaint_status_route(id_plainte):
    body = request.get_json(silent=True) or {}
    new_status = body.get('statut') or body.get('status')
    if not new_status:
        return jsonify({'error': 'statut requis'}), 400

    extra_fields = {}
    for field in ('technicien_nom', 'technicien_email', 'technicien_tel'):
        if field in body:
            extra_fields[field] = body[field]

    updated = db.update_complaint_status(id_plainte, new_status, extra_fields)
    if not updated:
        return jsonify({'error': f'Réclamation {id_plainte} introuvable.'}), 404
    return jsonify({'status': 'updated', 'id_plainte': id_plainte, 'nouveau_statut': new_status})


@app.route('/technicians', methods=['GET'])
def list_technicians_route():
    db_conn = db.get_db()
    techs = list(db_conn.users.find({'role': 'TECHNICIEN'}, {'_id': 0, 'password': 0}))
    for t in techs:
        if 'disponibilite' not in t or not t['disponibilite']:
            t['disponibilite'] = 'Disponible'
    return jsonify({'results': techs})


@app.route('/technicians/availability', methods=['GET', 'POST'])
def technician_availability_route():
    db_conn = db.get_db()
    if request.method == 'GET':
        email = request.args.get('email')
        if not email:
            return jsonify({'error': 'email requis'}), 400
        user = db_conn.users.find_one({'email': email})
        dispo = user.get('disponibilite', 'Disponible') if user else 'Disponible'
        return jsonify({'status': 'ok', 'email': email, 'availability': dispo})

    body = request.get_json(silent=True) or {}
    email = body.get('email')
    dispo = body.get('availability') or body.get('disponibilite')
    if not email or dispo not in ('Disponible', 'Occupé', 'En congé'):
        return jsonify({'error': 'champs invalides'}), 400

    result = db_conn.users.update_one(
        {'email': email, 'role': 'TECHNICIEN'},
        {'$set': {'disponibilite': dispo}}
    )
    if result.matched_count == 0:
        return jsonify({'error': 'technicien introuvable'}), 404
        
    return jsonify({'status': 'ok', 'email': email, 'availability': dispo})



@app.route('/users', methods=['GET'])
def list_users_route():
    """List all users, optionally filtered by role and/or governorate."""
    db_conn = db.get_db()
    query = {}
    role = request.args.get('role')
    gov = request.args.get('governorate')
    if role:
        query['role'] = role.upper()
    if gov:
        query['governorate'] = gov
    users = list(db_conn.users.find(query, {'_id': 0, 'password': 0,
                                             'verificationCode': 0,
                                             'resetPasswordToken': 0,
                                             'profileImageBase64': 0}))
    return jsonify({'results': users, 'total': len(users)})


@app.route('/users', methods=['POST'])
def create_user_route():
    """Admin creates a new user (technician, admin, or citizen)."""
    body = request.get_json(silent=True) or {}
    required = ('fullName', 'email', 'role', 'governorate')
    for field in required:
        if not body.get(field):
            return jsonify({'error': f'champ requis manquant: {field}'}), 400

    role = body['role'].upper()
    if role not in ('CITIZEN', 'ADMIN', 'TECHNICIEN'):
        return jsonify({'error': 'rôle invalide (CITIZEN, ADMIN, TECHNICIEN)'}), 400

    db_conn = db.get_db()
    if db_conn.users.find_one({'email': body['email']}):
        return jsonify({'error': 'email déjà utilisé'}), 409

    from datetime import datetime, timezone
    import bcrypt
    raw_pwd = body.get('password', 'sonede2026')
    hashed_pwd = bcrypt.hashpw(raw_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = {
        'fullName': body['fullName'],
        'email': body['email'],
        'password': hashed_pwd,
        'role': role,
        'phone': body.get('phone', ''),
        'address': body.get('address', ''),
        'governorate': body['governorate'],
        'delegation': body.get('delegation', ''),
        'enabled': True,
        'disponibilite': 'Disponible' if role == 'TECHNICIEN' else None,
        'createdAt': datetime.now(timezone.utc),
        'updatedAt': datetime.now(timezone.utc),
    }
    db_conn.users.insert_one(user)
    user.pop('_id', None)
    user.pop('password', None)
    return jsonify({'status': 'created', 'user': user}), 201


@app.route('/users/<email>', methods=['DELETE'])
def delete_user_route(email):
    db_conn = db.get_db()
    result = db_conn.users.delete_one({'email': email})
    if result.deleted_count == 0:
        return jsonify({'error': 'utilisateur introuvable'}), 404
    return jsonify({'status': 'deleted', 'email': email})


@app.route('/auth/login', methods=['POST'])
def login_route():
    """Authenticate user directly against MongoDB users collection."""
    body = request.get_json(silent=True) or {}
    email = body.get('email', '').strip()
    password = body.get('password', '')
    if not email or not password:
        return jsonify({'error': 'email et mot de passe requis'}), 400

    db_conn = db.get_db()
    user = db_conn.users.find_one({'email': email}, {'profileImageBase64': 0})
    if not user:
        return jsonify({'error': 'utilisateur introuvable'}), 401

    # Check if account is enabled
    if not user.get('enabled', False):
        return jsonify({'error': 'Compte non vérifié. Vérifiez votre email.'}), 403

    # Verify password — support BCrypt ($2a$/$2b$) and SHA-256
    stored = user.get('password', '')
    ok = False
    if stored.startswith('$2a$') or stored.startswith('$2b$'):
        try:
            import bcrypt
            ok = bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
        except Exception:
            ok = False
    else:
        import hashlib
        ok = stored == hashlib.sha256(password.encode()).hexdigest()

    if not ok:
        return jsonify({'error': 'mot de passe incorrect'}), 401

    user.pop('_id', None)
    user.pop('password', None)
    user.pop('verificationCode', None)
    user.pop('resetPasswordToken', None)
    if 'role' in user:
        user['role'] = user['role'].upper()
    return jsonify({'status': 'ok', 'user': user})



@app.route('/users/profile', methods=['GET'])
def get_profile_route():
    """Get user profile by email query param."""
    email = request.args.get('email', '').strip()
    if not email:
        return jsonify({'error': 'email requis'}), 400
    db_conn = db.get_db()
    user = db_conn.users.find_one({'email': email},
                                   {'_id': 0, 'password': 0,
                                    'verificationCode': 0,
                                    'resetPasswordToken': 0})
    if not user:
        return jsonify({'error': 'utilisateur introuvable'}), 404
    return jsonify(user)


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------

@app.route('/analyze_image', methods=['POST'])
def analyze_image_route():
    body = request.get_json(silent=True) or {}
    image_base64 = body.get('image_base64', '')
    if not image_base64:
        return jsonify({'error': 'Le champ "image_base64" est requis.'}), 400
    
    result = vision_processor.analyze_image(image_base64)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Prédiction directe (debug / intégrations qui ne veulent pas du flow guidé)
# ---------------------------------------------------------------------------

@app.route('/predict', methods=['POST'])
def predict_route():
    body = request.get_json(silent=True) or {}
    texte = body.get('texte', '')

    if not texte or not texte.strip():
        return jsonify({'error': 'Le champ "texte" est requis et ne peut pas être vide.'}), 400

    result = classifier.predict(texte)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Self-Growing Loop & Retraining
# ---------------------------------------------------------------------------

def _check_auto_retrain():
    """Vérifie si on a atteint le seuil de feedback pour déclencher un réentraînement."""
    if not os.path.exists(FEEDBACK_PATH):
        return

    try:
        count = 0
        with open(FEEDBACK_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('verified') == 'True':
                    count += 1
        
        if count >= AUTO_RETRAIN_THRESHOLD:
            print(f"[app] Seuil d'auto-retrain atteint ({count} >= {AUTO_RETRAIN_THRESHOLD}). Lancement en arrière-plan...")
            def bg_retrain():
                from train_model import train_and_save
                try:
                    train_and_save()
                    load_models()
                    # TODO: vider ou archiver les feedbacks utilisés
                    print("[app] Auto-retrain terminé avec succès.")
                except Exception as e:
                    print(f"[app] Erreur lors de l'auto-retrain: {e}")
            
            threading.Thread(target=bg_retrain).start()
    except Exception as e:
        print(f"[app] Erreur check_auto_retrain: {e}")


@app.route('/feedback', methods=['POST'])
def feedback_route():
    """
    Enregistre une correction humaine. Stocké mais N'EST PAS appliqué
    automatiquement au modèle en production : il faut appeler /retrain (ou
    lancer train_model.py) pour que le modèle en tienne compte -- volontaire,
    pour éviter l'empoisonnement du modèle par des corrections non validées.

    Body attendu :
    {
        "texte": "...",
        "categorie_corrigee": "fuite_visible",
        "urgence_corrigee": "haute",
        "verified": true
    }
    """
    body = request.get_json(silent=True) or {}
    texte = body.get('texte', '').strip()
    categorie_corrigee = body.get('categorie_corrigee')
    urgence_corrigee = body.get('urgence_corrigee')
    verified = bool(body.get('verified', False))

    if not texte:
        return jsonify({'error': 'Le champ "texte" est requis.'}), 400
    if categorie_corrigee and categorie_corrigee not in classifier.VALID_CATEGORIES:
        return jsonify({'error': f'categorie_corrigee doit être parmi {classifier.VALID_CATEGORIES}'}), 400
    if urgence_corrigee and urgence_corrigee not in classifier.VALID_URGENCIES:
        return jsonify({'error': f'urgence_corrigee doit être parmi {classifier.VALID_URGENCIES}'}), 400

    file_exists = os.path.exists(FEEDBACK_PATH)
    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
    with open(FEEDBACK_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['texte_plainte', 'categorie_corrigee', 'urgence_corrigee', 'verified', 'logged_at'])
        writer.writerow([
            texte,
            categorie_corrigee or '',
            urgence_corrigee or '',
            verified,
            datetime.now(timezone.utc).isoformat(),
        ])

    _check_auto_retrain()

    return jsonify({'status': 'saved'}), 201


@app.route('/label_unknown_word', methods=['POST'])
def label_unknown_word_route():
    """
    Associe un mot inconnu (ex: 'blabla') à un alias ou mot canonique existant (ex: 'fuite').
    Permet d'étendre progressivement le dictionnaire Derja.
    """
    body = request.get_json(silent=True) or {}
    mot_inconnu = (body.get('mot_inconnu') or '').strip().lower()
    mot_canonique = (body.get('mot_canonique') or '').strip().lower()
    
    if not mot_inconnu or not mot_canonique:
        return jsonify({'error': 'mot_inconnu et mot_canonique sont requis.'}), 400
        
    file_exists = os.path.exists(UNKNOWN_WORDS_PATH)
    os.makedirs(os.path.dirname(UNKNOWN_WORDS_PATH), exist_ok=True)
    with open(UNKNOWN_WORDS_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['mot_inconnu', 'mot_canonique', 'logged_at'])
        writer.writerow([mot_inconnu, mot_canonique, datetime.now(timezone.utc).isoformat()])
        
    return jsonify({'status': 'saved'})


@app.route('/retrain', methods=['POST'])
def retrain_route():
    """À appeler manuellement (ou via cron nocturne) une fois assez de
    feedback vérifié accumulé -- pas à chaque requête utilisateur."""
    from train_model import train_and_save
    try:
        train_and_save()
        load_models()
        return jsonify({'status': 'retrained'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/faq', methods=['GET'])
def list_faq_route():
    """Retourne la liste complète des questions/réponses FAQ pour affichage
    dans l'application mobile (section Aide/FAQ)."""
    try:
        docs = rag._load_faq()
        return jsonify({'count': len(docs), 'faq': docs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/learning/gaps', methods=['GET'])
def get_learning_gaps_route():
    """Retourne les questions que le chatbot n'a pas su répondre, pour que
    l'administrateur puisse enrichir la FAQ."""
    limit = int(request.args.get('limit', 50))
    only_unresolved = request.args.get('unresolved_only', 'true').lower() == 'true'
    
    gaps = learning.get_learning_gaps(db.get_db(), limit=limit, only_unresolved=only_unresolved)
    return jsonify({'count': len(gaps), 'gaps': gaps})


@app.route('/learning/faq-stats', methods=['GET'])
def get_faq_stats_route():
    """Retourne les statistiques d'utilisation des différentes questions FAQ."""
    limit = int(request.args.get('limit', 50))
    stats = learning.get_faq_usage_stats(db.get_db(), limit=limit)
    return jsonify({'count': len(stats), 'stats': stats})


# ---------------------------------------------------------------------------
# Chat History (ChatGPT style)
# ---------------------------------------------------------------------------

@app.route('/users/<user_id>/conversations', methods=['GET'])
def get_user_conversations_route(user_id):
    """Retourne la liste des conversations (historique) pour un utilisateur donné."""
    convs = db.list_user_conversations(user_id)
    return jsonify({"conversations": convs})


@app.route('/conversations/<session_id>', methods=['GET'])
def get_conversation_route(session_id):
    """Retourne l'historique complet d'une conversation spécifique."""
    session = db.get_session(session_id)
    if not session:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify(session)


@app.route('/conversations/<session_id>', methods=['DELETE'])
def delete_conversation_route(session_id):
    """Permet à l'utilisateur de supprimer manuellement une conversation de son historique."""
    db.delete_session(session_id)
    return jsonify({"status": "deleted"})


if __name__ == '__main__':
    load_models()
    app.run(host='0.0.0.0', port=5000, debug=False)
