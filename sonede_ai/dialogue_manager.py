"""
Gestionnaire de dialogue pour le chatbot SONEDE.
v4 : Intent-first routing — the bot understands what the user wants BEFORE
     entering any state machine. Supports greetings, FAQ questions, complaints,
     complaint tracking, and politely redirects off-topic messages.
"""
import random
import uuid

import classifier
import db
import duplicate_checker
import vision_processor
from dialect_dictionary import analyze_dialect
from intent_detector import detect_intent
from knowledge_base import rag
from language_detector import detect_language
from location_extractor import extract_location
import learning

# ---------------------------------------------------------------------------
# State constants (complaint flow — preserved from v3)
# ---------------------------------------------------------------------------
STATE_INIT = "INIT"
STATE_ASK_PROBLEM = "ASK_PROBLEM"
STATE_CLARIFY_CATEGORY = "CLARIFY_CATEGORY"
STATE_CONFIRM_DUPLICATE = "CONFIRM_DUPLICATE"
STATE_CONFIRM_SUMMARY = "CONFIRM_SUMMARY"
STATE_ASK_LOCATION = "ASK_LOCATION"
STATE_ASK_IMAGE = "ASK_IMAGE"
STATE_DONE = "DONE"

# New states for the smart conversation
STATE_CONVERSATION = "CONVERSATION"  # Free conversation (greetings, FAQ, etc.)

_YES_WORDS = {
    "oui", "yes", "ok", "d'accord", "daccord", "behi", "eyy", "yeah",
    "نعم", "ايه", "أيه", "أكيد", "akid", "اي", "أي", "ay",
}
_NO_WORDS = {
    "non", "no", "nn", "la", "l'a", "لا", "ماشي", "mashi", "machi", "mch",
}

_CATEGORY_LABELS = {
    "coupure_non_signalee": {"fr": "coupure d'eau non signalée", "ar": "انقطاع مياه غير معلن", "en": "unreported water cut"},
    "coupure_planifiee": {"fr": "coupure d'eau planifiée", "ar": "انقطاع مياه مبرمج", "en": "planned water cut"},
    "pression_faible": {"fr": "pression d'eau faible", "ar": "ضعف الضغط", "en": "low water pressure"},
    "qualite_eau": {"fr": "qualité de l'eau", "ar": "جودة المياه", "en": "water quality issue"},
    "fuite_visible": {"fr": "fuite d'eau visible", "ar": "تسرب ظاهر للمياه", "en": "visible leak"},
    "panne_pompage": {"fr": "panne de pompage", "ar": "عطب في محطة الضخ", "en": "pumping station failure"},
    "facturation": {"fr": "litige de facturation", "ar": "خلاف حول الفاتورة", "en": "billing dispute"},
    "retard_intervention": {"fr": "retard d'intervention", "ar": "تأخر في التدخل", "en": "delayed intervention"},
    "felicitation": {"fr": "retour positif", "ar": "ملاحظة إيجابية", "en": "positive feedback"},
    "suggestion": {"fr": "suggestion", "ar": "اقتراح", "en": "suggestion"},
}

_STATUS_LABELS = {
    "nouveau": {"fr": "nouvelle", "ar": "جديدة", "en": "new"},
    "en_cours": {"fr": "en cours", "ar": "قيد المعالجة", "en": "in progress"},
    "resolu": {"fr": "résolue", "ar": "تم حلها", "en": "resolved"},
    "rejete": {"fr": "rejetée", "ar": "مرفوضة", "en": "rejected"},
}

_URGENCY_LABELS = {
    "critique": {"fr": "critique", "ar": "حرجة", "en": "critical"},
    "haute": {"fr": "haute", "ar": "عالية", "en": "high"},
    "moyenne": {"fr": "moyenne", "ar": "متوسطة", "en": "medium"},
    "faible": {"fr": "faible", "ar": "منخفضة", "en": "low"},
}


def _lang_bucket(lang: str) -> str:
    if lang in ("ar", "tn_arabe"):
        return "ar"
    if lang == "en":
        return "en"
    return "fr"


def _category_label(categorie: str, lang: str) -> str:
    return _CATEGORY_LABELS.get(categorie, {}).get(_lang_bucket(lang), categorie)


def _status_label(statut: str, lang: str) -> str:
    return _STATUS_LABELS.get(statut, {}).get(_lang_bucket(lang), statut)


def _urgency_label(urgence: str, lang: str) -> str:
    return _URGENCY_LABELS.get(urgence, {}).get(_lang_bucket(lang), urgence)


# ---------------------------------------------------------------------------
# Natural, human-like response templates (varied to avoid robotic feel)
# ---------------------------------------------------------------------------

