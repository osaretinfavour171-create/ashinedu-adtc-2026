#!/usr/bin/env python3
"""Conversational flow engine for Ashinedu.

Adapted from Fish Audio's conversation.py pattern:
https://github.com/fishaudio/fish-speech/blob/main/fish_speech/conversation.py

Fish Audio uses Message(dataclass) + Conversation(list[Message]) to manage
multi-turn dialogue context. We adapt this for clinical conversations:

- Message: role (system/patient/healthworker) + content + emotional tags
- Conversation: maintains full dialogue history, builds clinical context
- ConversationalFlow: determines tone, pacing, and response style

v2 improvements (Fish Audio pattern upgrade):
- Active topic tracking: auto-detect symptoms, remember what was discussed
- Adaptive response length: short for urgent, detailed for calm
"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional
import re


# ---------------------------------------------------------------------------
# Emotional tone tags (adapted from Fish Audio's [whisper], [excited], etc.)
# ---------------------------------------------------------------------------

class ToneTag(Enum):
    """Response tone tags — adapted from Fish Audio's inline emotion control."""
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
# Patient emotional state detection
# ---------------------------------------------------------------------------

class EmotionalState(Enum):
    """Detected patient emotional state from conversation."""
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
# Message (adapted from Fish Audio's Message dataclass)
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


# ---------------------------------------------------------------------------
# Conversation (adapted from Fish Audio's Conversation class)
# ---------------------------------------------------------------------------

class ClinicalConversation:
    """Manages multi-turn clinical dialogue history with topic tracking."""

    def __init__(self, messages: list[ClinicalMessage] = None):
        self.messages: list[ClinicalMessage] = messages or []
        self._emotion_history: list[EmotionalState] = []
        self._topic_stack: list[str] = []  # Active discussion topics
        self._discussed_topics: set[str] = set()  # All topics ever mentioned
        self._mentioned_symptoms: set[str] = set()  # Symptoms already covered

    def append(self, message: ClinicalMessage):
        """Add a message and auto-track topics from patient input."""
        self.messages.append(message)
        if message.emotion:
            self._emotion_history.append(message.emotion)
        # Auto-detect topics from patient messages
        if message.role == "patient":
            topics = self._extract_topics(message.content)
            message.detected_topics = topics
            for t in topics:
                self._push_topic(t)
                self._discussed_topics.add(t)
                self._mentioned_symptoms.add(t)

    def _extract_topics(self, text: str) -> list[str]:
        """Extract symptom topics from text."""
        text_lower = text.lower()
        found = []
        for topic, keywords in SYMPTOM_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(topic)
        return found

    def _push_topic(self, topic: str):
        """Push topic to stack if not already active."""
        if topic not in self._topic_stack:
            self._topic_stack.append(topic)

    def pop_topic(self):
        """Pop the most recent topic."""
        if self._topic_stack:
            self._topic_stack.pop()

    def get_last_n(self, n: int = 5) -> list[ClinicalMessage]:
        return self.messages[-n:]

    def get_patient_messages(self) -> list[ClinicalMessage]:
        return [m for m in self.messages if m.role == "patient"]

    def get_discussed_topics(self) -> list[str]:
        """Get all topics that have been discussed."""
        return list(self._discussed_topics)

    def get_unmentioned_symptoms(self, query_symptoms: list[str]) -> list[str]:
        """For a given set of query symptoms, return ones NOT yet discussed.
        
        This enables smart follow-ups: if the patient mentioned fever and
        we know malaria often comes with headache, we can ask about headache.
        """
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
        """Build rich clinical context from conversation history."""
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
    # Conversation state
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
# Conversational Flow Engine (the main adapter)
# ---------------------------------------------------------------------------

