"""
text_to_speech.py — Synthèse vocale (Text-to-Speech) pour l'assistant vocal SONEDE.

Moteur principal : edge-tts (Microsoft Edge TTS) — rapide, voix naturelles.

Prérequis :
    pip install edge-tts
"""
from __future__ import annotations

import asyncio
import base64
import logging
import io

try:
    import edge_tts
    _tts_available = True
except ImportError:
    _tts_available = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language mapping — maps internal lang codes to edge-tts voice codes
# ---------------------------------------------------------------------------
# 'ar-TN-BahaNeural' (Male) and 'ar-TN-ReemNeural' (Female) are Tunisian voices!
_LANG_MAP: dict[str, str] = {
    "fr": "fr-FR-DeniseNeural",
    "ar": "ar-TN-BahaNeural",
    "tn_arabe": "ar-TN-ReemNeural",      
    "tn_latin": "fr-FR-DeniseNeural",      
    "en": "en-US-AriaNeural",
}


def is_available() -> bool:
    """Indique si la synthèse vocale est fonctionnelle."""
    return _tts_available

async def _synthesize_async(text: str, lang: str) -> bytes:
    if not _tts_available:
        return b""
        
    voice = _LANG_MAP.get(lang, "fr-FR-DeniseNeural")
    try:
        # Increase speed to make it feel more conversational and less sluggish
        communicate = edge_tts.Communicate(text, voice, rate="+15%")
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        logger.info(
            f"[text_to_speech] Synthèse edge-tts OK — {len(audio_data)} octets, "
            f"voix={voice}, texte={text[:60]}..."
        )
        return audio_data
    except Exception as e:
        logger.error(f"[text_to_speech] Erreur synthèse edge-tts: {e}")
        return b""

def synthesize(text: str, lang: str = "fr") -> bytes:
    """
    Convertit du texte en audio MP3 en bloquant (sync).
    """
    if not text or not text.strip():
        return b""
    
    return asyncio.run(_synthesize_async(text, lang))

def synthesize_to_base64(text: str, lang: str = "fr") -> str:
    """
    Même chose que synthesize() mais retourne l'audio encodé en base64
    (prêt à être injecté dans une réponse JSON).
    """
    mp3_bytes = synthesize(text, lang)
    if not mp3_bytes:
        return ""
    return base64.b64encode(mp3_bytes).decode("ascii")