_GREETINGS = {
    "fr": [
        "Bonjour ! 😊 Je suis l'assistant SONEDE. Comment puis-je vous aider aujourd'hui ?",
        "Bonjour et bienvenue ! Je suis là pour répondre à vos questions sur les services SONEDE. Que puis-je faire pour vous ?",
        "Salut ! 👋 Comment puis-je vous aider avec vos services d'eau ?",
    ],
    "ar": [
        "مرحبا! 😊 أنا مساعد الصوندة. كيف يمكنني مساعدتك اليوم؟",
        "أهلا وسهلا! أنا هنا للإجابة عن أسئلتك حول خدمات الصوندة. بماذا أستطيع خدمتك؟",
        "مرحبا بك! 👋 كيف أقدر نعاونك بخصوص خدمات الماء؟",
    ],
    "en": [
        "Hello! 😊 I'm the SONEDE assistant. How can I help you today?",
        "Hi there! Welcome! I'm here to help with any SONEDE water service questions. What can I do for you?",
        "Hello and welcome! 👋 How can I assist you with your water services?",
    ],
}

_FAREWELLS = {
    "fr": [
        "Au revoir ! N'hésitez pas à revenir si vous avez d'autres questions. 😊",
        "Merci pour votre visite ! Bonne journée et à bientôt. 👋",
        "À bientôt ! Je suis toujours là si vous avez besoin d'aide.",
    ],
    "ar": [
        "مع السلامة! ما تترددش ترجعلنا إذا عندك أسئلة أخرى. 😊",
        "شكرا على زيارتك! نهارك سعيد. 👋",
        "بالسلامة! أنا ديما هنا إذا تحتاج مساعدة.",
    ],
    "en": [
        "Goodbye! Don't hesitate to come back if you have more questions. 😊",
        "Thanks for reaching out! Have a great day. 👋",
        "See you! I'm always here if you need help.",
    ],
}

_OFF_TOPIC = {
    "fr": [
        "Je suis spécialisé dans les services SONEDE (eau potable en Tunisie). Je peux vous aider avec :\n• Les factures et paiements\n• Les problèmes d'eau (coupure, fuite, pression, qualité)\n• Les nouveaux branchements\n• Le suivi de réclamations\n\nComment puis-je vous aider ?",
    ],
    "ar": [
        "أنا متخصص في خدمات الصوندة (الماء الصالح للشرب في تونس). نقدر نعاونك في:\n• الفواتير والخلاص\n• مشاكل الماء (انقطاع، تسرب، ضغط، جودة)\n• الربط الجديد\n• متابعة الشكاوى\n\nكيف نقدر نعاونك؟",
    ],
    "en": [
        "I specialize in SONEDE services (drinking water in Tunisia). I can help you with:\n• Bills and payments\n• Water issues (cuts, leaks, pressure, quality)\n• New connections\n• Complaint tracking\n\nHow can I help you?",
    ],
}

_UNCLEAR = {
    "fr": [
        "Je n'ai pas bien compris votre message. Pourriez-vous reformuler ? Par exemple :\n• Posez une question sur les services SONEDE\n• Décrivez un problème d'eau\n• Donnez votre numéro de réclamation (PL-XXXXXXXX) pour le suivi",
    ],
    "ar": [
        "ما فهمتش مليح رسالتك. تنجم تعاود تكتبها؟ مثلا:\n• اطرح سؤال على خدمات الصوندة\n• وصف مشكلة في الماء\n• أعطيني رقم الشكوى (PL-XXXXXXXX) باش نتبع فيها",
    ],
    "en": [
        "I didn't quite understand your message. Could you rephrase it? For example:\n• Ask a question about SONEDE services\n• Describe a water problem\n• Give me your complaint number (PL-XXXXXXXX) to track it",
    ],
}

_FAQ_ANSWER_PREFIX = {
    "fr": "",
    "ar": "",
    "en": "",
}

_FAQ_NOT_FOUND = {
    "fr": "Je n'ai malheureusement pas trouvé de réponse précise à votre question. Vous pouvez :\n• Reformuler votre question\n• Contacter le numéro vert SONEDE : 80 100 319\n• Vous rendre à votre agence locale\n\nOu si vous avez un problème à signaler, décrivez-le et je vous aiderai à déposer une réclamation.",
    "ar": "للأسف ما لقيت جواب دقيق لسؤالك. تنجم:\n• تعاود تصوغ السؤال\n• تتصل بالرقم الأخضر: 80 100 319\n• تمشي للوكالة المحلية\n\nولا إذا عندك مشكل تحب تبلغ عليه، وصفلي وأنا نعاونك.",
    "en": "I'm sorry, I couldn't find a precise answer to your question. You can:\n• Rephrase your question\n• Call the SONEDE toll-free number: 80 100 319\n• Visit your local agency\n\nOr if you have an issue to report, describe it and I'll help you file a complaint.",
}

_COMPLAINT_TRACKING_NOT_FOUND = {
    "fr": "Je n'ai pas trouvé de réclamation avec le numéro {id}. Vérifiez le numéro (format PL-XXXXXXXX) et réessayez, ou contactez votre agence SONEDE locale.",
    "ar": "ما لقيت شكوى بالرقم {id}. تحقق من الرقم (صيغة PL-XXXXXXXX) وأعد المحاولة، أو اتصل بوكالة الصوندة المحلية.",
    "en": "I couldn't find a complaint with ID {id}. Please check the number (format PL-XXXXXXXX) and try again, or contact your local SONEDE agency.",
}

