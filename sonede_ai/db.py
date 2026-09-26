"""
Couche d'accès MongoDB pour le chatbot SONEDE.

Remplace le CSV comme source de vérité pour :
  - `complaints`     : les réclamations réellement créées via le chatbot /
                        l'app Flutter (ce que voient les écrans "détail
                        réclamation" et "suivi des réclamations").
  - `conversations`  : l'état de chaque session de dialogue en cours
                        (langue détectée, localisation/problème déjà
                        collectés, étape du flow). TTL sur ces documents :
                        une conversation abandonnée expire toute seule.

sonede_complaints_dataset.csv reste utilisé tel quel par train_model.py
(données d'entraînement historiques) -- on ne le touche pas. duplicate_checker
lit maintenant `complaints` (live) en plus du CSV (historique), voir ce
module.

Variables d'environnement :
  MONGO_URI      (défaut: mongodb://localhost:27017)
  MONGO_DB_NAME  (défaut: sonede_smart_platform)
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import PyMongoError

# Charge .env s'il existe (répertoire courant ou parent). N'écrase jamais des
# variables déjà exportées dans le shell -- .env sert de valeur par défaut
# pratique pour le dev local, pas pour la prod (où on exporte les vraies
# variables d'environnement / secrets manager).
load_dotenv()

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'sonede_smart_platform')

CONVERSATION_TTL_MINUTES = 30
OPEN_STATUSES = {'nouveau', 'en_cours', 'recue', 'assignee', 'enInspection', 'enReparation'}

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _db = _client[MONGO_DB_NAME]
    return _db


def ensure_indexes():
    """À appeler une fois au démarrage de l'API (voir app.py load_models)."""
    db = get_db()

    db.complaints.create_index([('id_plainte', ASCENDING)], unique=True)
    db.complaints.create_index([('statut', ASCENDING), ('categorie', ASCENDING)])
    db.complaints.create_index([('gouvernorat', ASCENDING), ('delegation', ASCENDING)])
    db.complaints.create_index([('date_signalement', DESCENDING)])

    db.conversations.create_index([('session_id', ASCENDING)], unique=True)
    # Remove TTL if it exists so chats persist
    try:
        db.conversations.drop_index("expires_at_1")
    except Exception:
        pass
    db.conversations.create_index([('user_id', ASCENDING)])


# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------

def _generate_complaint_id() -> str:
    return f"PL-{uuid.uuid4().hex[:8].upper()}"


def create_complaint(data: dict) -> dict:
    """Insère une nouvelle réclamation et retourne le document complet
    (avec id_plainte généré), pour que l'app Flutter/Angular puisse
    l'afficher immédiatement dans l'écran de détail."""
    db = get_db()
    doc = {
        'id_plainte': _generate_complaint_id(),
        'statut': 'recue',
        'date_signalement': datetime.now(timezone.utc),
        'historique_statuts': [
            {'statut': 'recue', 'horodatage': datetime.now(timezone.utc)}
        ],
        **data,
    }
    db.complaints.insert_one(doc)
    doc.pop('_id', None)
    return doc


def get_complaint(id_plainte: str) -> dict | None:
    db = get_db()
    doc = db.complaints.find_one({'id_plainte': id_plainte}, {'_id': 0})
    return doc


from bson import ObjectId
import re

def list_complaints(filters: dict = None, limit: int = 50) -> list:
    """Pour l'écran de suivi des réclamations (liste + filtres statut /
    catégorie / gouvernorat côté Angular ou Flutter)."""
    db = get_db()
    raw_query = filters or {}
    query = {}
    
    for k, v in raw_query.items():
        if k in ('user_email', 'user_id'):
            # Match case-insensitively against user_id, user_email, citoyen_email
            regex = re.compile(f"^{re.escape(str(v).strip())}$", re.IGNORECASE)
            query['$or'] = [
                {'user_id': regex},
                {'user_email': regex},
                {'citoyen_email': regex}
            ]
        elif k == 'technicien_email':
            regex = re.compile(f"^{re.escape(str(v).strip())}$", re.IGNORECASE)
            query['technicien_email'] = regex
        else:
            query[k] = v

    cursor = (
        db.complaints.find(query)
        .sort('date_signalement', DESCENDING)
        .limit(limit)
    )
    res = []
    for doc in cursor:
        doc_id = str(doc.get('_id', ''))
        doc['id'] = doc.get('id_plainte') or doc_id
        doc['id_plainte'] = doc.get('id_plainte') or doc_id
        doc['_id'] = doc_id
        res.append(doc)
    return res


