"""
Détection de langue légère pour le chatbot SONEDE.

Ne dépend d'aucune librairie externe supplémentaire (pas de fasttext/langdetect) :
juste des heuristiques sur les caractères Unicode et des listes de mots-outils.
Cible : 5 classes (fr / ar / tn_latin / tn_arabe / en, + mixed/unknown).

Changement vs la v1 : la v1 ne distinguait jamais "ar" (arabe standard) de
"tn_arabe" (derja en graphie arabe) -- tout texte majoritairement en
caractères arabes retombait sur "ar" faute de lexique. On ajoute ici une
liste de particules/mots très fréquents en derja tunisienne graphie arabe et
absents (ou très rares) en arabe standard moderne (MSA), pour faire la
distinction. Toujours pas un modèle : un lexique explicable, comme le reste
du pipeline.

Si un jour vous voulez remplacer ceci par XLM-R (cf. doc d'architecture),
gardez la même signature de fonction `detect_language(text) -> dict`.
"""
import re

_ARABIC_CHAR_RE = re.compile(r'[\u0600-\u06FF]')
_LATIN_CHAR_RE = re.compile(r'[a-zA-Z]')

# Mots-outils qui trahissent le français "standard".
_FRENCH_MARKERS = {
    "je", "nous", "vous", "le", "la", "les", "des", "une", "un", "est",
    "sans", "depuis", "avec", "pour", "que", "cette", "mon", "ma", "mes",
    "bonjour", "merci", "svp", "eau", "facture",
}

# Mots-outils qui trahissent l'anglais.
_ENGLISH_MARKERS = {
    "the", "is", "my", "water", "since", "please", "bill", "hello", "thanks",
    "no", "have", "has", "days", "leak",
}

# Marqueurs Derja très fréquents en caractères latins (tn_latin).
_DERJA_LATIN_MARKERS = {
    "el", "fama", "famech", "ma3andich", "3andi", "3andhom", "yji", "behi",
    "khayba", "barcha", "3ala", "fi", "mte3", "kifech", "chna3mel", "ya",
    "kho", "weldi", "3ayetlkom", "9asset", "dh3if", "tay7", "m3aker",
}

# Marqueurs Derja très fréquents en caractères ARABES, quasi absents du MSA
# écrit (particules, formes dialectales de base, mots du quotidien).
# Objectif : séparer "ar" (arabe standard / formel) de "tn_arabe" (derja
# écrite en graphie arabe), sans prétendre couvrir tout le dialecte.
_DERJA_ARABIC_MARKERS = {
    "برشة", "توا", "هكا", "زعمة", "عندي", "عندهم", "راهو", "راهي", "ماشي",
    "فما", "فماش", "قداش", "شنوة", "شنية", "كيفاش", "باش", "نحب", "نجم",
    "يجي", "ياخي", "خويا", "ولدي", "بالك", "معناتها", "مانيش", "موش",
    "كي", "وقتاش", "تفركس", "صحيت", "ياسر", "هاذاكا", "هاذيكا",
}


def _tokenize(text: str):
    return re.findall(r"[a-zA-Z]+|[\u0600-\u06FF]+", text.lower())


def detect_language(text: str) -> dict:
    """
    Retourne :
    {
        "language": "fr" | "ar" | "tn_latin" | "tn_arabe" | "en" | "mixed" | "unknown",
        "scores": {"arabic_ratio": float, "derja_latin_hits": int,
                    "derja_arabic_hits": int, ...},
    }

    Règle de décision :
      1. Texte majoritairement en caractères arabes -> "tn_arabe" si des
         particules derja arabes sont présentes, sinon "ar" par défaut.
      2. Sinon (caractères latins) -> tn_latin si des marqueurs Derja latins
         sont présents, sinon fr ou en selon les mots-outils dominants.
      3. Mélange significatif des deux scripts -> "mixed".
    """
    if not text or not text.strip():
        return {"language": "unknown", "scores": {}}

    arabic_chars = len(_ARABIC_CHAR_RE.findall(text))
    latin_chars = len(_LATIN_CHAR_RE.findall(text))
    total_chars = arabic_chars + latin_chars

    if total_chars == 0:
        return {"language": "unknown", "scores": {}}

    arabic_ratio = arabic_chars / total_chars
    tokens = _tokenize(text)

    derja_latin_hits = sum(1 for tok in tokens if tok in _DERJA_LATIN_MARKERS)
    derja_arabic_hits = sum(1 for tok in tokens if tok in _DERJA_ARABIC_MARKERS)
    french_hits = sum(1 for tok in tokens if tok in _FRENCH_MARKERS)
    english_hits = sum(1 for tok in tokens if tok in _ENGLISH_MARKERS)

    scores = {
        "arabic_ratio": round(arabic_ratio, 3),
        "derja_latin_hits": derja_latin_hits,
        "derja_arabic_hits": derja_arabic_hits,
        "french_hits": french_hits,
        "english_hits": english_hits,
    }

    if 0.2 < arabic_ratio < 0.8:
        return {"language": "mixed", "scores": scores}

    if arabic_ratio >= 0.8:
        if derja_arabic_hits >= 1:
            return {"language": "tn_arabe", "scores": scores}
        return {"language": "ar", "scores": scores}

    # Script latin dominant
    if derja_latin_hits >= 1 and derja_latin_hits >= max(french_hits, english_hits):
        return {"language": "tn_latin", "scores": scores}
    if english_hits > french_hits:
        return {"language": "en", "scores": scores}
    if french_hits > 0:
        return {"language": "fr", "scores": scores}

    return {"language": "tn_latin", "scores": scores}
