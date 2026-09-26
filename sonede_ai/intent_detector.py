"""
Intent Detection for the SONEDE chatbot.

Classifies user messages into intents BEFORE the dialogue manager decides
what to do. This enables the bot to respond naturally to greetings,
answer FAQ questions, route complaints, and politely redirect off-topic
messages.

Intents:
    greeting           – "hello", "bonjour", "مرحبا", "ahla"
    farewell           – "bye", "merci", "شكرا", "bslama"
    faq_question       – "how to pay?", "c'est quoi SONEDE?", "كيفاش نخلص؟"
    complaint          – "no water", "fuite", "الماء مقطوع"
    complaint_tracking – "PL-ABC123", "where's my ticket?"
    off_topic          – "what's the weather?", "tell me a joke"
    unclear            – ambiguous / too short to classify

Uses a fast keyword-first approach, then semantic similarity as fallback.
"""
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Greeting & Farewell patterns (multilingual)
# ---------------------------------------------------------------------------

_GREETING_PATTERNS = {
    # French
    "bonjour", "bonsoir", "salut", "coucou", "hello", "hi", "hey",
    "bsr", "bjr", "slt","slm",
    # Arabic
    "مرحبا", "مرحبة", "السلام", "السلام عليكم", "سلام", "اهلا", "أهلا",
    "صباح الخير", "مساء الخير",
    # Tunisian Derja (Latin)
    "ahla", "aslema", "slem", "slam", "ya3tik essa7a",
    # Tunisian Derja (Arabic)
    "أهلا", "عسلامة", "يعطيك الصحة",
    # English
    "good morning", "good evening", "good afternoon", "greetings",
}

_FAREWELL_PATTERNS = {
    # French
    "au revoir", "merci", "bonne journée", "bonne soirée", "à bientôt",
    "adieu", "ciao",
    # Arabic
    "شكرا", "مع السلامة", "بالسلامة", "الله يسلمك", "الله يعطيك",
    # Tunisian Derja (Latin)
    "bslama", "sahit", "teslam", "merci barcha", "yatik essa7a",
    "beslama", "bislama",
    # Tunisian Derja (Arabic)
    "بسلامة", "صحيت", "بارك الله فيك",
    # English
    "bye", "goodbye", "thanks", "thank you", "see you", "take care",
}

# Simple greeting words that might appear as part of a longer message
_GREETING_WORDS = {
    "bonjour", "bonsoir", "salut", "hello", "hi", "hey", "salam",
    "مرحبا", "سلام", "اهلا", "أهلا", "ahla", "aslema", "slem",
}

_FAREWELL_WORDS = {
    "merci", "شكرا", "bye", "thanks", "bslama", "بسلامة", "sahit",
    "ciao", "goodbye",
}

# ---------------------------------------------------------------------------
# Complaint tracking pattern (PL-XXXXXXXX)
# ---------------------------------------------------------------------------

_COMPLAINT_ID_RE = re.compile(r'PL-[A-Z0-9]{6,10}', re.IGNORECASE)

_TRACKING_KEYWORDS = {
    # French
    "suivi", "suivre", "statut", "état", "etat", "avancement", "réclamation",
    "ticket", "numéro", "numero",
    # Arabic
    "متابعة", "حالة", "شكوى", "رقم", "تتبع",
    # Tunisian Derja
    "winek", "winha", "chsayer", "وينها", "شصاير",
    # English
    "track", "tracking", "status", "follow", "where",
}

# ---------------------------------------------------------------------------
# Complaint-related keywords (signals user wants to file a complaint)
# ---------------------------------------------------------------------------

