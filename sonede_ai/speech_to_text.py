"""
speech_to_text.py — Transcription audio -> texte, Derja tunisienne (+ code-switching FR/EN).

v2 : N-best rescoring avec intent_detector.
    Vosk ne renvoie pas qu'une seule transcription -- on peut lui demander
    plusieurs hypothèses candidates (SetMaxAlternatives). Jusqu'ici on ne
    gardait que la 1ère (celle jugée la plus probable par le seul modèle
    acoustique+langue de Kaldi). Le problème : ce modèle ne sait rien du
    contexte SONEDE, donc il peut classer en 1ère position une hypothèse
    phonétiquement plausible mais qui ne veut rien dire dans ce domaine,
    alors qu'une hypothèse plus bas dans la liste est un vrai message
    "j'ai une fuite d'eau" reconnaissable par intent_detector.

    On fait donc tourner CHAQUE hypothèse candidate à travers
    intent_detector.detect_intent() (le même code qui route déjà vos
    messages tapés) et on choisit celle qui ressemble le plus à un vrai
    message SONEDE (complaint / faq_question / complaint_tracking /
    greeting / farewell), plutôt que systématiquement la 1ère de Vosk.

    C'est le même principe que le filtrage "off_topic" déjà en place pour
    le texte tapé -- on l'utilise ici en amont, pour AIDER la transcription
    à choisir la bonne hypothèse, pas seulement pour juger le résultat final.

Prérequis :
    pip install vosk librosa numpy soundfile
    (+ le modèle téléchargé et dézippé dans model/vosk-tn, voir le rapport)
"""
import base64
import json
import os
import tempfile

# pyrefly: ignore [missing-import]
import vosk

from dialect_dictionary import analyze_dialect
from intent_detector import detect_intent
from preprocessing import normalize_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOSK_MODEL_PATH = os.path.join(BASE_DIR, 'model', 'vosk-tn')
VOSK_SAMPLE_RATE = 16000  # Vosk attend du PCM 16 bits mono à 16kHz
MAX_ALTERNATIVES = 5      # nombre d'hypothèses candidates demandées à Vosk

# Intents qui indiquent "ce texte a du sens dans le contexte SONEDE" --
# mêmes catégories que celles gérées par dialogue_manager._route_by_intent().
_RELEVANT_INTENTS = {"complaint", "faq_question", "complaint_tracking", "greeting", "farewell"}

vosk.SetLogLevel(-1)  # coupe les logs internes très verbeux de Kaldi

_model = None


def load_model():
    """À appeler une seule fois, au démarrage de l'API (app.py load_models())."""
    global _model
    if _model is not None:
        return _model

    if not os.path.isdir(VOSK_MODEL_PATH):
        print(f"[speech_to_text] Modèle Vosk introuvable dans {VOSK_MODEL_PATH}. "
              f"Voir le rapport pour les instructions de téléchargement.")
        return None

    print(f"[speech_to_text] Chargement du modèle LinTO ASR (Tunisien) depuis {VOSK_MODEL_PATH}...")
    try:
        _model = vosk.Model(VOSK_MODEL_PATH)
        print("[speech_to_text] Modèle Vosk (Derja tunisienne) chargé avec succès.")
    except Exception as e:
        print(f"[speech_to_text] Erreur chargement modèle Vosk: {e}")
        _model = None
    return _model


def is_loaded() -> bool:
    return _model is not None


import av
import io

def _decode_to_pcm16(audio_base64: str) -> bytes:
    """Base64 -> Décodage en mémoire via PyAV (FFmpeg) -> Resampling 16kHz Mono PCM16."""
    audio_data = base64.b64decode(audio_base64)
    input_file = io.BytesIO(audio_data)
    
    # Ouvrir le fichier audio en mémoire
    container = av.open(input_file)
    
    audio_streams = [s for s in container.streams if s.type == 'audio']
    if not audio_streams:
        container.close()
        raise ValueError("Aucun flux audio trouvé dans le fichier reçu.")
    audio_stream = audio_streams[0]
    
    # Configurer le rééchantillonneur vers 16kHz Mono PCM 16-bit
    resampler = av.AudioResampler(
        format='s16',     # Signed 16-bit
        layout='mono',    # 1 canal (mono)
        rate=VOSK_SAMPLE_RATE # 16kHz
    )
    
    pcm_bytes = bytearray()
    for packet in container.demux(audio_stream):
        try:
            for frame in packet.decode():
                resampled_frames = resampler.resample(frame)
                for rf in resampled_frames:
                    pcm_bytes.extend(rf.to_ndarray().tobytes())
        except av.error.InvalidDataError:
            # Ignorer les paquets invalides et continuer le décodage du reste
            continue
        except Exception as e:
            print(f"[speech_to_text] Avertissement décodage packet: {e}")
            continue

    # Flush du resampler pour récupérer les dernières frames
    try:
        for rf in resampler.resample(None):
            pcm_bytes.extend(rf.to_ndarray().tobytes())
    except Exception as e:
        print(f"[speech_to_text] Avertissement flush resampler: {e}")
        
    container.close()
    return bytes(pcm_bytes)


