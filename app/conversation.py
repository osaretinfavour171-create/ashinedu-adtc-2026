#!/usr/bin/env python3
"""Conversational flow engine for EARL AI.

Adapted from Fish Audio's conversation.py pattern.

v3 improvements:
- Language-aware: all opening/closing phrases respect current language
- Conversation persistence: saves to JSON, restores on restart
- Active topic tracking + adaptive response length (from v2)
"""

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Emotional tone tags
# ---------------------------------------------------------------------------

class ToneTag(Enum):
    CALM = "calm"
    REASSURING = "reassuring"
    URGENT = "urgent"
    GENTLE = "gentle"
    SIMPLE = "simple"
    PROFESSIONAL = "professional"
    EMPATHETIC = "empathetic"
    DIRECT = "direct"
    ENCOURAGING = "encouraging"


# ---------------------------------------------------------------------------
# Patient emotional state
# ---------------------------------------------------------------------------

class EmotionalState(Enum):
    ANXIOUS = "anxious"
    CALM = "calm"
    DISTRESSED = "distressed"
    CONFUSED = "confused"
    URGENT = "urgent"
    DEFERRING = "deferring"
    SKEPTICAL = "skeptical"


EMOTION_PATTERNS = {
    EmotionalState.ANXIOUS: [
        "worried", "scared", "afraid", "anxious", "nervous",
        "what if", "is it serious", "will i die", "am i going to die",
        "i'm afraid", "i'm scared", "please help", "i don't know what to do",
        "abeg help me", "i dey fear", "wetin go happen", "e go kill me",
    ],
    EmotionalState.DISTRESSED: [
        "pain", "hurts", "suffering", "agony", "unbearable",
        "i can't take it", "the pain is too much", "please",
        "e dey pain me", "i dey suffer", "e too much",
    ],
    EmotionalState.CONFUSED: [
        "i don't understand", "what do you mean", "confused",
        "which one", "how so", "explain", "i don't get it",
        "i no understand", "wetin you mean", "how na",
    ],
    EmotionalState.URGENT: [
        "emergency", "now", "immediately", "quick", "hurry",
        "right now", "very bad", "getting worse", "can't wait",
        "now now", "sharp sharp", "e dey serious",
    ],
    EmotionalState.SKEPTICAL: [
        "are you sure", "really", "i don't think so", "but",
        "last time", "it didn't work", "doesn't work",
        "you sure?", "e sure?", "i don't believe",
    ],
    EmotionalState.DEFERRING: [
        "okay", "alright", "fine", "whatever you say",
        "i trust you", "just tell me", "anything you say",
    ],
}


# ---------------------------------------------------------------------------
# Symptom/topic keywords for active topic tracking
# ---------------------------------------------------------------------------

SYMPTOM_KEYWORDS = {
    "fever": ["fever", "hot body", "temperature", "body dey hot", "hot"],
    "cough": ["cough", "coughing", "chest dey tight", "catarrh"],
    "headache": ["headache", "head pain", "head dey pain", "migraine"],
    "diarrhoea": ["diarrhoea", "run stomach", "loose stool", "stomach dey run"],
    "vomiting": ["vomit", "vomiting", "throwing up", "e dey vomit"],
    "malaria": ["malaria", "malarial", "shivering", "chills"],
    "pain": ["pain", "ache", "hurts", "body dey pain", "sore"],
    "rash": ["rash", "skin", "itch", "body dey itch", "spots"],
    "breathing": ["breathing", "breath", "wheezing", "asthma", "chest tight"],
    "stomach": ["stomach", "belly", "abdomen", "gastric", "ulcer"],
    "joint": ["joint", "knee", "elbow", "arthritis", "swelling"],
    "infection": ["infection", "wound", "boil", "pus", "swollen"],
    "eye": ["eye", "vision", "blurry", "red eye", "discharge"],
    "ear": ["ear", "hearing", "earache", "ear pain"],
    "tooth": ["tooth", "teeth", "gum", "dental", "mouth"],
    "pregnancy": ["pregnant", "pregnancy", "ANC", "antenatal"],
    "mental_health": ["sad", "depression", "anxiety", "sleep", "insomnia"],
    "child_health": ["child", "pikin", "baby", "infant", "toddler"],
}