_COMPLAINT_KEYWORDS = {
    # French
    "problème", "probleme", "panne", "fuite", "coupure", "coupé",
    "pas d'eau", "eau coupée", "sans eau", "pression", "faible",
    "qualité", "trouble", "couleur", "odeur", "facture", "surfacturation",
    "compteur", "retard", "intervention", "urgence", "urgent",
    "cassé", "cassée", "broken", "signaler", "réclamation", "plainte",
    "rue", "route",
    # Arabic
    "مشكلة", "عطب", "تسرب", "انقطاع", "مقطوع", "ضغط", "ضعيف",
    "جودة", "عكر", "لون", "رائحة", "فاتورة", "عداد", "تأخر",
    "طوارئ", "كسر", "إبلاغ", "شكوى", "مقصوص", "قصو", "مفيش", "ماء", "الماء",
    "شارع", "الشارع", "كياس", "الكياس", "سيلان", "يجري", "خارج", "يضيع",
    # Tunisian Derja (Latin)
    "mochkla", "moshkla", "mochkil", "panna", "tsarrub", "ma3andich",
    "9at3a", "dh3if", "m3aker", "khayba", "ma9sous", "mgassos",
    "sabala", "sabbela", "kayes", "kayess", "chera3", "fuit", "mksar",
    "taksir", "takssir", "ri7tou", "me", "miel", "cheraa", "yijri", "ydhi3",
    # Tunisian Derja (Arabic)
    "مشكل", "ماعنديش", "قاطعة", "ضعيف", "معكر", "خايبة", "مقصوص", "ريحتو",
    "كياس", "شارع", "يجري", "يضيع", "خارج", "ماء",
    # English
    "problem", "issue", "leak", "cut", "no water", "pressure",
    "quality", "bill", "meter", "delay", "emergency", "report",
    "complaint", "street", "road",
}

# ---------------------------------------------------------------------------
# FAQ signal keywords (user is asking a question, not filing a complaint)
# ---------------------------------------------------------------------------

_FAQ_QUESTION_WORDS = {
    # French
    "comment", "quand", "où", "combien", "quel", "quelle", "quels",
    "quelles", "est-ce", "pourquoi", "c'est quoi", "qu'est-ce",
    "horaire", "horaires", "payer", "paiement", "abonnement",
    "raccordement", "branchement", "tarif", "prix", "contact",
    "téléphone", "adresse", "agence", "numéro vert",
    # Arabic
    "كيف", "كيفاش", "متى", "وين", "أين", "كم", "شنو", "شنوة",
    "ما هو", "ما هي", "لماذا", "علاش", "وقتاش",
    "ساعات", "دفع", "خلاص", "اشتراك", "ربط", "تعريفة", "ثمن",
    "اتصال", "هاتف", "عنوان", "وكالة", "رقم أخضر",
    # Tunisian Derja (Latin)
    "kifech", "chneya", "wa9tech", "9addech", "win", "3lech",
    "sa3at", "5aless", "abonnement", "raccordement",
    # English
    "how", "when", "where", "what", "which", "why", "who",
    "hours", "pay", "payment", "subscription", "connection",
    "tariff", "price", "contact", "phone", "address", "agency",
}

# Question mark patterns
_QUESTION_RE = re.compile(r'[?؟]')


def detect_intent(message: str, session_state: str = None) -> dict:
    """
    Detect the user's intent from their message.

    Parameters
    ----------
    message : str
        The user's raw message text.
    session_state : str, optional
        Current dialogue state (e.g., 'CONFIRM_SUMMARY'). If the user is
        mid-flow in the complaint state machine, we respect that context.

    Returns
    -------
    dict
        {
            "intent": str,          # greeting | farewell | faq_question |
                                    # complaint | complaint_tracking |
                                    # off_topic | unclear
            "confidence": float,    # 0.0 to 1.0
            "complaint_id": str,    # only if intent == complaint_tracking
            "details": dict,        # debug info (keyword hits, etc.)
        }
    """
    if not message or not message.strip():
        return _result("unclear", 0.0)

    text = message.strip()
    text_lower = text.lower()
    # \w+ natively supports French accents, Arabic characters, and numbers (for Derja like mta3)
    tokens = set(re.findall(r"\w+", text_lower))

    # If user is in the middle of a complaint flow (answering yes/no, etc.),
    # keep them in the complaint intent to not break the state machine
    if session_state in ("CLARIFY_CATEGORY", "CONFIRM_DUPLICATE",
                         "CONFIRM_SUMMARY"):
        return _result("complaint", 0.95, details={
            "reason": "mid_flow_context",
            "session_state": session_state,
        })

    # ── 1. Complaint tracking (highest priority — specific pattern) ──
    id_match = _COMPLAINT_ID_RE.search(text)
    if id_match:
        return _result("complaint_tracking", 0.99, complaint_id=id_match.group())

    tracking_hits = len(tokens & _TRACKING_KEYWORDS)
    if tracking_hits >= 2 and _COMPLAINT_ID_RE.search(text):
        return _result("complaint_tracking", 0.95, complaint_id=id_match.group())

    # ── 2. Pure greeting (short message, just a greeting) ──
    if _is_pure_greeting(text_lower, tokens):
        return _result("greeting", 0.95, details={"reason": "pure_greeting"})

    # ── 3. Pure farewell ──
    if _is_pure_farewell(text_lower, tokens):
        return _result("farewell", 0.95, details={"reason": "pure_farewell"})

    # ── 4. Score-based classification ──
    complaint_score = _score_complaint(text_lower, tokens)
    faq_score = _score_faq(text_lower, tokens)
    greeting_score = _score_greeting(tokens)
    farewell_score = _score_farewell(tokens)
    tracking_score = _score_tracking(text_lower, tokens)

    scores = {
        "complaint": complaint_score,
        "faq_question": faq_score,
        "greeting": greeting_score,
        "farewell": farewell_score,
        "complaint_tracking": tracking_score,
    }

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    # If nothing scores above threshold, it's either off_topic or unclear
    if best_score < 0.2:
        # Very short messages with no recognizable keywords
        if len(tokens) <= 2:
            return _result("unclear", 0.3, details={"scores": scores})
        return _result("off_topic", 0.4, details={"scores": scores})

    # If greeting/farewell appears alongside other intents, prefer the other
    if best_intent in ("greeting", "farewell") and best_score < 0.5:
        other_scores = {k: v for k, v in scores.items()
                        if k not in ("greeting", "farewell")}
        if other_scores:
            alt_intent = max(other_scores, key=other_scores.get)
            alt_score = other_scores[alt_intent]
            if alt_score > 0.15:
                return _result(alt_intent, alt_score, details={"scores": scores})

    return _result(best_intent, best_score, details={"scores": scores})


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def _is_pure_greeting(text_lower: str, tokens: set) -> bool:
    """Check if the message is purely a greeting (nothing else substantial)."""
    # Exact match against known greeting phrases
    stripped = text_lower.strip("!. ")
    if stripped in _GREETING_PATTERNS:
        return True
    # Short message (1-3 tokens) with a greeting word
    if len(tokens) <= 3 and tokens & _GREETING_WORDS:
        return True
    return False


