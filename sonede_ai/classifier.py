"""
Chargement des modèles ML et logique de prédiction (catégorie + urgence).
v3 : Utilise SentenceTransformer (intfloat/multilingual-e5-base) au lieu de TF-IDF.
Inclut un mécanisme de RAG (Similarité Cosinus) et un fallback LLM local (Ollama)
lorsque la confiance du classifieur LogisticRegression est basse.
"""
import os

import joblib
import numpy as np
import scipy.sparse as sp
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from preprocessing import normalize_text
from dialect_dictionary import analyze_dialect
from llm_fallback import classify_with_llm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'model')

CATEGORY_CONFIDENCE_THRESHOLD = 0.5
RAG_SIMILARITY_THRESHOLD = 0.85
EMBEDDING_PREFIX = "query: "
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-base"

_state = {}
VALID_CATEGORIES = []
VALID_URGENCIES = []


def load_models():
    """Charge (ou recharge) les modèles depuis disque en mémoire."""
    global VALID_CATEGORIES, VALID_URGENCIES
    
    print(f"[classifier] Chargement de SentenceTransformer ({EMBEDDING_MODEL_NAME})...")
    _state['embed_model'] = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    _state['category_model'] = joblib.load(os.path.join(MODEL_DIR, 'category_model.joblib'))
    _state['urgency_model'] = joblib.load(os.path.join(MODEL_DIR, 'urgency_model.joblib'))
    _state['category_encoder'] = joblib.load(os.path.join(MODEL_DIR, 'category_encoder.joblib'))
    
    rag_path = os.path.join(MODEL_DIR, 'dataset_embeddings.joblib')
    if os.path.exists(rag_path):
        _state['rag_data'] = joblib.load(rag_path)
    else:
        _state['rag_data'] = None
        
    VALID_CATEGORIES = sorted(_state['category_model'].classes_.tolist())
    VALID_URGENCIES = sorted(_state['urgency_model'].classes_.tolist())
    return VALID_CATEGORIES, VALID_URGENCIES


def is_loaded() -> bool:
    return 'category_model' in _state and 'embed_model' in _state


def predict(texte: str) -> dict:
    """
    Prédit la catégorie et l'urgence en utilisant une approche en cascade :
    1. Embedding avec SentenceTransformer
    2. Modèle LogisticRegression principal
    3. Si confiance < 0.5 -> RAG (plus proche voisin dans dataset_embeddings)
    4. Si RAG < 0.85 -> Fallback LLM (Ollama)
    """
    clean = normalize_text(texte)
    if not clean:
        return {
            'categorie': 'inconnu',
            'categorie_confidence': 0.0,
            'urgence': 'basse',
            'urgence_confidence': 0.0,
            'toutes_categories': {},
            'needs_clarification': True,
            'source': 'none',
            'rag_info': None,
            'dialect_matches': []
        }

    # ── 1. Embedding ──
    prefixed = f"{EMBEDDING_PREFIX}{clean}"
    X = _state['embed_model'].encode([prefixed], normalize_embeddings=True)

    # ── 2. Logistic Regression (Primary) ──
    cat_proba = _state['category_model'].predict_proba(X)[0]
    cat_classes = _state['category_model'].classes_
    best_cat_idx = cat_proba.argmax()
    categorie = cat_classes[best_cat_idx]
    categorie_confidence = float(cat_proba[best_cat_idx])

    needs_clarification = (categorie_confidence < CATEGORY_CONFIDENCE_THRESHOLD)
    source = 'model'
    rag_info = None

    # ── 3. Fallback (RAG -> LLM) ──
    if needs_clarification and _state.get('rag_data'):
        # RAG Search
        sims = cosine_similarity(X, _state['rag_data']['embeddings'])[0]
        best_sim_idx = sims.argmax()
        best_sim = float(sims[best_sim_idx])

        if best_sim >= RAG_SIMILARITY_THRESHOLD:
            categorie = _state['rag_data']['categories'][best_sim_idx]
            categorie_confidence = best_sim
            needs_clarification = False
            source = 'rag'
            rag_info = {
                'matched_text': _state['rag_data']['texts'][best_sim_idx],
                'similarity': round(best_sim, 3)
            }
        else:
            # LLM Fallback
            llm_result = classify_with_llm(texte, VALID_CATEGORIES)
            if llm_result['category']:
                categorie = llm_result['category']
                categorie_confidence = llm_result['confidence']
                needs_clarification = False
                source = 'llm'

    # ── 4. Urgency Cascade ──
    cat_encoded = _state['category_encoder'].transform([[categorie]])
    X_urgency = sp.hstack([sp.csr_matrix(X), cat_encoded]).tocsr()

    urg_proba = _state['urgency_model'].predict_proba(X_urgency)[0]
    urg_classes = _state['urgency_model'].classes_
    best_urg_idx = urg_proba.argmax()
    urgence = urg_classes[best_urg_idx]
    urgence_confidence = float(urg_proba[best_urg_idx])

    # ── 5. Dialect Urgency Check ──
    dialect_info = analyze_dialect(clean)
    if dialect_info['urgency_signal'] and urgence == 'basse':
        urgence = 'haute'
        urgence_confidence = 1.0
        source += '+dialect_urgency'
        
    # Si la catégorie prédite a été influencée par le dico dialectal (RAG ou pas), on l'indique
    if dialect_info['category_hints'] and categorie in dialect_info['category_hints']:
        source += '+dialect_hint'

    return {
        'categorie': categorie,
        'categorie_confidence': round(categorie_confidence, 3),
        'urgence': urgence,
        'urgence_confidence': round(urgence_confidence, 3),
        'toutes_categories': {
            str(cls): round(float(p), 3) for cls, p in zip(cat_classes, cat_proba)
        },
        'needs_clarification': needs_clarification,
        'source': source,
        'rag_info': rag_info,
        'dialect_matches': dialect_info['matches']
    }