def update_complaint_status(id_plainte: str, new_status: str, extra_fields: dict = None) -> bool:
    db = get_db()
    set_fields = {'statut': new_status}
    if extra_fields:
        for k, v in extra_fields.items():
            set_fields[k] = v
            
    # Build match query supporting id_plainte, string _id, and ObjectId _id
    queries = [{'id_plainte': str(id_plainte)}, {'reference': str(id_plainte)}, {'_id': str(id_plainte)}]
    try:
        if ObjectId.is_valid(str(id_plainte)):
            queries.append({'_id': ObjectId(str(id_plainte))})
    except Exception:
        pass

    result = db.complaints.update_one(
        {'$or': queries},
        {
            '$set': set_fields,
            '$push': {
                'historique_statuts': {
                    'statut': new_status,
                    'horodatage': datetime.now(timezone.utc),
                }
            },
        },
    )
    return result.matched_count > 0 or result.modified_count > 0



def find_open_similar_complaints(
    categorie: str,
    delegation: str = None,
    gouvernorat: str = None,
    window_days: int = 5,
    limit: int = 5,
) -> list:
    """Équivalent Mongo de duplicate_checker._load_complaints(), mais sur les
    réclamations LIVE (créées via le chatbot), pas le dataset historique."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    query = {
        'categorie': categorie,
        'statut': {'$in': list(OPEN_STATUSES)},
        'date_signalement': {'$gte': cutoff},
    }
    if delegation:
        query['delegation'] = delegation
    elif gouvernorat:
        query['gouvernorat'] = gouvernorat

    cursor = (
        db.complaints.find(query, {'_id': 0})
        .sort('date_signalement', DESCENDING)
        .limit(limit)
    )
    return list(cursor)


def get_unresolved_complaints(days=7):
    """Récupère les réclamations techniques non résolues des X derniers jours."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = {
        'statut': {'$in': ['nouveau', 'en_cours', 'recue', 'assignee', 'enInspection', 'enReparation']},
        'categorie': {'$in': ['fuite_visible', 'panne_pompage', 'pression_faible', 'qualite_eau', 'coupure_non_signalee', 'coupure_planifiee', 'retard_intervention']},
        'date_signalement': {'$gte': cutoff}
    }
    return list(db.complaints.find(query, {'_id': 0}))


def save_ai_insight(region: str, insight_text: str, urgency: str = "Normale"):
    """Enregistre une recommandation/alerte IA dans la collection ai_insights."""
    db = get_db()
    doc = {
        'id_insight': f"AI-{uuid.uuid4().hex[:6].upper()}",
        'region': region,
        'insight_text': insight_text,
        'urgence': urgency,
        'date_generation': datetime.now(timezone.utc)
    }
    db.ai_insights.insert_one(doc)
    doc.pop('_id', None)
    return doc


# ---------------------------------------------------------------------------
# Conversation sessions (dialogue_manager state)
# ---------------------------------------------------------------------------

def get_session(session_id: str) -> dict | None:
    db = get_db()
    return db.conversations.find_one({'session_id': session_id}, {'_id': 0})


def save_session(session_id: str, state: dict) -> None:
    db = get_db()
    now = datetime.now(timezone.utc)

    # `state` may be the dict previously returned by get_session(), which
    # already carries our own bookkeeping fields (session_id, created_at,
    # updated_at, expires_at, and Mongo's _id if not projected out). If we
    # spread those back into $set while also setting created_at via
    # $setOnInsert, Mongo raises "would create a conflict" because the same
    # path can't be touched by both operators in one update. Strip them
    # before rebuilding the update.
    clean_state = {
        k: v for k, v in state.items()
        if k not in ('_id', 'session_id', 'created_at', 'updated_at', 'expires_at')
    }

    db.conversations.update_one(
        {'session_id': session_id},
        {
            '$set': {
                **clean_state,
                'session_id': session_id,
                'updated_at': now,
            },
            '$setOnInsert': {'created_at': now},
        },
        upsert=True,
    )


def delete_session(session_id: str) -> None:
    db = get_db()
    db.conversations.delete_one({'session_id': session_id})


def is_available() -> bool:
    """Ping rapide pour /health -- ne lève pas d'exception."""
    try:
        get_db().command('ping')
        return True
    except PyMongoError:
        return False


def list_user_conversations(user_id: str) -> list:
    """Fetch all past conversations for a user, sorted by most recent."""
    db = get_db()
    cursor = (
        db.conversations.find({'user_id': user_id}, {'_id': 0, 'history': 0})
        .sort('updated_at', DESCENDING)
    )
    return list(cursor)