# ---------------------------------------------------------------------------
# Language-aware phrases
# ---------------------------------------------------------------------------

# All conversational phrases keyed by language
PHRASES = {
    "pidgin": {
        "anxious_open": "No worry, I dey help you. Make we look into this together.\n",
        "distressed_open": "I understand say you dey suffer. Make I help you with this.\n",
        "confused_open": "No worry, I go explain am well well for you.\n",
        "urgent_open": "I hear you. Make we act quick.\n",
        "skeptical_open": "I understand your concern. Make I explain the evidence.\n",
        "followup_open": "Okay, I don note wetin you talk before.\n",
        "followup_topics": "I don note say we talk about {topics} before.\n",
        "topic_note": "\nNote: {topics} fit dey related.",
        "reassuring_close": "\nYou go dey alright. Just follow the treatment.",
        "reassuring_close_elderly": "\nYou go dey alright. Just follow wetin I talk.",
        "reassuring_close_child": "\nYour pikin go dey alright. Just follow the medicine.",
        "encouraging_close": "\nIf e no dey better in 2-3 days, come back make we check am again.",
        "urgent_close": "\nIf e dey worse, go hospital now now. No wait!",
        "gentle_close": "\nTake your time. If you get any question, ask me.",
        # Follow-up question suggestions
        "suggest_cough": "E dey cough?",
        "suggest_stomach": "Stomach dey run?",
        "suggest_breathing": "E dey find am hard to breathe?",
        "suggest_vomit": "E dey vomit too?",
        "suggest_fever": "E get fever?",
    },
    "en": {
        "anxious_open": "Don't worry, I'm here to help. Let's look into this together.\n",
        "distressed_open": "I understand you're in pain. Let me help you with this.\n",
        "confused_open": "Don't worry, I'll explain this clearly for you.\n",
        "urgent_open": "I hear you. Let's act quickly.\n",
        "skeptical_open": "I understand your concern. Let me explain the evidence.\n",
        "followup_open": "Okay, I've noted what you mentioned before.\n",
        "followup_topics": "I've noted we discussed {topics} before.\n",
        "topic_note": "\nNote: {topics} may be related.",
        "reassuring_close": "\nYou'll be alright. Just follow the treatment.",
        "reassuring_close_elderly": "\nYou'll be alright. Just follow the advice.",
        "reassuring_close_child": "\nYour child will be alright. Just follow the medicine.",
        "encouraging_close": "\nIf it doesn't improve in 2-3 days, come back and we'll check again.",
        "urgent_close": "\nIf it gets worse, go to the hospital immediately. Don't wait!",
        "gentle_close": "\nTake your time. If you have any questions, ask me.",
        # Follow-up question suggestions
        "suggest_cough": "Is there a cough?",
        "suggest_stomach": "Is there diarrhoea?",
        "suggest_breathing": "Is there difficulty breathing?",
        "suggest_vomit": "Is there vomiting too?",
        "suggest_fever": "Is there a fever?",
    },
}


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

