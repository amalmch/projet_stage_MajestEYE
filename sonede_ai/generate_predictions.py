import sys
import json
import urllib.request
import urllib.error
from collections import defaultdict
from db import get_unresolved_complaints, save_ai_insight

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

def generate_prediction(region_name, count, categories):
    categories_str = ", ".join(set(categories))
    prompt = (
        f"Tu es un expert technique des infrastructures en eau (SONEDE). "
        f"Dans la région de '{region_name}', il y a eu {count} plaintes techniques non résolues "
        f"récemment concernant : {categories_str}. "
        "Génère une alerte très courte (1 à 2 phrases max) pour le tableau de bord technique. "
        "Donne une recommandation d'intervention claire. Réponds directement en français sans introduction."
    )

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        req = urllib.request.Request(
            OLLAMA_GENERATE_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception as e:
        print(f"Erreur avec Ollama pour {region_name}: {e}")
        print("  -> Utilisation du generateur de secours local (Rule-based Fallback)...")
        
        # Rule-based expert system recommendations
        unique_cats = set(categories)
        if "fuite_visible" in unique_cats:
            return f"Alerte : Repetition d'incidents de fuites d'eau a {region_name}. Recommandation : Envoyer une equipe technique inspecter le reseau de distribution principal pour colmater la breche."
        elif "coupure_non_signalee" in unique_cats:
            return f"Alerte : Coupure d'eau generalisee signalee par plusieurs usagers a {region_name}. Recommandation : Envoyer d'urgence un technicien a la station de pompage locale pour diagnostiquer une potentielle panne."
        elif "pression_faible" in unique_cats:
            return f"Alerte : Baisse de pression observee par les citoyens a {region_name}. Recommandation : Ajuster les vannes de regulation et verifier l'etat de la pompe principale."
        elif "qualite_eau" in unique_cats:
            return f"Alerte : Eau insalubre ou malodorante signalee a {region_name}. Recommandation : Purger la canalisation et prelever un echantillon pour analyses de conformite."
        else:
            return f"Alerte : Accumulation de plaintes ({categories_str}) dans la zone de {region_name}. Recommandation : Depecher une equipe d'inspection pour evaluer l'etat des infrastructures locales."

def main():
    print("[IA Predictor] Démarrage de l'analyse des réclamations techniques...")
    complaints = get_unresolved_complaints(days=7)
    
    if not complaints:
        print("Aucune réclamation technique récente trouvée (ou statut est déjà résolu).")
        return

    # Grouper par région (gouvernorat - delegation)
    regions = defaultdict(list)
    for c in complaints:
        g = c.get('gouvernorat', 'Inconnu')
        d = c.get('delegation', 'Inconnu')
        cat = c.get('categorie', 'autre')
        region_key = f"{g} - {d}"
        regions[region_key].append(cat)

    insights_generated = 0
    for region, cats in regions.items():
        if len(cats) >= 2: # Seuil: au moins 2 plaintes pour générer une alerte
            print(f"-> Analyse de la région {region} ({len(cats)} plaintes)...")
            insight = generate_prediction(region, len(cats), cats)
            
            if insight:
                # Déterminer l'urgence basique
                urgence = "Critique" if len(cats) >= 5 else "Élevée"
                
                # Sauvegarder dans MongoDB
                save_ai_insight(region, insight, urgency=urgence)
                print(f"   [OK] Insight généré et sauvegardé (Urgence: {urgence})")
                insights_generated += 1
        else:
            print(f"-> Région {region}: Seulement {len(cats)} plainte(s), ignorée.")

    print(f"[IA Predictor] Terminé. {insights_generated} prédictions générées.")

if __name__ == "__main__":
    main()
