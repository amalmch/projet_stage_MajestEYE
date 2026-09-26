"""
Vérification des incidents existants (doublons) pour le chatbot SONEDE.

Version MongoDB : interroge la collection `complaints` (réclamations
réellement créées par le chatbot / l'app Flutter), qui est la vraie base
live. C'est le remplacement annoncé dans l'ancienne version de ce fichier
("en production, remplacez _load_complaints() par une requête à votre vraie
base"). Le CSV historique (sonede_complaints_dataset.csv) n'est plus consulté
ici : il continue de servir uniquement à train_model.py.

La logique de correspondance ne change pas : même catégorie + statut ouvert
(nouveau/en_cours) + fenêtre de temps récente, filtré par délégation si
connue, sinon gouvernorat, sinon pas de filtre géographique.
"""
import db

DEFAULT_WINDOW_DAYS = 5


def reload():
    """Conservé pour compatibilité avec app.py (appelé après /retrain) --
    n'a plus d'effet : il n'y a plus de cache CSV en mémoire à invalider,
    chaque appel interroge Mongo directement."""
    return None


def check_existing_incidents(
    categorie: str,
    delegation: str = None,
    gouvernorat: str = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict:
    """
    Retourne :
    {
        "existing_count": int,
        "matches": [ {id_plainte, statut, date_signalement, delegation, gouvernorat}, ... ],
        "recommendation": "existing_incident" | "no_match" | "insufficient_location"
    }
    """
    matches_raw = db.find_open_similar_complaints(
        categorie=categorie,
        delegation=delegation,
        gouvernorat=gouvernorat,
        window_days=window_days,
    )

    matches = [
        {
            "id_plainte": m["id_plainte"],
            "statut": m["statut"],
            "date_signalement": m["date_signalement"].strftime('%Y-%m-%d')
            if hasattr(m["date_signalement"], "strftime") else str(m["date_signalement"]),
            "delegation": m.get("delegation"),
            "gouvernorat": m.get("gouvernorat"),
        }
        for m in matches_raw
    ]

    if not delegation and not gouvernorat:
        recommendation = "insufficient_location"
    elif matches:
        recommendation = "existing_incident"
    else:
        recommendation = "no_match"

    return {
        "existing_count": len(matches),
        "matches": matches,
        "recommendation": recommendation,
    }