@dataclass
class ClinicalMessage:
    """A single message in the clinical conversation."""
    role: Literal["system", "patient", "healthworker"]
    content: str
    tone_tags: list[ToneTag] = field(default_factory=list)
    emotion: Optional[EmotionalState] = None
    metadata: dict = field(default_factory=dict)
    timestamp: float = 0.0
    detected_topics: list[str] = field(default_factory=list)

    def add_tone(self, tag: ToneTag):
        if tag not in self.tone_tags:
            self.tone_tags.append(tag)

    def has_tone(self, tag: ToneTag) -> bool:
        return tag in self.tone_tags

    def to_dict(self) -> dict:
        """Serialize for persistence."""
        return {
            "role": self.role,
            "content": self.content,
            "emotion": self.emotion.value if self.emotion else None,
            "tone_tags": [t.value for t in self.tone_tags],
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "detected_topics": self.detected_topics,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ClinicalMessage":
        """Deserialize from persistence."""
        return cls(
            role=d["role"],
            content=d["content"],
            emotion=EmotionalState(d["emotion"]) if d.get("emotion") else None,
            tone_tags=[ToneTag(t) for t in d.get("tone_tags", [])],
            metadata=d.get("metadata", {}),
            timestamp=d.get("timestamp", 0),
            detected_topics=d.get("detected_topics", []),
        )


# ---------------------------------------------------------------------------
# Conversation with persistence
# ---------------------------------------------------------------------------

class ClinicalConversation:
    """Manages multi-turn clinical dialogue with topic tracking and persistence."""

    def __init__(self, messages: list[ClinicalMessage] = None):
        self.messages: list[ClinicalMessage] = messages or []
        self._emotion_history: list[EmotionalState] = []
        self._topic_stack: list[str] = []
        self._discussed_topics: set[str] = set()
        self._mentioned_symptoms: set[str] = set()

    def append(self, message: ClinicalMessage):
        """Add a message and auto-track topics from patient input."""
        self.messages.append(message)
        if message.emotion:
            self._emotion_history.append(message.emotion)
        if message.role == "patient":
            topics = self._extract_topics(message.content)
            message.detected_topics = topics
            for t in topics:
                self._push_topic(t)
                self._discussed_topics.add(t)
                self._mentioned_symptoms.add(t)

    def _extract_topics(self, text: str) -> list[str]:
        text_lower = text.lower()
        found = []
        for topic, keywords in SYMPTOM_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(topic)
        return found

    def _push_topic(self, topic: str):
        if topic not in self._topic_stack:
            self._topic_stack.append(topic)

    def get_last_n(self, n: int = 5) -> list[ClinicalMessage]:
        return self.messages[-n:]

    def get_patient_messages(self) -> list[ClinicalMessage]:
        return [m for m in self.messages if m.role == "patient"]

    def get_discussed_topics(self) -> list[str]:
        return list(self._discussed_topics)

    def get_unmentioned_symptoms(self, query_symptoms: list[str]) -> list[str]:
        return [s for s in query_symptoms if s not in self._mentioned_symptoms]

    # ------------------------------------------------------------------
    # Emotion tracking
    # ------------------------------------------------------------------

    def detect_emotion(self, text: str) -> EmotionalState:
        text_lower = text.lower()
        scores = {}
        for emotion, patterns in EMOTION_PATTERNS.items():
            score = sum(1 for p in patterns if p in text_lower)
            if score > 0:
                scores[emotion] = score
        if not scores:
            return EmotionalState.CALM
        return max(scores, key=scores.get)

    def get_emotional_arc(self) -> EmotionalState:
        if not self._emotion_history:
            return EmotionalState.CALM
        recent = self._emotion_history[-3:]
        if EmotionalState.URGENT in recent:
            return EmotionalState.URGENT
        if EmotionalState.DISTRESSED in recent:
            return EmotionalState.DISTRESSED
        if EmotionalState.ANXIOUS in recent:
            return EmotionalState.ANXIOUS
        from collections import Counter
        counts = Counter(recent)
        return counts.most_common(1)[0][0]

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    def build_clinical_context(self) -> dict:
        emotion = self.get_emotional_arc()
        turn_count = len(self.messages)
        patient_msgs = self.get_patient_messages()
        is_followup = turn_count > 2
        is_repeated = self._is_repeated_concern()

        is_elderly = any(
            m.metadata.get("age_years", 0) and m.metadata.get("age_years", 0) > 60
            for m in patient_msgs
        )
        is_child = any(
            m.metadata.get("age_years", 0) and m.metadata.get("age_years", 0) < 12
            for m in patient_msgs
        )
        has_fever = any(
            "fever" in m.content.lower() or "hot body" in m.content.lower()
            for m in patient_msgs
        )

        return {
            "emotion": emotion,
            "turn_count": turn_count,
            "is_followup": is_followup,
            "is_repeated": is_repeated,
            "is_elderly": is_elderly,
            "is_child": is_child,
            "has_fever": has_fever,
            "patient_message_count": len(patient_msgs),
            "topic_stack": self._topic_stack.copy(),
            "discussed_topics": list(self._discussed_topics),
            "mentioned_symptoms": list(self._mentioned_symptoms),
        }

    def _is_repeated_concern(self) -> bool:
        patient_msgs = self.get_patient_messages()
        if len(patient_msgs) < 2:
            return False
        words1 = set(patient_msgs[-1].content.lower().split())
        words2 = set(patient_msgs[-2].content.lower().split())
        overlap = words1 & words2
        if len(words1) > 0 and len(overlap) / len(words1) > 0.4:
            return True
        return False

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize entire conversation for JSON persistence."""
        return {
            "messages": [m.to_dict() for m in self.messages],
            "emotion_history": [e.value for e in self._emotion_history],
            "topic_stack": self._topic_stack,
            "discussed_topics": list(self._discussed_topics),
            "mentioned_symptoms": list(self._mentioned_symptoms),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ClinicalConversation":
        """Restore conversation from JSON."""
        conv = cls()
        conv.messages = [ClinicalMessage.from_dict(m) for m in d.get("messages", [])]
        conv._emotion_history = [EmotionalState(e) for e in d.get("emotion_history", [])]
        conv._topic_stack = d.get("topic_stack", [])
        conv._discussed_topics = set(d.get("discussed_topics", []))
        conv._mentioned_symptoms = set(d.get("mentioned_symptoms", []))
        return conv

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def length(self) -> int:
        return len(self.messages)

    @property
    def is_new(self) -> bool:
        return len(self.messages) <= 1

    def clear(self):
        self.messages.clear()
        self._emotion_history.clear()
        self._topic_stack.clear()
        self._discussed_topics.clear()
        self._mentioned_symptoms.clear()

    def __len__(self):
        return len(self.messages)

    def __repr__(self):
        return f"ClinicalConversation({len(self.messages)} messages, topics={self._topic_stack})"


# ---------------------------------------------------------------------------
# Conversational Flow Engine
# ---------------------------------------------------------------------------

class ConversationalFlow:
    """Language-aware conversational flow with persistence.

    All phrases adapt to the current language setting.
    Conversation history is saved to disk and restored on restart.
    """

    def __init__(self, persistence_path: str = None):
        self.conversation = ClinicalConversation()
        self._lang = "pidgin"
        self._persistence_path = persistence_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "conversation_history.json"
        )

    def set_language(self, lang: str):
        """Update the language for all future phrases."""
        self._lang = lang if lang in PHRASES else "pidgin"

    def _phrase(self, key: str) -> str:
        """Get a phrase in the current language."""
        return PHRASES.get(self._lang, PHRASES["pidgin"]).get(key, "")

    def _phrase_format(self, key: str, **kwargs) -> str:
        """Get a formatted phrase in the current language."""
        template = self._phrase(key)
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template

    def start(self):
        """Start a new conversation (clears previous)."""
        self.conversation.clear()
        self.conversation.append(ClinicalMessage(
            role="system",
            content="Clinical consultation started.",
            tone_tags=[ToneTag.PROFESSIONAL],
        ))

    def process_patient_input(self, text: str, metadata: dict = None) -> ClinicalMessage:
        emotion = self.conversation.detect_emotion(text)
        msg = ClinicalMessage(
            role="patient",
            content=text,
            emotion=emotion,
            metadata=metadata or {},
        )
        self.conversation.append(msg)
        return msg

    def determine_tone(self) -> list[ToneTag]:
        context = self.conversation.build_clinical_context()
        emotion = context["emotion"]
        tags = []

        if emotion == EmotionalState.URGENT:
            tags.extend([ToneTag.URGENT, ToneTag.DIRECT])
        elif emotion == EmotionalState.DISTRESSED:
            tags.extend([ToneTag.CALM, ToneTag.REASSURING])
        elif emotion == EmotionalState.ANXIOUS:
            tags.extend([ToneTag.REASSURING, ToneTag.EMPATHETIC])
        elif emotion == EmotionalState.CONFUSED:
            tags.extend([ToneTag.SIMPLE, ToneTag.GENTLE])
        elif emotion == EmotionalState.SKEPTICAL:
            tags.extend([ToneTag.PROFESSIONAL, ToneTag.DIRECT])
        else:
            tags.append(ToneTag.PROFESSIONAL)

        if context["is_elderly"]:
            tags.append(ToneTag.GENTLE)
            if ToneTag.SIMPLE not in tags:
                tags.append(ToneTag.SIMPLE)
        if context["is_child"]:
            tags.append(ToneTag.GENTLE)
        if context["is_followup"] and context["is_repeated"]:
            tags.append(ToneTag.REASSURING)
            tags.append(ToneTag.ENCOURAGING)

        return list(dict.fromkeys(tags))

    # ------------------------------------------------------------------
    # Adaptive response length
    # ------------------------------------------------------------------

    def _determine_response_length(self, tone_tags: list[ToneTag]) -> str:
        if ToneTag.URGENT in tone_tags:
            return "short"
        if ToneTag.DIRECT in tone_tags:
            return "medium"
        if ToneTag.SIMPLE in tone_tags:
            return "medium"
        if ToneTag.GENTLE in tone_tags:
            return "detailed"
        if ToneTag.PROFESSIONAL in tone_tags:
            return "detailed"
        return "medium"

    def _trim_response(self, text: str, max_length: str) -> str:
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        if max_length == "short":
            action_lines = []
            for line in lines:
                lower = line.lower()
                if any(w in lower for w in ["give", "take", "refer", "go", "hospital",
                                             "dose", "mg", "paracetamol", "act", "ors",
                                             "emergency", "now", "immediately"]):
                    action_lines.append(line)
            if action_lines:
                return "\n".join(action_lines[:3])
            return "\n".join(lines[:2])

        if max_length == "medium":
            return "\n".join(lines[:6])

        return text

    # ------------------------------------------------------------------
    # Format response (language-aware)
    # ------------------------------------------------------------------

    def format_response(self, clinical_answer: str, tone_tags: list[ToneTag] = None,
                        lang: str = None) -> str:
        """Format clinical answer with language-appropriate conversational tone.

        Args:
            clinical_answer: The clinical content.
            tone_tags: Override tone tags (auto-detected if None).
            lang: Override language (uses stored language if None).
        """
        if lang:
            self._lang = lang if lang in PHRASES else "pidgin"

        if tone_tags is None:
            tone_tags = self.determine_tone()

        context = self.conversation.build_clinical_context()
        emotion = context["emotion"]
        lines = []

        # Opening line based on emotion (in current language)
        if emotion == EmotionalState.ANXIOUS:
            lines.append(self._phrase("anxious_open"))
        elif emotion == EmotionalState.DISTRESSED:
            lines.append(self._phrase("distressed_open"))
        elif emotion == EmotionalState.CONFUSED:
            lines.append(self._phrase("confused_open"))
        elif emotion == EmotionalState.URGENT:
            lines.append(self._phrase("urgent_open"))
        elif emotion == EmotionalState.SKEPTICAL:
            lines.append(self._phrase("skeptical_open"))
        elif context["is_followup"]:
            topics = context["discussed_topics"]
            if topics:
                topic_str = ", ".join(topics[:3])
                lines.append(self._phrase_format("followup_topics", topics=topic_str))
            else:
                lines.append(self._phrase("followup_open"))

        # Clinical answer with adaptive length
        resp_length = self._determine_response_length(tone_tags)
        trimmed = self._trim_response(clinical_answer, resp_length)
        lines.append(trimmed)

        # Active topic context
        if resp_length in ("medium", "detailed") and context["mentioned_symptoms"]:
            symptoms = context["mentioned_symptoms"]
            if len(symptoms) >= 2:
                lines.append(self._phrase_format("topic_note", topics=", ".join(symptoms)))

        # Closing based on tone (in current language)
        if ToneTag.REASSURING in tone_tags:
            if context["is_elderly"]:
                lines.append(self._phrase("reassuring_close_elderly"))
            elif context["is_child"]:
                lines.append(self._phrase("reassuring_close_child"))
            else:
                lines.append(self._phrase("reassuring_close"))

        if ToneTag.ENCOURAGING in tone_tags:
            lines.append(self._phrase("encouraging_close"))

        if ToneTag.URGENT in tone_tags:
            lines.append(self._phrase("urgent_close"))

        if ToneTag.GENTLE in tone_tags:
            lines.append(self._phrase("gentle_close"))

        # Store healthworker response
        self.conversation.append(ClinicalMessage(
            role="healthworker",
            content=clinical_answer,
            tone_tags=tone_tags,
        ))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Smart follow-ups
    # ------------------------------------------------------------------

    def get_smart_followup_suggestions(self, current_symptoms: list[str] = None) -> list[str]:
        """Suggest follow-up questions in the current language."""
        context = self.conversation.build_clinical_context()
        suggestions = []

        if context["emotion"] in (EmotionalState.URGENT, EmotionalState.DISTRESSED):
            return suggestions

        mentioned = set(context["mentioned_symptoms"])

        if "fever" in mentioned and "cough" not in mentioned:
            suggestions.append(self._phrase("suggest_cough"))
        if "fever" in mentioned and "vomiting" not in mentioned:
            suggestions.append(self._phrase("suggest_vomit"))
        if "cough" in mentioned and "breathing" not in mentioned:
            suggestions.append(self._phrase("suggest_breathing"))
        if "diarrhoea" in mentioned and "vomiting" not in mentioned:
            suggestions.append(self._phrase("suggest_vomit"))
        if "pain" in mentioned and "fever" not in mentioned:
            suggestions.append(self._phrase("suggest_fever"))
        if "child_health" in mentioned and "diarrhoea" not in mentioned:
            suggestions.append(self._phrase("suggest_stomach"))

        return suggestions[:3]

    def get_conversation_summary(self) -> str:
        context = self.conversation.build_clinical_context()
        lines = [
            f"Conversation turns: {context['turn_count']}",
            f"Patient emotion: {context['emotion'].value}",
            f"Topics discussed: {', '.join(context['discussed_topics']) or 'none'}",
            f"Active topics: {', '.join(context['topic_stack']) or 'none'}",
            f"Language: {self._lang}",
            f"Is follow-up: {context['is_followup']}",
            f"Is repeated concern: {context['is_repeated']}",
        ]
        if context["is_elderly"]:
            lines.append("Patient is elderly (>60)")
        if context["is_child"]:
            lines.append("Patient is a child (<12)")
        return "\n".join(lines)

    def should_ask_followup(self) -> bool:
        context = self.conversation.build_clinical_context()
        if context["turn_count"] > 8:
            return False
        if context["emotion"] in (EmotionalState.URGENT, EmotionalState.DISTRESSED):
            return False
        if context["is_repeated"]:
            return False
        return True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self):
        """Save conversation to disk for persistence across sessions."""
        try:
            data = self.conversation.to_dict()
            data["_lang"] = self._lang
            data["_saved_at"] = time.time()
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Don't crash if save fails

    def load(self) -> bool:
        """Restore conversation from disk. Returns True if loaded."""
        try:
            if not os.path.isfile(self._persistence_path):
                return False
            with open(self._persistence_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Don't restore conversations older than 24 hours
            saved_at = data.get("_saved_at", 0)
            if time.time() - saved_at > 86400:
                os.remove(self._persistence_path)
                return False
            self.conversation = ClinicalConversation.from_dict(data)
            self._lang = data.get("_lang", "pidgin")
            return True
        except Exception:
            return False

    def clear_persistence(self):
        """Delete saved conversation."""
        try:
            if os.path.isfile(self._persistence_path):
                os.remove(self._persistence_path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_flow_instance: Optional[ConversationalFlow] = None


def get_conversational_flow() -> ConversationalFlow:
    global _flow_instance
    if _flow_instance is None:
        _flow_instance = ConversationalFlow()
    return _flow_instance


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("Conversational Flow Engine v3 — CLI Test\n")
    print("Features: language-aware + persistence + topic tracking + adaptive length\n")

    # Test 1: Pidgin mode
    print("=" * 60)
    print("TEST 1: Pidgin mode — anxious mother")
    print("=" * 60)
    flow = ConversationalFlow()
    flow.set_language("pidgin")
    flow.start()

    for text in ["my pikin get hot body i dey scared", "e dey vomit too"]:
        flow.process_patient_input(text)

    tone = flow.determine_tone()
    answer = flow.format_response("Paracetamol 10mg/kg. Keep hydrated.", tone)
    print(f"  {answer}\n")

    # Test 2: English mode — same scenario
    print("=" * 60)
    print("TEST 2: English mode — same scenario")
    print("=" * 60)
    flow2 = ConversationalFlow()
    flow2.set_language("en")
    flow2.start()

    for text in ["my child has fever and I'm worried", "also vomiting"]:
        flow2.process_patient_input(text)

    tone2 = flow2.determine_tone()
    answer2 = flow2.format_response("Paracetamol 10mg/kg. Keep hydrated.", tone2)
    print(f"  {answer2}\n")

    # Test 3: Persistence
    print("=" * 60)
    print("TEST 3: Persistence save/load")
    print("=" * 60)
    flow.save()
    print(f"  Saved to: {flow._persistence_path}")

    flow3 = ConversationalFlow()
    loaded = flow3.load()
    print(f"  Loaded: {loaded}")
    print(f"  Messages restored: {len(flow3.conversation.messages)}")
    print(f"  Topics restored: {flow3.conversation.get_discussed_topics()}")
    print(f"  Language restored: {flow3._lang}")
    flow3.clear_persistence()
    print("  Cleaned up persistence file.\n")

    # Test 4: Urgent — short response
    print("=" * 60)
    print("TEST 4: Urgent — adaptive short response")
    print("=" * 60)
    flow4 = ConversationalFlow()
    flow4.set_language("en")
    flow4.start()
    flow4.process_patient_input("emergency difficulty breathing now now")
    tone4 = flow4.determine_tone()
    long_answer = (
        "Difficulty breathing is serious. You should:\n"
        "1. Give sitting position\n"
        "2. Check for wheezing\n"
        "3. Give salbutamol if available\n"
        "4. Monitor for 15 minutes\n"
        "5. Refer to hospital if no improvement\n"
    )
    answer4 = flow4.format_response(long_answer, tone4)
    print(f"  {answer4}\n")

    # Test 5: Smart follow-ups in both languages
    print("=" * 60)
    print("TEST 5: Smart follow-ups")
    print("=" * 60)
    print(f"  Pidgin: {flow.get_smart_followup_suggestions()}")
    flow2.set_language("en")
    print(f"  English: {flow2.get_smart_followup_suggestions()}")
