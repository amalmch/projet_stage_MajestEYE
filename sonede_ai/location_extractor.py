"""
Extraction de localisation (gouvernorat / délégation) depuis un texte libre.

Approche : gazetteer (liste de lieux connus) construit directement depuis
data/sonede_complaints_dataset.csv, plutôt qu'un modèle NER entraîné séparément.
C'est délibéré :
  - Les 20 gouvernorats tunisiens ne changent pas.
  - Les délégations de votre dataset couvrent déjà une bonne partie des cas
    réels remontés par l'app mobile.
  - Un gazetteer est 100% explicable et ne "devine" jamais un lieu qui
    n'existe pas (contrairement à un NER qui peut halluciner une entité).

v2 -- deux bugs corrigés pour supporter la Derja en graphie arabe :
  1. La normalisation retirait TOUS les caractères arabes (regex
     `[^a-z0-9\\s]` -> espace), donc un lieu écrit en arabe ne pouvait
     structurellement jamais matcher, même avec un alias arabe défini.
     Corrigé : on garde la plage Unicode arabe dans la normalisation.
  2. `_MANUAL_ALIASES` ne contenait aucun alias en graphie arabe. On ajoute
     les 24 gouvernorats tunisiens en arabe standard (mappés vers
     l'orthographe latine telle que stockée dans le CSV). Limite assumée
     (identique à l'esprit du module d'origine) : les délégations en arabe
     ne sont pas couvertes ici faute d'un référentiel de transliteration
     complet -- à enrichir au fur et à mesure, comme pour les alias latins.

Limite assumée : si une délégation n'est pas encore dans le dataset, elle ne
sera pas reconnue. Solution : ajouter la délégation dans le CSV (colonne
gouvernorat/delegation) puis relancer train_model.py -- le gazetteer se
reconstruit automatiquement au prochain chargement de ce module.
"""
import os
import re
import unicodedata

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'sonede_complaints_dataset.csv')

_ARABIC_RANGE = r'\u0600-\u06FF'

# Quelques alias/variantes orthographiques fréquentes qui ne matcheraient pas
# tel quel (accents oubliés, orthographe alternative courante, graphie
# arabe). Les clés qui ne correspondent à aucun gouvernorat/délégation
# présent dans le dataset sont ignorées silencieusement par _build_gazetteer.
_MANUAL_ALIASES = {
    "beja": "Béja",
    "medenine": "Médenine",
    "kebili": "Kébili",
    "la marsa": "La Marsa",  # zone connue non présente telle quelle dans le dataset
    "kalaa kebira": "Kalâa Kebira",
    "kalaat el andalous": "Kalâat el-Andalous",
    # -- Gouvernorats en arabe standard --
    "تونس": "Tunis",
    "أريانة": "Ariana",
    "بن عروس": "Ben Arous",
    "منوبة": "Manouba",
    "نابل": "Nabeul",
    "زغوان": "Zaghouan",
    "بنزرت": "Bizerte",
    "باجة": "Béja",
    "جندوبة": "Jendouba",
    "الكاف": "Le Kef",
    "سليانة": "Siliana",
    "سوسة": "Sousse",
    "المنستير": "Monastir",
    "المهدية": "Mahdia",
    "صفاقس": "Sfax",
    "القيروان": "Kairouan",
    "القصرين": "Kasserine",
    "سيدي بوزيد": "Sidi Bouzid",
    "قابس": "Gabès",
    "مدنين": "Médenine",
    "تطاوين": "Tataouine",
    "قفصة": "Gafsa",
    "توزر": "Tozeur",
    "قبلي": "Kébili",
}


def _strip_accents(s: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s)
        if unicodedata.category(c) != 'Mn'
    )


def _build_gazetteer():
    """
    Construit, à l'import du module :
      - la liste des gouvernorats connus
      - la liste des délégations connues, chacune mappée à son gouvernorat
      - une version "normalisée" (minuscule, sans accents/diacritiques) de
        chaque nom, pour un matching tolérant aux fautes de frappe/accents,
        en latin comme en arabe.
    """
    df = pd.read_csv(DATA_PATH)
    gouvernorats = sorted(df['gouvernorat'].dropna().unique().tolist())
    delegation_to_gouv = (
        df[['delegation', 'gouvernorat']]
        .dropna()
        .drop_duplicates()
        .set_index('delegation')['gouvernorat']
        .to_dict()
    )

    entries = []  # list of (normalized_name, display_name, level, gouvernorat)

    for g in gouvernorats:
        entries.append((_strip_accents(g).lower(), g, 'gouvernorat', g))

    for delegation, gouv in delegation_to_gouv.items():
        entries.append((_strip_accents(delegation).lower(), delegation, 'delegation', gouv))

    for alias, canonical in _MANUAL_ALIASES.items():
        if canonical not in gouvernorats and canonical not in delegation_to_gouv:
            continue  # canonical absent du dataset actuel -> alias inutile pour l'instant
        gouv = delegation_to_gouv.get(canonical, canonical if canonical in gouvernorats else None)
        level = 'gouvernorat' if canonical in gouvernorats else 'delegation'
        entries.append((_strip_accents(alias).lower(), canonical, level, gouv))

    # Trier par longueur décroissante : matcher "sfax médina" avant "sfax"
    # pour préférer la précision (délégation) au gouvernorat générique.
    entries.sort(key=lambda e: len(e[0]), reverse=True)
    return entries


_GAZETTEER = _build_gazetteer()


def extract_location(text: str) -> dict:
    """
    Retourne :
    {
        "found": bool,
        "gouvernorat": str | None,
        "delegation": str | None,   # None si seul le gouvernorat a matché
        "matched_text": str | None, # ce qui a été reconnu dans le texte original
    }

    Ne matche que sur un gazetteer connu -> pas d'hallucination de lieu.
    Si rien n'est trouvé, l'appelant (dialogue_manager.py) doit demander la
    localisation à l'utilisateur plutôt que de supposer.
    """
    if not text:
        return {"found": False, "gouvernorat": None, "delegation": None, "matched_text": None}

    norm = _strip_accents(text).lower()
    # Ponctuation -> espace, mais on garde les lettres latines, les chiffres
    # ET la plage Unicode arabe (v1 supprimait les caractères arabes ici,
    # rendant tout matching arabe impossible).
    norm = re.sub(fr'[^a-z0-9{_ARABIC_RANGE}\s]', ' ', norm)
    norm = re.sub(r'\s+', ' ', norm).strip()
    padded = f" {norm} "

    for norm_name, display_name, level, gouv in _GAZETTEER:
        # Recherche de mot entier pour éviter "ben arous" de matcher dans un
        # mot plus long par accident.
        if f" {norm_name} " in padded:
            if level == 'gouvernorat':
                return {
                    "found": True,
                    "gouvernorat": gouv,
                    "delegation": None,
                    "matched_text": display_name,
                }
            return {
                "found": True,
                "gouvernorat": gouv,
                "delegation": display_name,
                "matched_text": display_name,
            }

    return {"found": False, "gouvernorat": None, "delegation": None, "matched_text": None}