_COMPLAINT_TRACKING_FOUND = {
    "fr": "Voici les informations sur votre réclamation {id} :\n• Catégorie : {categorie}\n• Statut : {statut}\n• Date de signalement : {date}\n• Urgence : {urgence}\n\nSi vous avez d'autres questions, n'hésitez pas !",
    "ar": "هاذي معلومات شكواك {id}:\n• الصنف: {categorie}\n• الحالة: {statut}\n• تاريخ الإبلاغ: {date}\n• الاستعجال: {urgence}\n\nإذا عندك أسئلة أخرى، ما تترددش!",
    "en": "Here's the info on your complaint {id}:\n• Category: {categorie}\n• Status: {statut}\n• Reported: {date}\n• Urgency: {urgence}\n\nFeel free to ask if you have more questions!",
}

_ASK_PROBLEM = {
    "fr": "D'accord, je vais vous aider à signaler un problème. Pouvez-vous me décrire ce qui se passe ? (Vous pouvez aussi envoyer une photo).",
    "ar": "تو نعاونك تبلغ عن المشكل. وصفلي شنو صاير؟ (تنجم تبعثلي تصويرة زادة).",
    "en": "I'll help you report an issue. Can you describe what's happening? (You can also send a photo).",
}

# Complaint flow templates (preserved from v3)
_TEXTS = {
    "ask_location": {
        "fr": "Pourriez-vous m'indiquer l'endroit exact du problème ? (Vous pouvez utiliser le bouton GPS ou taper l'adresse).",
        "ar": "بربي نجمت تعطيني البلاصة بالضبط؟ (تنجم تستعمل زر الـ GPS ولا تكتب العنوان).",
        "tn_arabe": "وين بالضبط المشكلة هاذي؟ (تنجم تبعث الـ GPS متاعك ولا تكتب العنوان).",
        "tn_latin": "Win bedhabt el mochkla hethi? (tnajem tab3ath el GPS wala tekteb l'adresse).",
        "en": "Could you please provide the exact location? (You can use the GPS button or type the address).",
    },
    "ask_image": {
        "fr": "Merci. Avez-vous une photo du problème pour aider nos techniciens ? (Vous pouvez envoyer une image ou répondre 'non').",
        "ar": "شكرا. عندك تصويرة للمشكل باش تعاون الفنيين؟ (تنجم تبعث تصويرة ولا تجاوب بـ 'لا').",
        "tn_arabe": "عيشك. عندك تصويرة للمشكلة باش تعاونا؟ (تنجم تبعث تصويرة ولا تجاوب بـ 'لا').",
        "tn_latin": "3aychek. 3andek taswira lel mochkla bech t3awenna? (tnajem tab3ath taswira wala tjaweb b 'la').",
        "en": "Thank you. Do you have a photo of the issue to help our technicians? (You can send an image or answer 'no').",
    },
    "already_in_progress": {
        "fr": "Votre réclamation est déjà en cours de traitement (ticket {id_plainte}). Nos équipes s'en occupent ! 😊",
        "ar": "شكواك قيد المعالجة حاليا (رقم {id_plainte}). فرقنا تتكفل بها! 😊",
        "tn_arabe": "شكوتك ديجا قاعدين نخدمو عليها (رقم {id_plainte}). الفريق متاعنا لاهي بيها! 😊",
        "tn_latin": "Chakwtek deja 9a3din nekhdmou 3liha (ticket {id_plainte}). L'équipe mte3na lehya biha! 😊",
        "en": "Your complaint is already in progress (ticket {id_plainte}). Our teams are on it! 😊",
    },
    "greet_ask_problem": {
        "fr": "Bonjour, je suis l'assistant SONEDE. Quel est votre problème ? (Vous pouvez aussi envoyer une photo de la fuite ou du compteur).",
        "ar": "مرحبا، أنا مساعد الصوندة. ما هي مشكلتك؟ (يمكنك أيضا إرسال صورة للتسرب أو العداد).",
        "tn_arabe": "أهلا، أنا مساعد الصوندة. شنية المشكلة؟ (تنجم تبعثلي تصويرة زادة).",
        "tn_latin": "Ahla, ena l'assistant mte3 SONEDE. Chneya el mochkla? (tnajem tab3athli taswira zada).",
        "en": "Hello, I'm the SONEDE assistant. What's the issue? (You can also send a photo).",
    },
    "clarify_category": {
        "fr": "Je ne suis pas totalement sûr de la catégorie. Pouvez-vous préciser (ex: fuite, coupure, qualité, facturation) ?",
        "ar": "لست متأكدا من نوع المشكلة. هل يمكن التوضيح أكثر؟",
        "tn_arabe": "موش متأكد برشة من نوع المشكل. تنجم توضح أكثر؟",
        "tn_latin": "Mouch mota2akked barcha 3ala naw3 el moshkil. Tnajem twadeh aktar?",
        "en": "I'm not fully sure of the category. Could you clarify?",
    },
    "duplicate_found": {
        "fr": "Une réclamation pour {categorie} est déjà ouverte dans votre zone (ticket {id_plainte}). Voulez-vous quand même signaler ? (oui/non)",
        "ar": "توجد شكوى بخصوص {categorie} في منطقتكم ({id_plainte}). هل تريد الاستمرار؟ (نعم/لا)",
        "tn_arabe": "كاين شكوى مفتوحة على {categorie} بحذاكم ({id_plainte}). تحب تكمل؟ (اي/لا)",
        "tn_latin": "Fama chakwa mawjouda 3ala {categorie} bahdhekum ({id_plainte}). T7eb tkammel? (ewa/la)",
        "en": "A ticket for {categorie} is already open near you ({id_plainte}). Still want to report? (yes/no)",
    },
    "attached_to_existing": {
        "fr": "Très bien, votre situation est suivie via le ticket {id_plainte}.",
        "ar": "جيد، وضعيتكم متابعة عبر الشكوى {id_plainte}.",
        "tn_arabe": "طيب، الوضعية متابعة بالشكوى {id_plainte}.",
        "tn_latin": "Behi, el wad3iya metab3a bel chakwa {id_plainte}.",
        "en": "Understood, tracking via ticket {id_plainte}.",
    },
    "confirm_summary": {
        "fr": "Récapitulatif : {categorie} ({urgence}){location_info}. Je confirme ? (oui/non)",
        "ar": "ملخص: {categorie} ({urgence}){location_info}. هل أؤكد؟ (نعم/لا)",
        "tn_arabe": "ملخص: {categorie} ({urgence}){location_info}. نأكد؟ (اي/لا)",
        "tn_latin": "Récap: {categorie} ({urgence}){location_info}. Na confirmi? (ewa/la)",
        "en": "Summary: {categorie} ({urgence}){location_info}. Confirm? (yes/no)",
    },
    "saved": {
        "fr": "Enregistré (ticket {id_plainte}). Suivez-le dans l'app. 👍",
        "ar": "تم التسجيل ({id_plainte}). تابعه في التطبيق. 👍",
        "tn_arabe": "تسجلت ({id_plainte}). تنجم تتابعها. 👍",
        "tn_latin": "Etsajjlet ({id_plainte}). Tnajem tetba3ha. 👍",
        "en": "Saved ({id_plainte}). Track it in the app. 👍",
    },
    "cancelled": {
        "fr": "Annulé. N'hésitez pas à me poser d'autres questions ou à recommencer quand vous voulez. 😊",
        "ar": "ألغيت. ما تترددش تسألني أي سؤال آخر أو تبدا من جديد. 😊",
        "tn_arabe": "ألغيت. ابدا من جديد وقتلي تحب. 😊",
        "tn_latin": "Annulé. Ebda men jdid wa9t ma t7eb. 😊",
        "en": "Cancelled. Feel free to ask other questions or start over anytime. 😊",
    },
    "need_yes_no": {
        "fr": "Veuillez répondre par oui ou non.",
        "ar": "الرجاء الإجابة بنعم أو لا.",
        "tn_arabe": "جاوب بـ اي ولا لا.",
        "tn_latin": "Jaweb b eyy wala la.",
        "en": "Please answer yes or no.",
    },
}


