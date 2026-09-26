"""
Learning & Conversation Logging for the SONEDE chatbot.

Tracks:
    - Full conversation histories (for quality monitoring)
    - Unanswered FAQ queries (learning gaps — questions the bot couldn't
      answer well, so an admin can later add them to the knowledge base)
    - Intent detection accuracy signals

This module enables the chatbot to "learn" in the sense of:
    1. Discovering gaps in its knowledge base (FAQ entries to add)
    2. Tracking which FAQ entries are most used
    3. Logging unknown patterns for future intent detection improvement
"""
from datetime import datetime, timezone
from typing import Optional


def log_conversation_turn(db, session_id: str, role: str, text: str,
                          intent: str = None, faq_id: str = None,
                          faq_score: float = None) -> None:
    """
    Log a single turn in the conversation.

    Parameters
    ----------
    db : MongoDB database instance
    session_id : str
    role : str
        'user' or 'assistant'
    text : str
        The message text
    intent : str, optional
        Detected intent (for user messages)
    faq_id : str, optional
        FAQ entry used to answer (for assistant messages)
    faq_score : float, optional
        Confidence score of the FAQ match
    """
    doc = {
        "session_id": session_id,
        "role": role,
        "text": text,
        "timestamp": datetime.now(timezone.utc),
    }
    if intent:
        doc["intent"] = intent
    if faq_id:
        doc["faq_id"] = faq_id
    if faq_score is not None:
        doc["faq_score"] = round(faq_score, 3)

    try:
        db.conversation_logs.insert_one(doc)
    except Exception as e:
        # Don't let logging failures break the chatbot
        print(f"[learning] Error logging turn: {e}")


def log_learning_gap(db, session_id: str, user_message: str,
                     detected_intent: str, best_faq_score: float,
                     language: str = "fr") -> None:
    """
    Log a question the bot couldn't answer well (low FAQ score).
    These gaps can be reviewed by admins to expand the knowledge base.

    Parameters
    ----------
    db : MongoDB database instance
    session_id : str
    user_message : str
        The question the user asked
    detected_intent : str
        What the intent detector classified it as
    best_faq_score : float
        The best FAQ match score (low score = gap)
    language : str
        Detected language of the message
    """
    doc = {
        "session_id": session_id,
        "user_message": user_message,
        "detected_intent": detected_intent,
        "best_faq_score": round(best_faq_score, 3),
        "language": language,
        "logged_at": datetime.now(timezone.utc),
        "resolved": False,
        "resolution": None,  # Admin can fill this in later
    }

    try:
        db.learning_gaps.insert_one(doc)
    except Exception as e:
        print(f"[learning] Error logging gap: {e}")


def log_faq_usage(db, faq_id: str) -> None:
    """
    Increment the usage counter for a FAQ entry.
    Helps identify the most/least useful entries.
    """
    try:
        db.faq_usage.update_one(
            {"faq_id": faq_id},
            {
                "$inc": {"count": 1},
                "$set": {"last_used": datetime.now(timezone.utc)},
                "$setOnInsert": {"first_used": datetime.now(timezone.utc)},
            },
            upsert=True,
        )
    except Exception as e:
        print(f"[learning] Error logging FAQ usage: {e}")


def get_learning_gaps(db, limit: int = 50,
                      only_unresolved: bool = True) -> list:
    """
    Retrieve learning gaps for admin review.
    """
    query = {}
    if only_unresolved:
        query["resolved"] = False

    try:
        cursor = (
            db.learning_gaps.find(query, {"_id": 0})
            .sort("logged_at", -1)
            .limit(limit)
        )
        return list(cursor)
    except Exception as e:
        print(f"[learning] Error retrieving gaps: {e}")
        return []


def resolve_gap(db, gap_id: str, resolution: str) -> bool:
    """
    Mark a learning gap as resolved (admin added the answer to FAQ).
    """
    try:
        from bson import ObjectId
        result = db.learning_gaps.update_one(
            {"_id": ObjectId(gap_id)},
            {
                "$set": {
                    "resolved": True,
                    "resolution": resolution,
                    "resolved_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"[learning] Error resolving gap: {e}")
        return False


def get_faq_usage_stats(db, limit: int = 50) -> list:
    """
    Get FAQ usage statistics (most used entries).
    """
    try:
        cursor = (
            db.faq_usage.find({}, {"_id": 0})
            .sort("count", -1)
            .limit(limit)
        )
        return list(cursor)
    except Exception as e:
        print(f"[learning] Error retrieving FAQ stats: {e}")
        return []
