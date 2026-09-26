"""
RAG (Retrieval Augmented Generation) for the SONEDE chatbot.

v4 : Improved search with keyword boosting, multi-language answer
selection, and better confidence thresholds for broader FAQ matching.
"""
import json
import os
import re

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from preprocessing import normalize_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAQ_PATH = os.path.join(BASE_DIR, 'faq.json')

# Increased to 0.78 to prevent hallucinated/wrong matches for off-topic queries
CONFIDENCE_THRESHOLD = 0.78
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-base"
EMBEDDING_PREFIX_DOC = "passage: "
EMBEDDING_PREFIX_QUERY = "query: "

# Keyword boost: if user message contains exact keywords from a FAQ entry
KEYWORD_BOOST = 0.08

_state = {}


def _load_faq():
    with open(FAQ_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_index():
    """
    Build the semantic search index over the FAQ documents.
    Call once at API startup.
    """
    print(f"[rag] Loading model {EMBEDDING_MODEL_NAME}...")
    embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    docs = _load_faq()
    corpus = [
        f"{EMBEDDING_PREFIX_DOC}{normalize_text(d['titre'])} "
        f"{normalize_text(d.get('contenu_fr', ''))} "
        f"{normalize_text(d.get('contenu_ar', ''))} "
        f"{normalize_text(d.get('contenu_en', ''))}"
        for d in docs
    ]

    print("[rag] Vectorizing FAQ documents...")
    matrix = embed_model.encode(corpus, normalize_embeddings=True)

    _state['docs'] = docs
    _state['embed_model'] = embed_model
    _state['matrix'] = matrix
    return len(docs)


def retrieve(query: str, top_k: int = 3, category_hint: str = None,
             lang: str = "fr") -> dict:
    """
    Search the FAQ for the best matching answer.

    Returns
    -------
    dict
        {
            "results": [
                {
                    "id": str,
                    "titre": str,
                    "contenu": str,       # answer in the user's language
                    "contenu_fr": str,
                    "contenu_ar": str,
                    "contenu_en": str,
                    "score": float,
                },
                ...
            ],
            "confident": bool,
        }
    """
    if 'embed_model' not in _state:
        build_index()

    clean = normalize_text(query)
    q_vec = _state['embed_model'].encode(
        [f"{EMBEDDING_PREFIX_QUERY}{clean}"], normalize_embeddings=True
    )
    scores = cosine_similarity(q_vec, _state['matrix'])[0]

    docs = _state['docs']
    clean_lower = clean.lower()
    # \w+ in Python 3 natively supports Arabic, French accents (é, à), and numbers (mta3).
    query_tokens = set(re.findall(r"\w+", clean_lower))

    scored = []
    for doc, score in zip(docs, scores):
        boosted = float(score)

        # Category hint boost
        if category_hint and doc.get('category') == category_hint:
            boosted += 0.05

        # Keyword boost: check if any of the FAQ's keywords appear in the query
        doc_keywords = set(k.lower() for k in doc.get('keywords', []))
        keyword_hits = len(query_tokens & doc_keywords)
        if keyword_hits > 0:
            boosted += min(keyword_hits * KEYWORD_BOOST, 0.2)

        scored.append((boosted, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    # Select the answer in the user's preferred language
    lang_key = _lang_to_content_key(lang)

    results = []
    for score, doc in top:
        # Pick the best available language for the answer
        contenu = doc.get(lang_key) or doc.get("contenu_fr", "")
        results.append({
            "id": doc["id"],
            "titre": doc["titre"],
            "contenu": contenu,
            "contenu_fr": doc.get("contenu_fr", ""),
            "contenu_ar": doc.get("contenu_ar", ""),
            "contenu_en": doc.get("contenu_en", ""),
            "score": round(score, 3),
        })

    confident = bool(results) and results[0]["score"] >= CONFIDENCE_THRESHOLD

    return {"results": results, "confident": confident}


def _lang_to_content_key(lang: str) -> str:
    """Map detected language code to the FAQ content field name."""
    if lang in ("ar", "tn_arabe"):
        return "contenu_ar"
    if lang == "en":
        return "contenu_en"
    return "contenu_fr"