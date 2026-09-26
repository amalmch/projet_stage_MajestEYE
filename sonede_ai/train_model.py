"""
Entraîne les modèles de classification (catégorie + urgence) à partir de
sonede_complaints_dataset.csv, en incluant automatiquement les retours
vérifiés accumulés dans data/feedback_log.csv (voir app.py /feedback).

v3 : remplace TF-IDF par SentenceTransformer (intfloat/multilingual-e5-base)
pour des embeddings multilingues 768-dim qui comprennent nativement le
français, l'arabe, l'anglais et une grande partie du dialecte tunisien.
Le classifieur reste un LogisticRegression (rapide, interprétable) entraîné
sur ces embeddings — pas besoin de fine-tuner le transformer lui-même.

Les embeddings du dataset sont sauvegardés dans model/dataset_embeddings.joblib
pour être réutilisés par le RAG de classifier.py (recherche de similarité
cosinus quand la confiance du modèle est basse).

Usage :
    python train_model.py

Régénère à chaque exécution :
    model/category_model.joblib
    model/urgency_model.joblib
    model/category_encoder.joblib
    model/dataset_embeddings.joblib   (NEW : embeddings + textes + labels)
    model/metadata.json
    model/evaluation_report.txt
"""
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

from preprocessing import normalize_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'sonede_complaints_dataset.csv')
FEEDBACK_PATH = os.path.join(BASE_DIR, 'data', 'feedback_log.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'model')

# Modèle d'embedding multilingue — excellent pour FR/AR/EN/Derja.
# Le prefix "query: " est recommandé par intfloat pour les requêtes.
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-base"
EMBEDDING_PREFIX = "query: "

MIN_SAMPLES_PER_CLASS_FOR_TEST_SPLIT = 2


def load_training_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df[['texte_plainte', 'categorie', 'urgence']].dropna()

    # Inclure les retours vérifiés accumulés depuis la mise en prod
    if os.path.exists(FEEDBACK_PATH):
        feedback_df = pd.read_csv(FEEDBACK_PATH)
        if len(feedback_df) > 0:
            verified = feedback_df[feedback_df['verified'] == True]  # noqa: E712
            if len(verified) > 0:
                verified = verified[['texte_plainte', 'categorie_corrigee', 'urgence_corrigee']]
                verified = verified.rename(columns={
                    'categorie_corrigee': 'categorie',
                    'urgence_corrigee': 'urgence',
                })
                df = pd.concat([df, verified], ignore_index=True)
                print(f"[train] +{len(verified)} exemples vérifiés inclus depuis feedback_log.csv")

    df['texte_plainte'] = df['texte_plainte'].apply(normalize_text)
    df = df[df['texte_plainte'].str.len() > 0]
    return df


def _safe_stratify(df: pd.DataFrame, column: str):
    counts = df[column].value_counts()
    if (counts < MIN_SAMPLES_PER_CLASS_FOR_TEST_SPLIT).any():
        return None
    return df[column]


def _embed_texts(model: SentenceTransformer, texts: list[str], batch_size: int = 64) -> np.ndarray:
    """Encode texts with the E5 prefix recommended by intfloat."""
    prefixed = [f"{EMBEDDING_PREFIX}{t}" for t in texts]
    return model.encode(prefixed, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)


def train_and_save():
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = load_training_data()
    print(f"[train] {len(df)} exemples au total")

    # ── Load SentenceTransformer ──
    print(f"[train] Chargement du modèle d'embedding : {EMBEDDING_MODEL_NAME}")
    embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    # ── Train / test split ──
    stratify_col = _safe_stratify(df, 'categorie')
    train_df, test_df = train_test_split(
        df, test_size=0.2, random_state=42, stratify=stratify_col
    )

    # ── Compute embeddings ──
    print("[train] Calcul des embeddings (train)…")
    X_train = _embed_texts(embed_model, train_df['texte_plainte'].tolist())
    print("[train] Calcul des embeddings (test)…")
    X_test = _embed_texts(embed_model, test_df['texte_plainte'].tolist())

    report_lines = []

    # ── Category model ──
    print("[train] Entraînement du modèle de catégorie…")
    category_model = LogisticRegression(
        max_iter=2000,
        class_weight='balanced',
        solver='lbfgs',
        C=1.0,
    )
    category_model.fit(X_train, train_df['categorie'])

    y_pred_cat = category_model.predict(X_test)
    cat_report = classification_report(test_df['categorie'], y_pred_cat, zero_division=0)
    cat_f1 = f1_score(test_df['categorie'], y_pred_cat, average='macro', zero_division=0)
    report_lines.append(f"=== categorie (macro F1 = {cat_f1:.3f}) ===\n{cat_report}\n")
    print(f"[train] categorie macro F1: {cat_f1:.3f}")
    
    # Save Confusion Matrix for Category
    plt.figure(figsize=(10, 8))
    cm_cat = confusion_matrix(test_df['categorie'], y_pred_cat, labels=category_model.classes_)
    sns.heatmap(cm_cat, annot=True, fmt='d', cmap='Blues', xticklabels=category_model.classes_, yticklabels=category_model.classes_)
    plt.title('Matrice de Confusion - Catégorie')
    plt.ylabel('Vraie classe')
    plt.xlabel('Classe prédite')
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, 'confusion_matrix_category.png'))
    plt.close()

    # ── Urgency model (cascaded: text embedding + predicted category) ──
    print("[train] Entraînement du modèle d'urgence (cascade)…")
    category_encoder = OneHotEncoder(handle_unknown='ignore')
    train_pred_category = category_model.predict(X_train).reshape(-1, 1)
    test_pred_category = category_model.predict(X_test).reshape(-1, 1)

    cat_train_encoded = category_encoder.fit_transform(train_pred_category)
    cat_test_encoded = category_encoder.transform(test_pred_category)

    X_train_urgency = sp.hstack([sp.csr_matrix(X_train), cat_train_encoded]).tocsr()
    X_test_urgency = sp.hstack([sp.csr_matrix(X_test), cat_test_encoded]).tocsr()

    from sklearn.ensemble import RandomForestClassifier
    urgency_model = RandomForestClassifier(n_estimators=200, class_weight='balanced', random_state=42, max_depth=15)
    urgency_model.fit(X_train_urgency, train_df['urgence'])

    y_pred_urgency = urgency_model.predict(X_test_urgency)
    urg_report = classification_report(test_df['urgence'], y_pred_urgency, zero_division=0)
    urg_f1 = f1_score(test_df['urgence'], y_pred_urgency, average='macro', zero_division=0)
    report_lines.append(f"=== urgence (cascade, macro F1 = {urg_f1:.3f}) ===\n{urg_report}\n")
    print(f"[train] urgence (cascade) macro F1: {urg_f1:.3f}")

    # Save Confusion Matrix for Urgency
    plt.figure(figsize=(8, 6))
    cm_urg = confusion_matrix(test_df['urgence'], y_pred_urgency, labels=urgency_model.classes_)
    sns.heatmap(cm_urg, annot=True, fmt='d', cmap='Reds', xticklabels=urgency_model.classes_, yticklabels=urgency_model.classes_)
    plt.title('Matrice de Confusion - Urgence')
    plt.ylabel('Vraie classe')
    plt.xlabel('Classe prédite')
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, 'confusion_matrix_urgency.png'))
    plt.close()

    # ── Save models ──
    joblib.dump(category_model, os.path.join(MODEL_DIR, 'category_model.joblib'))
    joblib.dump(urgency_model, os.path.join(MODEL_DIR, 'urgency_model.joblib'))
    joblib.dump(category_encoder, os.path.join(MODEL_DIR, 'category_encoder.joblib'))

    # ── Save dataset embeddings for RAG in classifier.py ──
    # Embed the ENTIRE dataset (not just train) so RAG has max coverage.
    print("[train] Calcul des embeddings (dataset complet pour RAG)…")
    all_embeddings = _embed_texts(embed_model, df['texte_plainte'].tolist())
    rag_data = {
        'embeddings': all_embeddings,
        'texts': df['texte_plainte'].tolist(),
        'categories': df['categorie'].tolist(),
        'urgencies': df['urgence'].tolist(),
    }
    joblib.dump(rag_data, os.path.join(MODEL_DIR, 'dataset_embeddings.joblib'))
    print(f"[train] Embeddings RAG sauvegardés ({len(df)} documents)")

    # ── Metadata ──
    metadata = {
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'embedding_model': EMBEDDING_MODEL_NAME,
        'embedding_dim': int(X_train.shape[1]),
        'n_samples': len(df),
        'n_train': len(train_df),
        'n_test': len(test_df),
        'category_classes': sorted(category_model.classes_.tolist()),
        'urgency_classes': sorted(urgency_model.classes_.tolist()),
        'category_f1_macro': round(cat_f1, 3),
        'urgency_f1_macro': round(urg_f1, 3),
    }
    with open(os.path.join(MODEL_DIR, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    with open(os.path.join(MODEL_DIR, 'evaluation_report.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"[train] Modèles sauvegardés dans {MODEL_DIR}/")


if __name__ == '__main__':
    train_and_save()