class ConversationalFlow:
    """Adapts Fish Audio's conversational patterns for clinical dialogue.

    v2 improvements:
    - Active topic tracking: auto-detect and remember symptoms
    - Adaptive response length: short for urgent, detailed for calm
    """

    def __init__(self):
        self.conversation = ClinicalConversation()

    def start(self):
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
    # Adaptive response length (Fish Audio pattern)
    # ------------------------------------------------------------------

    def _determine_response_length(self, tone_tags: list[ToneTag]) -> str:
        """Determine how detailed the response should be.

        Fish Audio adapts response pacing based on context:
        - Urgent: short, punchy, action-oriented
        - Calm/educational: longer, explanatory
        - Confused: medium, with examples
        """
        if ToneTag.URGENT in tone_tags:
            return "short"      # 1-2 sentences max
        if ToneTag.DIRECT in tone_tags:
            return "medium"     # 2-3 sentences
        if ToneTag.SIMPLE in tone_tags:
            return "medium"     # Simple but complete
        if ToneTag.GENTLE in tone_tags:
            return "detailed"   # Thorough, patient
        if ToneTag.PROFESSIONAL in tone_tags:
            return "detailed"   # Full clinical detail
        return "medium"

    def _trim_response(self, text: str, max_length: str) -> str:
        """Trim a response to match the target length.

        If the answer is too long for an urgent situation,
        extract only the most critical lines.
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        if max_length == "short":
            # Keep only lines with action words (give, take, refer, go)
            action_lines = []
            for line in lines:
                lower = line.lower()
                if any(w in lower for w in ["give", "take", "refer", "go", "hospital",
                                             "dose", "mg", "paracetamol", "act", "ors",
                                             "emergency", "now", "immediately"]):
                    action_lines.append(line)
            if action_lines:
                return "\n".join(action_lines[:3])
            # Fallback: just the first 2 lines
            return "\n".join(lines[:2])

        if max_length == "medium":
            return "\n".join(lines[:6])

        # detailed — return everything
        return text

    def format_response(self, clinical_answer: str, tone_tags: list[ToneTag] = None) -> str:
        """Format a clinical answer with adaptive tone and length."""
        if tone_tags is None:
            tone_tags = self.determine_tone()

        context = self.conversation.build_clinical_context()
        emotion = context["emotion"]
        lines = []

        # --- Opening line based on emotion ---
        if emotion == EmotionalState.ANXIOUS:
            lines.append("No worry, I dey help you. Make we look into this together.\n")
        elif emotion == EmotionalState.DISTRESSED:
            lines.append("I understand say you dey suffer. Make I help you with this.\n")
        elif emotion == EmotionalState.CONFUSED:
            lines.append("No worry, I go explain am well well for you.\n")
        elif emotion == EmotionalState.URGENT:
            lines.append("I hear you. Make we act quick.\n")
        elif emotion == EmotionalState.SKEPTICAL:
            lines.append("I understand your concern. Make I explain the evidence.\n")
        elif context["is_followup"]:
            # Active topic awareness: mention what we already discussed
            topics = context["discussed_topics"]
            if topics:
                topic_str = ", ".join(topics[:3])
                lines.append(f"I don note say we talk about {topic_str} before.\n")
            else:
                lines.append("Okay, I don note wetin you talk before.\n")

        # --- Clinical answer (with adaptive length) ---
        resp_length = self._determine_response_length(tone_tags)
        trimmed = self._trim_response(clinical_answer, resp_length)
        lines.append(trimmed)

        # --- Active topic context: suggest what else to check ---
        if resp_length in ("medium", "detailed") and context["mentioned_symptoms"]:
            symptoms = context["mentioned_symptoms"]
            if len(symptoms) >= 2:
                lines.append(f"\nNote: {', '.join(symptoms)} fit dey related.")

        # --- Closing based on tone ---
        if ToneTag.REASSURING in tone_tags:
            if context["is_elderly"]:
                lines.append("\nYou go dey alright. Just follow wetin I talk.")
            elif context["is_child"]:
                lines.append("\nYour pikin go dey alright. Just follow the medicine.")
            else:
                lines.append("\nYou go dey alright. Just follow the treatment.")

        if ToneTag.ENCOURAGING in tone_tags:
            lines.append("\nIf e no dey better in 2-3 days, come back make we check am again.")

        if ToneTag.URGENT in tone_tags:
            lines.append("\nIf e dey worse, go hospital now now. No wait!")

        if ToneTag.GENTLE in tone_tags:
            lines.append("\nTake your time. If you get any question, ask me.")

        # Store the healthworker response
        self.conversation.append(ClinicalMessage(
            role="healthworker",
            content=clinical_answer,
            tone_tags=tone_tags,
        ))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Smart follow-ups based on topic tracking
    # ------------------------------------------------------------------

    def get_smart_followup_suggestions(self, current_symptoms: list[str] = None) -> list[str]:
        """Suggest follow-up questions based on what hasn't been discussed yet.

        Uses active topic tracking to avoid re-asking about things already covered.
        Returns suggested questions the healthworker could ask.
        """
        context = self.conversation.build_clinical_context()
        suggestions = []

        # Don't suggest if patient is urgent/distressed
        if context["emotion"] in (EmotionalState.URGENT, EmotionalState.DISTRESSED):
            return suggestions

        mentioned = set(context["mentioned_symptoms"])

        # Suggest related symptoms that haven't been mentioned
        if "fever" in mentioned and "cough" not in mentioned:
            suggestions.append("E dey cough?")
        if "fever" in mentioned and "vomiting" not in mentioned:
            suggestions.append("E dey vomit?")
        if "cough" in mentioned and "breathing" not in mentioned:
            suggestions.append("E dey find am hard to breathe?")
        if "diarrhoea" in mentioned and "vomiting" not in mentioned:
            suggestions.append("E dey vomit too?")
        if "pain" in mentioned and "fever" not in mentioned:
            suggestions.append("E get fever?")
        if "child_health" in mentioned and "diarrhoea" not in mentioned:
            suggestions.append("Stomach dey run?")

        return suggestions[:3]  # Max 3 suggestions

    def get_conversation_summary(self) -> str:
        context = self.conversation.build_clinical_context()
        lines = [
            f"Conversation turns: {context['turn_count']}",
            f"Patient emotion: {context['emotion'].value}",
            f"Topics discussed: {', '.join(context['discussed_topics']) or 'none'}",
            f"Active topics: {', '.join(context['topic_stack']) or 'none'}",
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

    flow = ConversationalFlow()
    flow.start()

    print("Conversational Flow Engine v2 — CLI Test\n")
    print("Features: active topic tracking + adaptive response length\n")

    # Test 1: Anxious mother
    print("=" * 60)
    print("TEST 1: Anxious mother with sick child")
    print("=" * 60)
    msgs = [
        "my pikin get hot body i dey scared",
        "e dey vomit too",
        "is it serious? please help me",
    ]
    for text in msgs:
        msg = flow.process_patient_input(text)
        print(f"  Patient: {text}")
        print(f"    Emotion: {msg.emotion.value} | Topics: {msg.detected_topics}")

    tone = flow.determine_tone()
    print(f"\n  Tone: {[t.value for t in tone]}")
    print(f"  Topics discussed: {flow.conversation.get_discussed_topics()}")
    answer = flow.format_response("Paracetamol 10mg/kg. Keep hydrated. ORS if diarrhoea.", tone)
    print(f"\n  Response:\n{answer}\n")

    # Test 2: Smart follow-ups
    print("=" * 60)
    print("TEST 2: Smart follow-up suggestions")
    print("=" * 60)
    suggestions = flow.get_smart_followup_suggestions()
    print(f"  Suggestions: {suggestions}\n")

    # Test 3: Urgent (adaptive length)
    print("=" * 60)
    print("TEST 3: Urgent — short response")
    print("=" * 60)
    flow2 = ConversationalFlow()
    flow2.start()
    flow2.process_patient_input("emergency difficulty breathing now now")
    tone2 = flow2.determine_tone()
    print(f"  Tone: {[t.value for t in tone2]}")
    long_answer = (
        "Difficulty breathing is a serious symptom. You should:\n"
        "1. Give the patient a sitting position\n"
        "2. Check if there is wheezing\n"
        "3. If the patient is a child, give salbutamol inhaler\n"
        "4. Monitor oxygen levels if possible\n"
        "5. If no improvement in 15 minutes, refer to hospital\n"
        "6. Give paracetamol for any fever\n"
        "7. Keep the patient calm\n"
    )
    answer2 = flow2.format_response(long_answer, tone2)
    print(f"\n  Response (trimmed for urgency):\n{answer2}\n")

    # Test 4: Topic tracking across conversation
    print("=" * 60)
    print("TEST 4: Topic tracking across turns")
    print("=" * 60)
    flow3 = ConversationalFlow()
    flow3.start()
    turns = [
        "i get headache and fever",
        "e dey vomit too",
        "i dey feel dizzy",
    ]
    for text in turns:
        flow3.process_patient_input(text)
    ctx = flow3.conversation.build_clinical_context()
    print(f"  Topics discussed: {ctx['discussed_topics']}")
    print(f"  Active topics: {ctx['topic_stack']}")
    print(f"  Mentioned symptoms: {ctx['mentioned_symptoms']}")
