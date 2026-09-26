import re

with open("c:/PROJET_STAGE_AMAL/sonede_ai/dialogue_manager.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add states
code = code.replace(
    'STATE_CONFIRM_SUMMARY = "CONFIRM_SUMMARY"',
    'STATE_CONFIRM_SUMMARY = "CONFIRM_SUMMARY"\nSTATE_ASK_LOCATION = "ASK_LOCATION"\nSTATE_ASK_IMAGE = "ASK_IMAGE"'
)

# 2. Add texts to _TEXTS
texts_to_add = """    "ask_location": {
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
    "greet_ask_problem": {"""
code = code.replace('    "greet_ask_problem": {', texts_to_add)

# 3. Add user_id to session state
code = code.replace(
    'def _new_session_state(lang: str) -> dict:',
    'def _new_session_state(lang: str, user_id: str = None) -> dict:'
)
code = code.replace(
    '        "location": None,',
    '        "location": None,\n        "user_id": user_id,\n        "adresse_texte": None,'
)

# 4. start_or_continue signature
code = code.replace(
    'def start_or_continue(session_id: str, message: str, image_base64: str = None,\n                      location: dict = None) -> dict:',
    'def start_or_continue(session_id: str, message: str, image_base64: str = None,\n                      location: dict = None, user_id: str = None) -> dict:'
)
code = code.replace(
    '        session = _new_session_state(detected_lang or "fr")',
    '        session = _new_session_state(detected_lang or "fr", user_id)'
)

# Also add updating user_id if it comes in late
code = code.replace(
    '    if location:\n        session["location"] = location',
    '    if location:\n        session["location"] = location\n    if user_id:\n        session["user_id"] = user_id'
)

# 5. replace handle problem input
handle_problem_old = """def _handle_problem_input(session_id: str, session: dict, message: str,
                          image_base64: str) -> dict:
    session["texte_plainte"] = message or ""

    if image_base64:
        vision_result = vision_processor.analyze_image(image_base64)
        session["image_analysis"] = vision_result
        if vision_result.get("category_hint"):
            desc = vision_result.get("description", "")
            session["texte_plainte"] += f" [Vision: {desc}]"

    return _run_classification_step(session_id, session)"""

handle_problem_new = """def _handle_problem_input(session_id: str, session: dict, message: str,
                          image_base64: str) -> dict:
    if message and not session.get("texte_plainte"):
        session["texte_plainte"] = message
    elif message:
        session["texte_plainte"] += f" {message}"

    if image_base64:
        vision_result = vision_processor.analyze_image(image_base64)
        session["image_analysis"] = vision_result
        if vision_result.get("category_hint"):
            desc = vision_result.get("description", "")
            session["texte_plainte"] += f" [Vision: {desc}]"

    session["state"] = STATE_ASK_LOCATION
    reply = _t("ask_location", session["language"])
    return _finish_turn(session_id, session, reply, session["state"])"""

code = code.replace(handle_problem_old, handle_problem_new)

# 6. state loop injection
state_loop_old = """    if state == STATE_CLARIFY_CATEGORY:"""
state_loop_new = """    if state == STATE_ASK_LOCATION:
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

    if state == STATE_CLARIFY_CATEGORY:"""
code = code.replace(state_loop_old, state_loop_new)

# Remove CONFIRM_DUPLICATE from state loop entirely
duplicate_state_old = """    if state == STATE_CONFIRM_DUPLICATE:
        answer = _parse_yes_no(message or "")
        if answer is None:
            reply = _t("need_yes_no", session["language"])
            return _finish_turn(session_id, session, reply, state)
        if answer is False:
            existing_id = session["duplicate_match"]["id_plainte"]
            reply = _t("attached_to_existing", session["language"], id_plainte=existing_id)
            db.delete_session(session_id)
            return _response(session_id, reply, STATE_DONE, done=True, id_plainte=existing_id)
        session["state"] = STATE_CONFIRM_SUMMARY
        reply = _summary_text(session)
        return _finish_turn(session_id, session, reply, session["state"])"""
code = code.replace(duplicate_state_old, "")

# 7. duplicate check rewrite
duplicate_check_old = """    if session.get("location"):
        lat = session["location"].get("lat")
        lng = session["location"].get("lng")
        dup = duplicate_checker.check_existing_incidents(
            categorie=prediction["categorie"],
            delegation=None,
            gouvernorat=None,
        )
        if dup["recommendation"] == "existing_incident":
            session["duplicate_match"] = dup["matches"][0]
            session["state"] = STATE_CONFIRM_DUPLICATE
            reply = _t(
                "duplicate_found", lang,
                categorie=_category_label(prediction["categorie"], lang),
                id_plainte=dup["matches"][0]["id_plainte"]
            )
            return _finish_turn(session_id, session, reply, session["state"])"""

duplicate_check_new = """    if session.get("location"):
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
            
            return _finish_turn(session_id, session, reply, session["state"])"""
code = code.replace(duplicate_check_old, duplicate_check_new)


# 8. Save complaint updates
code = code.replace(
    '        "session_id": session_id,\n        "texte_plainte": session["texte_plainte"],',
    '        "session_id": session_id,\n        "user_id": session.get("user_id"),\n        "texte_plainte": session["texte_plainte"],\n        "adresse_texte": session.get("adresse_texte"),'
)
code = code.replace(
    '    session["image_analysis"] = None\n    session["duplicate_match"] = None',
    '    session["image_analysis"] = None\n    session["adresse_texte"] = None'
)


with open("c:/PROJET_STAGE_AMAL/sonede_ai/dialogue_manager.py", "w", encoding="utf-8") as f:
    f.write(code)
