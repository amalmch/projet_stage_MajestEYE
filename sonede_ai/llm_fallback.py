"""
LLM Fallback — Classification de réclamations SONEDE via Ollama.

Ce module fournit un mécanisme de secours lorsque le classificateur
principal (NLP ou vision) retourne une confiance insuffisante. Il envoie
le texte de la réclamation à une instance locale d'Ollama pour obtenir
une classification parmi les catégories SONEDE valides.

Fonctionnement :
    1. Vérifie que le serveur Ollama est joignable.
    2. Construit un prompt en français décrivant les catégories SONEDE.
    3. Envoie la requête au modèle LLM configuré (par défaut ``llama3``).
    4. Parse la réponse pour extraire une catégorie valide.

Dépendances requises :
    - requests (ou urllib intégré — ce module utilise ``urllib`` pour
      éviter des dépendances supplémentaires)

Exemple d'utilisation ::

    from sonede_ai.llm_fallback import classify_with_llm, is_available

    if is_available():
        result = classify_with_llm("l'eau est jaune", ["qualite_eau", "fuite_visible"])
        print(result)
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_GENERATE_URL: str = f"{OLLAMA_BASE_URL}/api/generate"
DEFAULT_MODEL: str = "llama3"
REQUEST_TIMEOUT: int = 10  # secondes

# Descriptions en français des catégories SONEDE (pour le prompt LLM)
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "fuite_visible": (
        "Fuite d'eau visible — fuite sur canalisation, eau qui coule "
        "dans la rue, rupture de conduite."
    ),
    "qualite_eau": (
        "Problème de qualité de l'eau — eau trouble, colorée (jaune, "
        "marron), mauvais goût ou odeur."
    ),
    "panne_pompage": (
        "Panne de pompage — station de pompage en panne, pompe cassée, "
        "défaillance électrique."
    ),
    "facturation": (
        "Problème de facturation — erreur sur la facture d'eau, "
        "contestation de relevé de compteur, surfacturation."
    ),
    "pression_faible": (
        "Pression d'eau faible — débit très faible au robinet, "
        "pression insuffisante."
    ),
    "coupure_non_signalee": (
        "Coupure d'eau non signalée — pas d'eau sans avis préalable, "
        "robinet sec, réservoir vide."
    ),
    "branchement": (
        "Demande de branchement ou raccordement — nouveau branchement, "
        "modification de branchement existant."
    ),
    "compteur": (
        "Problème de compteur — compteur en panne, compteur bloqué, "
        "demande de remplacement."
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_available() -> bool:
    """Vérifie si le serveur Ollama est joignable.

    Envoie une requête GET à l'URL de base d'Ollama et vérifie que le
    serveur répond avec un code HTTP 200.

    Returns
    -------
    bool
        ``True`` si le serveur Ollama répond, ``False`` sinon.
    """
    try:
        req = urllib.request.Request(OLLAMA_BASE_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        logger.debug("Ollama non joignable à %s", OLLAMA_BASE_URL)
        return False


def classify_with_llm(
    text: str,
    valid_categories: list[str],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Classifie un texte de réclamation via le LLM Ollama.

    Parameters
    ----------
    text : str
        Le texte de la réclamation de l'usager.
    valid_categories : list[str]
        Liste des identifiants de catégories valides parmi lesquels le
        LLM doit choisir.
    model : str, optional
        Nom du modèle Ollama à utiliser (par défaut ``llama3``).

    Returns
    -------
    dict
        Dictionnaire contenant :

        - ``category`` (*str | None*) — catégorie choisie par le LLM,
          ou ``None`` si la classification a échoué.
        - ``confidence`` (*float*) — score de confiance estimé
          (0.0 à 1.0). Fixé à 0.6 pour les réponses valides du LLM,
          car le LLM ne fournit pas de score natif.
        - ``llm_response`` (*str*) — réponse brute du LLM.
        - ``source`` (*str*) — ``"ollama"`` si le LLM a répondu,
          ``"none"`` sinon.
    """

    # -- Vérifier la disponibilité d'Ollama ---------------------------------
    if not is_available():
        logger.warning("Ollama indisponible — classification LLM impossible.")
        return _unavailable_result()

    # -- Construire le prompt -----------------------------------------------
    prompt = _build_prompt(text, valid_categories)

    # -- Envoyer la requête -------------------------------------------------
    try:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 150,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            OLLAMA_GENERATE_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        llm_response: str = body.get("response", "").strip()
        logger.info("Réponse LLM reçue (%d caractères).", len(llm_response))

    except urllib.error.URLError as exc:
        logger.error("Erreur réseau Ollama : %s", exc)
        return _unavailable_result()
    except json.JSONDecodeError as exc:
        logger.error("Réponse Ollama non-JSON : %s", exc)
        return _error_result("Réponse Ollama invalide (non-JSON).")
    except Exception as exc:
        logger.exception("Erreur inattendue lors de l'appel Ollama : %s", exc)
        return _error_result(f"Erreur inattendue : {exc}")

    # -- Parser la réponse pour extraire la catégorie -----------------------
    category = _extract_category(llm_response, valid_categories)

    if category is not None:
        return {
            "category": category,
            "confidence": 0.6,
            "llm_response": llm_response,
            "source": "ollama",
        }

    logger.warning(
        "Le LLM n'a pas retourné de catégorie valide parmi %s.",
        valid_categories,
    )
    return {
        "category": None,
        "confidence": 0.0,
        "llm_response": llm_response,
        "source": "ollama",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_prompt(text: str, valid_categories: list[str]) -> str:
    """Construit le prompt en français pour le LLM.

    Parameters
    ----------
    text : str
        Texte de la réclamation.
    valid_categories : list[str]
        Catégories parmi lesquelles choisir.

    Returns
    -------
    str
        Prompt complet à envoyer au LLM.
    """
    # Filtrer les descriptions pour ne garder que les catégories valides
    category_lines = []
    for cat in valid_categories:
        desc = CATEGORY_DESCRIPTIONS.get(cat, cat)
        category_lines.append(f"  - {cat} : {desc}")

    categories_block = "\n".join(category_lines)

    return (
        "Tu es un assistant de la SONEDE (Société Nationale d'Exploitation "
        "et de Distribution des Eaux) en Tunisie. Ton rôle est de classifier "
        "les réclamations des usagers.\n\n"
        "Voici les catégories possibles :\n"
        f"{categories_block}\n\n"
        "Réclamation de l'usager :\n"
        f'« {text} »\n\n'
        "Réponds UNIQUEMENT avec le nom exact de la catégorie la plus "
        "appropriée parmi celles listées ci-dessus. Ne donne aucune "
        "explication, juste le nom de la catégorie.\n\n"
        "Catégorie :"
    )


def _extract_category(
    llm_response: str,
    valid_categories: list[str],
) -> Optional[str]:
    """Extrait une catégorie valide de la réponse du LLM.

    La fonction essaie plusieurs stratégies :
    1. Correspondance exacte (la réponse entière est une catégorie).
    2. Recherche d'une catégorie présente dans la réponse.
    3. Recherche insensible à la casse et aux accents.

    Parameters
    ----------
    llm_response : str
        Réponse brute du LLM.
    valid_categories : list[str]
        Catégories valides acceptées.

    Returns
    -------
    str or None
        La catégorie extraite, ou ``None`` si aucune n'a été trouvée.
    """
    if not llm_response:
        return None

    cleaned = llm_response.strip().strip('"').strip("'").strip()

    # Stratégie 1 : correspondance exacte
    if cleaned in valid_categories:
        return cleaned

    cleaned_lower = cleaned.lower()
    if cleaned_lower in valid_categories:
        return cleaned_lower

    # Stratégie 2 : la catégorie apparaît dans la réponse
    for cat in valid_categories:
        if cat in cleaned_lower:
            return cat

    # Stratégie 3 : recherche par regex (mot isolé)
    for cat in valid_categories:
        pattern = re.compile(re.escape(cat), re.IGNORECASE)
        if pattern.search(llm_response):
            return cat

    return None


def _unavailable_result() -> dict[str, Any]:
    """Résultat standardisé quand Ollama n'est pas disponible.

    Returns
    -------
    dict
        Résultat avec ``category=None`` et ``source="none"``.
    """
    return {
        "category": None,
        "confidence": 0.0,
        "llm_response": "LLM unavailable",
        "source": "none",
    }


def _error_result(description: str) -> dict[str, Any]:
    """Résultat standardisé en cas d'erreur.

    Parameters
    ----------
    description : str
        Message d'erreur descriptif.

    Returns
    -------
    dict
        Résultat avec ``category=None`` et la description de l'erreur.
    """
    return {
        "category": None,
        "confidence": 0.0,
        "llm_response": description,
        "source": "ollama",
    }