def _is_pure_farewell(text_lower: str, tokens: set) -> bool:
    """Check if the message is purely a farewell."""
    stripped = text_lower.strip("!. ")
    if stripped in _FAREWELL_PATTERNS:
        return True
    if len(tokens) <= 3 and tokens & _FAREWELL_WORDS:
        return True
    return False


def _score_greeting(tokens: set) -> float:
    hits = len(tokens & _GREETING_WORDS)
    if hits == 0:
        return 0.0
    return min(0.3 + hits * 0.2, 0.8)


def _score_farewell(tokens: set) -> float:
    hits = len(tokens & _FAREWELL_WORDS)
    if hits == 0:
        return 0.0
    return min(0.3 + hits * 0.2, 0.8)


def _score_complaint(text_lower: str, tokens: set) -> float:
    """Score how likely the message is a complaint."""
    hits = len(tokens & _COMPLAINT_KEYWORDS)
    if hits == 0:
        return 0.0
    # More complaint keywords = higher confidence
    score = min(0.3 + hits * 0.15, 0.95)
    return score


def _score_faq(text_lower: str, tokens: set) -> float:
    """Score how likely the message is an FAQ question."""
    hits = len(tokens & _FAQ_QUESTION_WORDS)
    has_question_mark = bool(_QUESTION_RE.search(text_lower))

    if hits == 0 and not has_question_mark:
        return 0.0

    score = 0.0
    if has_question_mark:
        score += 0.25
    # Increased from 0.15 so a single question word passes the 0.2 threshold
    score += hits * 0.25
    return min(score, 0.9)


def _score_tracking(text_lower: str, tokens: set) -> float:
    """Score how likely the message is about tracking a complaint."""
    strong_tracking = {"suivi", "statut", "état", "etat", "status", "tracking", "متابعة", "حالة", "تتبع", "winek", "winha", "chsayer"}
    
    hits = len(tokens & _TRACKING_KEYWORDS)
    strong_hits = len(tokens & strong_tracking)
    has_id = bool(_COMPLAINT_ID_RE.search(text_lower))

    if has_id:
        return 0.95
    if hits == 0:
        return 0.0
    
    # Boost the score significantly if they use a strong tracking word (like "état", "status")
    return min(0.2 + hits * 0.15 + strong_hits * 0.2, 0.85)


# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------

def _result(intent: str, confidence: float, complaint_id: str = None,
            details: dict = None) -> dict:
    res = {
        "intent": intent,
        "confidence": round(confidence, 3),
    }
    if complaint_id:
        res["complaint_id"] = complaint_id
    if details:
        res["details"] = details
    return res
