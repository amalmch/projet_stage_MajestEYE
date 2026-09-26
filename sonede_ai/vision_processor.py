"""
Vision Processor — Classification d'images de problèmes d'eau SONEDE via CLIP.

Ce module utilise le modèle CLIP pré-entraîné (openai/clip-vit-base-patch32)
pour classifier automatiquement les photos soumises par les usagers en
catégories de réclamation SONEDE.

Fonctionnement :
    - Le modèle et le processeur sont chargés paresseusement (lazy loading)
      lors du premier appel à ``analyze_image``.
    - La classification est « zero-shot » : on compare l'image aux
      descriptions textuelles de chaque catégorie sans entraînement
      supplémentaire.

Dépendances requises :
    - transformers
    - torch
    - Pillow (PIL)

Exemple d'utilisation ::

    from sonede_ai.vision_processor import analyze_image

    result = analyze_image(base64_string)
    print(result["category_hint"], result["confidence"])
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded globals
# ---------------------------------------------------------------------------
_model = None
_processor = None
_model_name: str = "openai/clip-vit-base-patch32"

# ---------------------------------------------------------------------------
# Catégories de réclamation SONEDE et leurs descriptions textuelles
# ---------------------------------------------------------------------------
CATEGORY_LABELS: dict[str, list[str]] = {
    "fuite_visible": [
        "a water leak on a pipe or road",
        "water flooding from a broken pipe",
        "water running on the street",
    ],
    "qualite_eau": [
        "dirty yellow or brown water",
        "turbid cloudy water",
        "water with unusual color",
    ],
    "panne_pompage": [
        "a broken water pump",
        "a damaged pumping station",
        "electrical equipment failure",
    ],
    "facturation": [
        "a water bill or invoice document",
        "a water meter reading",
    ],
    "pression_faible": [
        "a thin stream of water from a tap",
        "very low water flow",
    ],
    "coupure_non_signalee": [
        "a dry empty tap with no water",
        "empty water tank",
    ],
}

# Flat list of all text prompts and reverse mapping prompt → category
_all_prompts: list[str] = []
_prompt_to_category: dict[str, str] = {}

for _cat, _descs in CATEGORY_LABELS.items():
    for _desc in _descs:
        _all_prompts.append(_desc)
        _prompt_to_category[_desc] = _cat

# Confidence threshold below which we consider the classification unreliable
CONFIDENCE_THRESHOLD: float = 0.3


# ---------------------------------------------------------------------------
# Model loading helpers
# ---------------------------------------------------------------------------

def _load_model() -> None:
    """Charge le modèle CLIP et le processeur de manière paresseuse.

    Cette fonction est appelée automatiquement lors du premier appel à
    :func:`analyze_image`. Le modèle est mis en cache dans les variables
    globales ``_model`` et ``_processor``.

    Raises
    ------
    RuntimeError
        Si le modèle ne peut pas être chargé (bibliothèque manquante,
        poids introuvables, etc.).
    """
    global _model, _processor

    if _model is not None and _processor is not None:
        return

    try:
        from transformers import CLIPModel, CLIPProcessor  # type: ignore[import-untyped]

        logger.info("Chargement du modèle CLIP « %s »…", _model_name)
        _processor = CLIPProcessor.from_pretrained(_model_name)
        _model = CLIPModel.from_pretrained(_model_name)
        _model.eval()
        logger.info("Modèle CLIP chargé avec succès.")
    except Exception as exc:
        _model = None
        _processor = None
        raise RuntimeError(
            f"Impossible de charger le modèle CLIP ({_model_name}): {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_image(image_base64: str) -> dict[str, Any]:
    """Analyse une image encodée en base64 et renvoie la catégorie SONEDE.

    Parameters
    ----------
    image_base64 : str
        L'image encodée en base64 (JPEG, PNG, etc.).

    Returns
    -------
    dict
        Dictionnaire contenant :

        - ``category_hint`` (*str | None*) — catégorie prédite ou ``None``
          si la confiance est inférieure au seuil.
        - ``confidence`` (*float*) — score de confiance de la catégorie
          prédite (entre 0 et 1).
        - ``all_scores`` (*dict[str, float]*) — scores agrégés pour
          chaque catégorie SONEDE.
        - ``description`` (*str*) — description textuelle la plus
          pertinente selon CLIP.

    Notes
    -----
    Si l'image est invalide, corrompue ou si le modèle n'est pas
    disponible, la fonction renvoie un résultat avec
    ``category_hint=None`` et ``confidence=0.0`` au lieu de lever une
    exception.
    """

    # -- 1. Décoder l'image base64 ------------------------------------------
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except Exception as exc:
        logger.warning("Échec du décodage base64 : %s", exc)
        return _error_result("Image base64 invalide.")

    try:
        from PIL import Image  # type: ignore[import-untyped]

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        logger.warning("Impossible d'ouvrir l'image : %s", exc)
        return _error_result("Image corrompue ou format non supporté.")

    # -- 2. Charger le modèle -----------------------------------------------
    try:
        _load_model()
    except RuntimeError as exc:
        logger.error("Modèle indisponible : %s", exc)
        return _error_result("Modèle CLIP indisponible.")

    # -- 3. Classification zero-shot ----------------------------------------
    try:
        import torch  # type: ignore[import-untyped]

        inputs = _processor(
            text=_all_prompts,
            images=image,
            return_tensors="pt",
            padding=True,
        )

        with torch.no_grad():
            outputs = _model(**inputs)

        # Similarité cosinus normalisée → probabilités
        logits_per_image = outputs.logits_per_image  # shape: (1, n_prompts)
        probs = logits_per_image.softmax(dim=1).squeeze(0)  # shape: (n_prompts,)

        # Associer chaque prompt à son score
        prompt_scores: dict[str, float] = {
            prompt: round(float(probs[i]), 4)
            for i, prompt in enumerate(_all_prompts)
        }

        # Agréger les scores par catégorie (score max parmi les prompts)
        category_scores: dict[str, float] = {}
        for cat, descs in CATEGORY_LABELS.items():
            category_scores[cat] = round(
                max(prompt_scores[d] for d in descs), 4
            )

        # Meilleure catégorie
        best_category = max(category_scores, key=category_scores.get)  # type: ignore[arg-type]
        best_confidence = category_scores[best_category]

        # Meilleure description (prompt individuel)
        best_prompt = max(prompt_scores, key=prompt_scores.get)  # type: ignore[arg-type]

        # Appliquer le seuil de confiance
        if best_confidence < CONFIDENCE_THRESHOLD:
            logger.info(
                "Confiance trop faible (%.2f < %.2f) — pas de catégorie.",
                best_confidence,
                CONFIDENCE_THRESHOLD,
            )
            return {
                "category_hint": None,
                "confidence": best_confidence,
                "all_scores": category_scores,
                "description": best_prompt,
            }

        return {
            "category_hint": best_category,
            "confidence": best_confidence,
            "all_scores": category_scores,
            "description": best_prompt,
        }

    except Exception as exc:
        logger.exception("Erreur lors de la classification CLIP : %s", exc)
        return _error_result("Erreur lors de l'analyse de l'image.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_result(description: str) -> dict[str, Any]:
    """Génère un résultat d'erreur standardisé.

    Parameters
    ----------
    description : str
        Message décrivant l'erreur rencontrée.

    Returns
    -------
    dict
        Résultat avec ``category_hint=None``, ``confidence=0.0`` et des
        scores à zéro pour chaque catégorie.
    """
    return {
        "category_hint": None,
        "confidence": 0.0,
        "all_scores": {cat: 0.0 for cat in CATEGORY_LABELS},
        "description": description,
    }