def _score_candidate(raw_text: str, rank: int) -> tuple:
    """
    Score une hypothèse candidate en réutilisant le pipeline texte existant.

    Retourne (score, intent, intent_confidence) -- plus le score est haut,
    plus cette hypothèse ressemble à un vrai message SONEDE.
    """
    clean = normalize_text(raw_text)          # Arabizi + alias Derja -> forme canonique
    if not clean:
        return (-1.0, "unclear", 0.0)

    intent_result = detect_intent(clean)
    intent = intent_result["intent"]
    intent_confidence = intent_result["confidence"]

    # Base : confiance de l'intent si l'intent est pertinent pour SONEDE,
    # pénalité sinon (off_topic / unclear) -- même logique que
    # dialogue_manager._route_by_intent(), réutilisée ici pour CHOISIR
    # la transcription plutôt que pour y répondre.
    score = intent_confidence if intent in _RELEVANT_INTENTS else -0.4

    # Petit bonus si le dictionnaire Derja reconnaît du vocabulaire
    # SONEDE dans le texte (fuite, coupure, compteur...) -- signal
    # indépendant de intent_detector, donc complémentaire.
    dialect_info = analyze_dialect(clean)
    if dialect_info.get("category_hints"):
        score += 0.15
    if dialect_info.get("matches"):
        score += 0.05 * min(len(dialect_info["matches"]), 3)

    # Léger a priori en faveur du rang Vosk d'origine : à score presque
    # égal, on fait confiance au modèle acoustique plutôt qu'à un
    # classement arbitraire. Évite de préférer une hypothèse bas-classée
    # sur un score d'intent quasi identique.
    score += max(0, (MAX_ALTERNATIVES - rank)) * 0.02

    return (score, intent, intent_confidence)


def transcribe(audio_base64: str) -> str:
    """
    Decode l'audio, obtient plusieurs hypothèses de transcription de Vosk,
    et choisit celle qui a le plus de sens dans le contexte SONEDE grâce à
    intent_detector + dialect_dictionary (déjà utilisés pour le texte tapé).
    """
    if _model is None:
        print("[speech_to_text] Modèle non initialisé (load_model() manquant ou échoué).")
        return ""
    if not audio_base64:
        return ""

    try:
        pcm16 = _decode_to_pcm16(audio_base64)

        recognizer = vosk.KaldiRecognizer(_model, VOSK_SAMPLE_RATE)
        recognizer.SetMaxAlternatives(MAX_ALTERNATIVES)
        recognizer.SetWords(True)
        recognizer.AcceptWaveform(pcm16)
        result = json.loads(recognizer.FinalResult())

        # Selon la config du modèle/version de Vosk, le résultat est soit
        # {"alternatives": [...]} (mode multi-hypothèses), soit un simple
        # {"text": "..."} (fallback si le modèle ne supporte pas les
        # alternatives) -- on gère les deux formes.
        alternatives = result.get("alternatives")
        if not alternatives:
            alternatives = [{"text": result.get("text", "")}]

        candidates = []
        for rank, alt in enumerate(alternatives):
            raw_text = (alt.get("text") or "").strip()
            if not raw_text:
                continue
            score, intent, intent_conf = _score_candidate(raw_text, rank)
            candidates.append((score, raw_text, intent, intent_conf, rank))

        if not candidates:
            print("[speech_to_text] Aucune hypothèse exploitable renvoyée par Vosk.")
            return ""

        candidates.sort(key=lambda c: c[0], reverse=True)
        best_score, best_text, best_intent, best_conf, best_rank = candidates[0]

        print(
            f"[speech_to_text] Choisi: \"{best_text}\" "
            f"(rang Vosk d'origine={best_rank}, intent={best_intent}, "
            f"conf_intent={best_conf:.2f}, score_final={best_score:.2f}, "
            f"{len(candidates)} hypothèses évaluées)"
        )

        return best_text

    except Exception as e:
        print(f"[speech_to_text] Erreur pendant la transcription: {e}")
        return ""