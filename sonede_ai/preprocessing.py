"""
Prétraitement de texte partagé entre l'entraînement et l'API Flask.
IMPORTANT : ce fichier doit rester identique des deux côtés (train + serve),
sinon le modèle verra du texte différent en production qu'à l'entraînement.

Pipeline v3 :
  1. Nettoyage de surface (URLs, espaces, Unicode, diacritiques, minuscules)
  2. Substitution de caractères Arabizi (8→gh, 9→q, 7→h, 5→kh, 3→a)
  3. Normalisation Derja (alias → forme canonique via dictionnaire étendu)
"""
import re
import unicodedata

from dialect_dictionary import apply_char_substitutions, normalize_derja

# Tashkeel (diacritiques arabes) : ajoutent du bruit sans changer le sens
# pour la classification, on les retire.
_ARABIC_DIACRITICS = re.compile(r'[\u064B-\u0652\u0670\u0640]')

_URL_RE = re.compile(r'https?://\S+|www\.\S+')
_MULTI_SPACE_RE = re.compile(r'\s+')
_MULTI_PUNCT_RE = re.compile(r'([!?.,]){2,}')


def normalize_text(text: str) -> str:
    """Normalise un texte multilingue (fr / ar / tn_latin / tn_arabe) avant
    vectorisation. Inclut désormais la normalisation Derja (Arabizi +
    dictionnaire d'alias) pour que les formes dialectales soient ramenées
    à leur forme canonique avant embedding / classification."""
    if not isinstance(text, str):
        return ''

    t = text.strip()
    t = _URL_RE.sub(' ', t)

    # Normalisation Unicode (formes composées/décomposées équivalentes)
    t = unicodedata.normalize('NFKC', t)

    # Retirer les diacritiques arabes (tashkeel)
    t = _ARABIC_DIACRITICS.sub('', t)

    # Minuscules (n'affecte que les caractères latins, sans effet sur l'arabe)
    t = t.lower()

    # Compresser la ponctuation répétée ("!!!" -> "!") et les espaces
    t = _MULTI_PUNCT_RE.sub(r'\1', t)
    t = _MULTI_SPACE_RE.sub(' ', t)

    # ── Étape Derja ──
    # 1. Substitution des chiffres Arabizi → lettres latines
    t = apply_char_substitutions(t)
    # 2. Remplacement des alias Derja par leur forme canonique
    t = normalize_derja(t)

    # Re-compresser les espaces après les substitutions
    t = _MULTI_SPACE_RE.sub(' ', t)

    return t.strip()