def _t(key: str, lang: str, **kwargs) -> str:
    templates = _TEXTS[key]
    lang = lang if lang in templates else "fr"
    return templates[lang].format(**kwargs)


def _pick_response(templates: dict, lang: str) -> str:
    """Pick a random response from the templates for the given language."""
    bucket = _lang_bucket(lang)
    options = templates.get(bucket, templates.get("fr", [""]))
    return random.choice(options)


def _parse_yes_no(text: str):
    t = text.strip().lower()
    if any(w in t for w in _YES_WORDS):
        return True
    if any(w in t for w in _NO_WORDS):
        return False
    return None


def _new_session_state(lang: str, user_id: str = None) -> dict:
    return {
        "title": None,
        "state": STATE_CONVERSATION,
        "language": lang,
        "location": None,
        "user_id": user_id,
        "adresse_texte": None,
        "texte_plainte": None,
        "image_analysis": None,
        "prediction": None,
        "dialect_info": None,
        "duplicate_match": None,
        "history": [],
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def start_or_continue(session_id: str, message: str, image_base64: str = None,
                      location: dict = None, user_id: str = None, audio_only: bool = False) -> dict:
    if not session_id:
        session_id = str(uuid.uuid4())

    session = db.get_session(session_id)

    # Text detection
    if message:
        lang_info = detect_language(message)
        detected_lang = lang_info["language"] if lang_info["language"] not in ("mixed", "unknown") else None
    else:
        detected_lang = "fr"

    if session is None:
        session = _new_session_state(detected_lang or "fr", user_id)
        if location:
            session["location"] = location

        # First message
        if message or image_base64:
            session["history"].append({"role": "user", "text": message or "[Image envoyée]"})
            title_text = (message or "[Image]").strip()
            session["title"] = title_text[:40] + ("..." if len(title_text) > 40 else "")

            if message == "Voici ma position actuelle." and not image_base64:
                reply = _pick_response(_GREETINGS, session["language"])
                session["history"].append({"role": "assistant", "text": reply})
                db.save_session(session_id, session)
                return _response(session_id, reply, session["state"])

            # Smart routing based on intent
            return _route_by_intent(session_id, session, message, image_base64, audio_only=audio_only)
        else:
            # Empty first message — just greet
            reply = _pick_response(_GREETINGS, session["language"])
            session["history"].append({"role": "assistant", "text": reply})
            db.save_session(session_id, session)
            return _response(session_id, reply, session["state"], action="REQUEST_GPS")

    session["history"].append({"role": "user", "text": message or "[Image envoyée]"})
    
    # Only change language if we are not in the middle of a flow, and it's not the hardcoded GPS string
    if detected_lang and message != "Voici ma position actuelle." and session["state"] in (STATE_CONVERSATION, STATE_DONE):
        session["language"] = detected_lang
        
    if location:
        session["location"] = location
    if user_id:
        session["user_id"] = user_id

    state = session["state"]

    # If user is in the middle of the complaint flow, stay in it
    if state == STATE_ASK_PROBLEM:
        if message == "Voici ma position actuelle." and not image_base64:
            reply = _pick_response(_GREETINGS, session["language"])
            return _finish_turn(session_id, session, reply, state)
        return _handle_problem_input(session_id, session, message, image_base64)

    if state == STATE_ASK_LOCATION:
        if location:
            pass
        elif message and message != "Voici ma position actuelle.":
            session["adresse_texte"] = message
            session["texte_plainte"] = f"{session.get('texte_plainte', '')} [Lieu: {message}]"
            
        if image_base64:
            vision_result = vision_processor.analyze_image(image_base64)
            session["image_analysis"] = vision_result
            if vision_result.get("category_hint"):
                desc = vision_result.get("description", "")
                session["texte_plainte"] += f" [Vision: {desc}]"
            return _run_classification_step(session_id, session)
            
        if audio_only:
            # Skip asking for an image in voice mode
            return _run_classification_step(session_id, session)

        session["state"] = STATE_ASK_IMAGE
        reply = _t("ask_image", session["language"])
        return _finish_turn(session_id, session, reply, session["state"])

    if state == STATE_ASK_IMAGE:
        if image_base64:
            vision_result = vision_processor.analyze_image(image_base64)
            session["image_analysis"] = vision_result
            if vision_result.get("category_hint"):
                desc = vision_result.get("description", "")
                session["texte_plainte"] += f" [Vision: {desc}]"
        elif message:
            ans = _parse_yes_no(message)
            if ans is False:
                pass
            elif ans is None:
                session["texte_plainte"] += f" {message}"
        
        return _run_classification_step(session_id, session)

    if state == STATE_CLARIFY_CATEGORY:
        if message:
            session["texte_plainte"] = f"{session.get('texte_plainte', '')} {message}"
        return _run_classification_step(session_id, session, force_after_clarification=True)



    if state == STATE_CONFIRM_SUMMARY:
        answer = _parse_yes_no(message or "")
        if answer is None:
            reply = _t("need_yes_no", session["language"])
            return _finish_turn(session_id, session, reply, state)
        if answer is False:
            reply = _t("cancelled", session["language"])
            session["state"] = STATE_CONVERSATION
            return _finish_turn(session_id, session, reply, session["state"])
        return _save_complaint(session_id, session)

    # STATE_CONVERSATION or STATE_DONE — route by intent
    if state in (STATE_CONVERSATION, STATE_DONE):
        return _route_by_intent(session_id, session, message, image_base64, audio_only=audio_only)

    # Fallback: reset and route
    return _route_by_intent(session_id, session, message, image_base64, audio_only=audio_only)


# ---------------------------------------------------------------------------
# Intent-based routing (the core new logic)
# ---------------------------------------------------------------------------

def _route_by_intent(session_id: str, session: dict, message: str,
                     image_base64: str = None, audio_only: bool = False) -> dict:
    """
    Route the user's message based on detected intent.
    This is what makes the bot feel intelligent and human-like.
    """
    lang = session["language"]

    # If there's an image, go straight to complaint flow
    if image_base64:
        session["state"] = STATE_ASK_PROBLEM
        return _handle_problem_input(session_id, session, message, image_base64, audio_only=audio_only)

    # Detect intent
    intent_result = detect_intent(message, session.get("state"))
    intent = intent_result["intent"]

    # Log the interaction for learning
    try:
        mongo_db = db.get_db()
        learning.log_conversation_turn(
            mongo_db, session_id, "user", message, intent=intent
        )
    except Exception:
        pass

    # ── Greeting ──
    if intent == "greeting":
        reply = _pick_response(_GREETINGS, lang)
        session["state"] = STATE_CONVERSATION
        return _finish_turn(session_id, session, reply, session["state"])

    # ── Farewell ──
    if intent == "farewell":
        reply = _pick_response(_FAREWELLS, lang)
        session["state"] = STATE_DONE
        return _finish_turn(session_id, session, reply, session["state"])

    # ── Complaint tracking ──
    if intent == "complaint_tracking":
        complaint_id = intent_result.get("complaint_id")
        return _handle_complaint_tracking(session_id, session, complaint_id, message)

    # ── FAQ question ──
    if intent == "faq_question":
        return _handle_faq_question(session_id, session, message)

    # ── Complaint ──
    if intent == "complaint":
        session["state"] = STATE_ASK_PROBLEM
        return _handle_problem_input(session_id, session, message, image_base64, audio_only=audio_only)

    # ── Off-topic ──
    if intent == "off_topic":
        reply = _pick_response(_OFF_TOPIC, lang)
        session["state"] = STATE_CONVERSATION
        return _finish_turn(session_id, session, reply, session["state"])

    # ── Unclear ──
    # Try FAQ first as a fallback — maybe the user is asking something
    # we can answer even if intent detection isn't sure
    faq_result = rag.retrieve(message, top_k=1, lang=lang)
    if faq_result["confident"]:
        return _handle_faq_question(session_id, session, message)

    if audio_only:
        # In voice mode, we want a conversational fallback, not a strict "I didn't understand".
        # If RAG didn't confidently match, still use it to answer or give a smooth conversational reply.
        try:
            from llm_service import generate_response
            prompt = f"Tu es l'assistant vocal intelligent de la SONEDE. Réponds brièvement et naturellement à cette question ou remarque d'un citoyen, sans lui demander de photos ou d'utiliser l'interface. S'il signale un problème d'eau, dis-lui de préciser le problème. Remarque: {message}"
            reply = generate_response(prompt)
            session["state"] = STATE_CONVERSATION
            return _finish_turn(session_id, session, reply, session["state"])
        except Exception:
            pass

    reply = _pick_response(_UNCLEAR, lang)
    session["state"] = STATE_CONVERSATION
    return _finish_turn(session_id, session, reply, session["state"])


# ---------------------------------------------------------------------------
# FAQ handling
# ---------------------------------------------------------------------------

def _handle_faq_question(session_id: str, session: dict, message: str) -> dict:
    """Search the FAQ and return the best answer."""
    lang = session["language"]
    faq_result = rag.retrieve(message, top_k=1, lang=lang)

    if faq_result["confident"] and faq_result["results"]:
        top = faq_result["results"][0]
        answer = top["contenu"]
        faq_id = top["id"]
        score = top["score"]

        # Log FAQ usage for learning
        try:
            mongo_db = db.get_db()
            learning.log_faq_usage(mongo_db, faq_id)
            learning.log_conversation_turn(
                mongo_db, session_id, "assistant", answer,
                faq_id=faq_id, faq_score=score
            )
        except Exception:
            pass

        # Build a natural response
        prefix = _FAQ_ANSWER_PREFIX.get(_lang_bucket(lang), "")
        reply = f"{prefix}{answer}"
        session["state"] = STATE_CONVERSATION
        return _finish_turn(session_id, session, reply, session["state"])
    else:
        # FAQ didn't find a good answer — log as learning gap
        best_score = faq_result["results"][0]["score"] if faq_result["results"] else 0.0
        try:
            mongo_db = db.get_db()
            learning.log_learning_gap(
                mongo_db, session_id, message,
                "faq_question", best_score, lang
            )
        except Exception:
            pass

        reply = _FAQ_NOT_FOUND.get(_lang_bucket(lang), _FAQ_NOT_FOUND["fr"])
        session["state"] = STATE_CONVERSATION
        return _finish_turn(session_id, session, reply, session["state"])


# ---------------------------------------------------------------------------
# Complaint tracking
# ---------------------------------------------------------------------------

def _handle_complaint_tracking(session_id: str, session: dict,
                               complaint_id: str, message: str) -> dict:
    """Look up a complaint by its ID and return the status."""
    lang = session["language"]
    bucket = _lang_bucket(lang)

    # Try to extract complaint ID from message if not provided
    if not complaint_id:
        import re
        match = re.search(r'PL-[A-Z0-9]{6,10}', message, re.IGNORECASE)
        if match:
            complaint_id = match.group().upper()
        else:
            # Check if this session has recently created a complaint
            try:
                mongo_db = db.get_db()
                import pymongo
                recent = mongo_db.complaints.find_one(
                    {"session_id": session_id},
                    sort=[("date_signalement", pymongo.DESCENDING)]
                )
                if recent and recent.get("id_plainte"):
                    complaint_id = recent["id_plainte"]
            except Exception as e:
                print(f"[tracking] Error fetching recent complaint: {e}")
            
            # If still no ID found, ask the user
            if not complaint_id:
                MISSING_ID = {
                    "fr": "Veuillez indiquer le numéro de votre réclamation (qui commence par PL-) pour que je puisse vérifier son statut.",
                    "ar": "الرجاء إعطائي رقم الشكوى (الذي يبدأ بـ PL-) باش نجم نثبت في حالتها.",
                    "en": "Please provide your complaint number (starting with PL-) so I can check its status."
                }
                reply = MISSING_ID.get(bucket, MISSING_ID["fr"])
                session["state"] = STATE_CONVERSATION
                return _finish_turn(session_id, session, reply, session["state"])

    complaint_id = complaint_id.upper()
    complaint = db.get_complaint(complaint_id)

    if complaint is None:
        template = _COMPLAINT_TRACKING_NOT_FOUND.get(bucket, _COMPLAINT_TRACKING_NOT_FOUND["fr"])
        reply = template.format(id=complaint_id)
    else:
        date_str = ""
        if complaint.get("date_signalement"):
            d = complaint["date_signalement"]
            if hasattr(d, 'strftime'):
                date_str = d.strftime("%d/%m/%Y %H:%M")
            else:
                date_str = str(d)

        template = _COMPLAINT_TRACKING_FOUND.get(bucket, _COMPLAINT_TRACKING_FOUND["fr"])
        reply = template.format(
            id=complaint_id,
            categorie=_category_label(complaint.get("categorie", ""), lang),
            statut=_status_label(complaint.get("statut", ""), lang),
            date=date_str,
            urgence=_urgency_label(complaint.get("urgence", ""), lang),
        )

    session["state"] = STATE_CONVERSATION
    return _finish_turn(session_id, session, reply, session["state"])


# ---------------------------------------------------------------------------
# Complaint flow (preserved from v3, with minor improvements)
# ---------------------------------------------------------------------------

def _handle_problem_input(session_id: str, session: dict, message: str,
                          image_base64: str, audio_only: bool = False) -> dict:
    if message and not session.get("texte_plainte"):
        session["texte_plainte"] = message
    elif message:
        session["texte_plainte"] += f" {message}"

    if image_base64:
        vision_result = vision_processor.analyze_image(image_base64)
        session["image_analysis"] = vision_result
        if vision_result.get("category_hint"):
            desc = vision_result.get("description", "")
            if not session.get("texte_plainte"):
                session["texte_plainte"] = f"[Vision: {desc}]"
            else:
                session["texte_plainte"] += f" [Vision: {desc}]"

    session["state"] = STATE_ASK_LOCATION
    
    if audio_only:
        # User requested specific phrasing in Derja
        if session["language"] in ["ar", "tn_arabe", "tn_latin"]:
            reply = "وين تسكن بالضبط؟" if session["language"] in ["ar", "tn_arabe"] else "win toskon bedhabt ?"
        else:
            reply = "D'accord, veuillez m'indiquer où vous habitez exactement."
    else:
        reply = _t("ask_location", session["language"])
        
    return _finish_turn(session_id, session, reply, session["state"])


def _run_classification_step(session_id: str, session: dict,
                             force_after_clarification: bool = False) -> dict:
    lang = session["language"]
    texte = session["texte_plainte"]

    prediction = classifier.predict(texte)
    dialect_info = analyze_dialect(texte)
    vision_info = session.get("image_analysis") or {}

    # Fusion of heuristics (Vision > Dialect > Classifier)
    if prediction["needs_clarification"]:
        if vision_info.get("category_hint") and vision_info.get("confidence", 0) > 0.4:
            prediction["categorie"] = vision_info["category_hint"]
            prediction["needs_clarification"] = False
            prediction["source"] += "+vision"
        elif dialect_info["category_hints"]:
            hinted = dialect_info["category_hints"][0]
            if hinted in prediction["toutes_categories"]:
                prediction["categorie"] = hinted
                prediction["needs_clarification"] = False

    session["prediction"] = prediction
    session["dialect_info"] = dialect_info

    if prediction["needs_clarification"] and not force_after_clarification:
        session["state"] = STATE_CLARIFY_CATEGORY
        reply = _t("clarify_category", lang)
        return _finish_turn(session_id, session, reply, session["state"])

    # Duplicate check if we have location
    if session.get("location"):
        lat = session["location"].get("lat")
        lng = session["location"].get("lng")
        dup = duplicate_checker.check_existing_incidents(
            categorie=prediction["categorie"],
            delegation=None,
            gouvernorat=None,
        )
        if dup["recommendation"] == "existing_incident":
            existing_id = dup["matches"][0]["id_plainte"]
            reply = _t("already_in_progress", lang, id_plainte=existing_id)
            
            session["state"] = STATE_CONVERSATION
            session["texte_plainte"] = None
            session["prediction"] = None
            session["dialect_info"] = None
            session["image_analysis"] = None
            session["adresse_texte"] = None
            
            return _finish_turn(session_id, session, reply, session["state"])

    session["state"] = STATE_CONFIRM_SUMMARY
    reply = _summary_text(session)
    return _finish_turn(session_id, session, reply, session["state"])


def _summary_text(session: dict) -> str:
    prediction = session["prediction"]
    lang = session["language"]
    
    loc_info = ""
    if session.get("location"):
        loc_map = {"fr": " (GPS partagé)", "ar": " (تم استلام الموقع)", "en": " (GPS received)"}
        loc_info = loc_map.get(_lang_bucket(lang), loc_map["fr"])
    elif session.get("adresse_texte"):
        loc_info = f" (Lieu: {session.get('adresse_texte')})"

    return _t(
        "confirm_summary", lang,
        categorie=_category_label(prediction["categorie"], lang),
        urgence=_urgency_label(prediction["urgence"], lang),
        location_info=loc_info
    )


def _reverse_geocode(lat: float, lng: float):
    import urllib.request, json
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&accept-language=fr"
        req = urllib.request.Request(url, headers={'User-Agent': 'SonedeApp/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            address = data.get('address', {})
            state = address.get('state', '')
            county = address.get('county', '')
            if state:
                state = state.replace('Gouvernorat', '').strip()
            return state, county
    except Exception as e:
        print(f"[reverse_geocode] Error: {e}")
        return None, None


def _geocode_address(query: str):
    import urllib.request, urllib.parse, json
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'SonedeApp/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"[geocode_address] Error: {e}")
    return None, None


def _save_complaint(session_id: str, session: dict) -> dict:
    prediction = session["prediction"]
    loc = session.get("location") or {}

    # Extraction du gouvernorat et delegation
    adresse = session.get("adresse_texte") or session.get("texte_plainte") or ""
    loc_info = extract_location(adresse)
    
    gouvernorat = loc_info.get("gouvernorat")
    delegation = loc_info.get("delegation")

    # Fallback to reverse geocoding if we only have GPS
    if not gouvernorat and loc.get("lat") and loc.get("lng"):
        gouvernorat, delegation = _reverse_geocode(loc.get("lat"), loc.get("lng"))

    # Fallback to geocoding if we only have text (to populate lat/lng on the map)
    lat = loc.get("lat")
    lng = loc.get("lng")
    if not lat and not lng and (gouvernorat or delegation):
        query_parts = []
        if delegation:
            query_parts.append(delegation)
        if gouvernorat:
            query_parts.append(gouvernorat)
        query_parts.append("Tunisie")
        query_str = ", ".join(query_parts)
        lat, lng = _geocode_address(query_str)

    complaint = db.create_complaint({
        "session_id": session_id,
        "user_id": session.get("user_id"),
        "texte_plainte": session["texte_plainte"],
        "adresse_texte": session.get("adresse_texte"),
        "gouvernorat": gouvernorat,
        "delegation": delegation,
        "categorie": prediction["categorie"],
        "categorie_confidence": prediction["categorie_confidence"],
        "urgence": prediction["urgence"],
        "urgence_confidence": prediction["urgence_confidence"],
        "langue": session["language"],
        "location_lat": lat,
        "location_lng": lng,
        "dialect_matches": session["dialect_info"]["matches"],
        "vision_category": (session.get("image_analysis") or {}).get("category_hint"),
        "source": prediction.get("source", "chatbot"),
    })

    # Log the successful complaint for learning
    try:
        mongo_db = db.get_db()
        learning.log_conversation_turn(
            mongo_db, session_id, "system",
            f"Complaint saved: {complaint['id_plainte']}",
            intent="complaint"
        )
    except Exception:
        pass

    reply = _t("saved", session["language"], id_plainte=complaint["id_plainte"])

    # After saving, keep session alive for follow-up questions
    session["state"] = STATE_CONVERSATION
    session["texte_plainte"] = None
    session["prediction"] = None
    session["dialect_info"] = None
    session["image_analysis"] = None
    session["adresse_texte"] = None

    return _finish_turn(session_id, session, reply, session["state"],
                        done=False, id_plainte=complaint["id_plainte"])


def _finish_turn(session_id: str, session: dict, reply: str, state: str,
                 done: bool = False, id_plainte: str = None) -> dict:
    session["history"].append({"role": "assistant", "text": reply})
    db.save_session(session_id, session)

    # Log assistant response for learning
    try:
        mongo_db = db.get_db()
        learning.log_conversation_turn(mongo_db, session_id, "assistant", reply)
    except Exception:
        pass

    return _response(session_id, reply, state, done=done, id_plainte=id_plainte)


def _response(session_id: str, reply: str, state: str, done: bool = False,
              id_plainte: str = None, action: str = None) -> dict:
    res = {
        "session_id": session_id,
        "reply": reply,
        "state": state,
        "done": done,
        "id_plainte": id_plainte,
    }
    if action:
        res["action"] = action
    return res