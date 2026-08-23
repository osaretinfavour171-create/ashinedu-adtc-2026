#!/usr/bin/env python3
"""Conversational flow engine for Ashinedu.

Adapted from Fish Audio's conversation.py pattern:
https://github.com/fishaudio/fish-speech/blob/main/fish_speech/conversation.py

Fish Audio uses Message(dataclass) + Conversation(list[Message]) to manage
multi-turn dialogue context. We adapt this for clinical conversations:

- Message: role (system/patient/healthworker) + content + emotional tags
- Conversation: maintains full dialogue history, builds clinical context
- ConversationalFlow: determines tone, pacing, and response style

Key difference from Fish Audio: we don't generate audio tokens, we generate
clinical response styles. The conversation context drives HOW we respond,
not WHAT we say (that comes from the knowledge graph).
"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional
import re


# ---------------------------------------------------------------------------
# Emotional tone tags (adapted from Fish Audio's [whisper], [excited], etc.)
# Fish Audio: [whisper] [excited] [angry] [pause] [emphasis]
# Ashinedu:  [calm] [reassuring] [urgent] [gentle] [simple] [professional]
# ---------------------------------------------------------------------------

class ToneTag(Enum):
    """Response tone tags — adapted from Fish Audio's inline emotion control."""
    CALM = "calm"                    # Reassuring, not panicking
    REASSURING = "reassuring"        # Comforting an anxious patient
    URGENT = "urgent"                # Emergency — act now
    GENTLE = "gentle"                # Elderly/children — slow, simple
    SIMPLE = "simple"                # Low literacy — plain language
    PROFESSIONAL = "professional"    # CHEW-to-CHEW communication
    EMPATHETIC = "empathetic"        # Emotional pain, mental health
    DIRECT = "direct"                # Clear instructions, no fluff
    ENCOURAGING = "encouraging"      # Motivating follow-through


# ---------------------------------------------------------------------------
# Patient emotional state detection
# ---------------------------------------------------------------------------

class EmotionalState(Enum):
    """Detected patient emotional state from conversation."""
    ANXIOUS = "anxious"          # Worried, asking many questions
    CALM = "calm"                # Normal consultation
    DISTRESSED = "distressed"    # In pain, upset
    CONFUSED = "confused"        # Doesn't understand
    URGENT = "urgent"            # Emergency situation
    DEFERRING = "deferring"      # Trusting, just wants answer
    SKEPTICAL = "skeptical"      # Questioning the advice


# Emotional keywords for detection (adapted from Fish Audio's tag detection)
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
# Message (adapted from Fish Audio's Message dataclass)
# ---------------------------------------------------------------------------

@dataclass
class ClinicalMessage:
    """A single message in the clinical conversation.

    Adapted from Fish Audio's Message:
    - role: who said it (system/patient/healthworker)
    - content: what was said
    - tone_tags: emotional tone markers (like Fish Audio's [whisper], [excited])
    - emotion: detected emotional state
    - metadata: clinical context (symptoms, conditions, etc.)
    """
    role: Literal["system", "patient", "healthworker"]
    content: str
    tone_tags: list[ToneTag] = field(default_factory=list)
    emotion: Optional[EmotionalState] = None
    metadata: dict = field(default_factory=dict)
    timestamp: float = 0.0

    def add_tone(self, tag: ToneTag):
        """Add a tone tag (like Fish Audio's inline [tag] syntax)."""
        if tag not in self.tone_tags:
            self.tone_tags.append(tag)

    def has_tone(self, tag: ToneTag) -> bool:
        return tag in self.tone_tags


# ---------------------------------------------------------------------------
# Conversation (adapted from Fish Audio's Conversation class)
# ---------------------------------------------------------------------------

class ClinicalConversation:
    """Manages multi-turn clinical dialogue history.

    Adapted from Fish Audio's Conversation:
    - Maintains list of Messages (like Fish Audio's self.messages)
    - Builds context from conversation history
    - Tracks emotional arc across turns
    - Determines appropriate response tone

    Fish Audio builds ContentSequence from messages for token encoding.
    We build ClinicalContext from messages for response style adaptation.
    """

    def __init__(self, messages: list[ClinicalMessage] = None):
        self.messages: list[ClinicalMessage] = messages or []
        self._emotion_history: list[EmotionalState] = []
        self._topic_stack: list[str] = []  # What we're discussing

    def append(self, message: ClinicalMessage):
        """Add a message to the conversation (like Fish Audio's append)."""
        self.messages.append(message)
        if message.emotion:
            self._emotion_history.append(message.emotion)

    def get_last_n(self, n: int = 5) -> list[ClinicalMessage]:
        """Get the last N messages for context window."""
        return self.messages[-n:]

    def get_patient_messages(self) -> list[ClinicalMessage]:
        """Get all patient messages for emotion tracking."""
        return [m for m in self.messages if m.role == "patient"]

    def get_system_messages(self) -> list[ClinicalMessage]:
        """Get all system/healthworker messages."""
        return [m for m in self.messages if m.role in ("system", "healthworker")]

    # ------------------------------------------------------------------
    # Emotion tracking (adapted from Fish Audio's multi-turn context)
    # ------------------------------------------------------------------

    def detect_emotion(self, text: str) -> EmotionalState:
        """Detect emotional state from patient text.

        Like Fish Audio detects emotion from speech features,
        we detect it from text patterns.
        """
        text_lower = text.lower()
        scores = {}

        for emotion, patterns in EMOTION_PATTERNS.items():
            score = sum(1 for p in patterns if p in text_lower)
            if score > 0:
                scores[emotion] = score

        if not scores:
            return EmotionalState.CALM

        # Return the strongest detected emotion
        return max(scores, key=scores.get)

    def get_emotional_arc(self) -> EmotionalState:
        """Get the current emotional trajectory of the conversation.

        Like Fish Audio uses previous turns to improve expressiveness,
        we use emotion history to determine current tone.
        """
        if not self._emotion_history:
            return EmotionalState.CALM

        # Recent emotions weigh more (last 3 messages)
        recent = self._emotion_history[-3:]

        # If any recent message is urgent/distressed, prioritize that
        if EmotionalState.URGENT in recent:
            return EmotionalState.URGENT
        if EmotionalState.DISTRESSED in recent:
            return EmotionalState.DISTRESSED
        if EmotionalState.ANXIOUS in recent:
            return EmotionalState.ANXIOUS

        # Default to the most common recent emotion
        from collections import Counter
        counts = Counter(recent)
        return counts.most_common(1)[0][0]

    # ------------------------------------------------------------------
    # Context building (adapted from Fish Audio's _build_content_sequence)
    # ------------------------------------------------------------------

    def build_clinical_context(self) -> dict:
        """Build clinical context from conversation history.

        Like Fish Audio builds ContentSequence from messages for the model,
        we build a context dict for the response formatter.
        """
        emotion = self.get_emotional_arc()
        turn_count = len(self.messages)
        patient_msgs = self.get_patient_messages()

        # Detect if patient is asking follow-up vs new complaint
        is_followup = turn_count > 2
        is_repeated = self._is_repeated_concern()

        # Determine patient characteristics from conversation
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
        }

    def _is_repeated_concern(self) -> bool:
        """Check if patient is repeating the same concern."""
        patient_msgs = self.get_patient_messages()
        if len(patient_msgs) < 2:
            return False
        # Simple check: do the last 2 patient messages share significant words?
        words1 = set(patient_msgs[-1].content.lower().split())
        words2 = set(patient_msgs[-2].content.lower().split())
        overlap = words1 & words2
        # If more than 40% of words overlap, it's likely repeated
        if len(words1) > 0 and len(overlap) / len(words1) > 0.4:
            return True
        return False

    def push_topic(self, topic: str):
        self._topic_stack.append(topic)

    def pop_topic(self):
        if self._topic_stack:
            self._topic_stack.pop()

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

    def __len__(self):
        return len(self.messages)

    def __repr__(self):
        return f"ClinicalConversation({len(self.messages)} messages)"


# ---------------------------------------------------------------------------
# Conversational Flow Engine (the main adapter)
# ---------------------------------------------------------------------------

class ConversationalFlow:
    """Adapts Fish Audio's conversational patterns for clinical dialogue.

    Fish Audio's key insight: previous conversation context improves
    the expressiveness of subsequent responses. We apply this to clinical
    conversations: the patient's emotional state, history, and conversation
    flow determine HOW we respond.

    This module determines the tone and style.
    The knowledge graph determines the clinical content.
    Together they produce natural, adaptive clinical responses.
    """

    def __init__(self):
        self.conversation = ClinicalConversation()

    def start(self):
        """Start a new conversation."""
        self.conversation.clear()
        self.conversation.append(ClinicalMessage(
            role="system",
            content="Clinical consultation started.",
            tone_tags=[ToneTag.PROFESSIONAL],
        ))

    def process_patient_input(self, text: str, metadata: dict = None) -> ClinicalMessage:
        """Process patient input and detect emotional state."""
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
        """Determine the appropriate response tone based on conversation context.

        Like Fish Audio uses previous turns to determine expressiveness,
        we use the emotional arc to determine clinical communication style.
        """
        context = self.conversation.build_clinical_context()
        emotion = context["emotion"]
        tags = []

        # Emergency situations → urgent, direct
        if emotion == EmotionalState.URGENT:
            tags.extend([ToneTag.URGENT, ToneTag.DIRECT])

        # Distressed patients → calm, reassuring
        elif emotion == EmotionalState.DISTRESSED:
            tags.extend([ToneTag.CALM, ToneTag.REASSURING])

        # Anxious patients → reassuring, empathetic
        elif emotion == EmotionalState.ANXIOUS:
            tags.extend([ToneTag.REASSURING, ToneTag.EMPATHETIC])

        # Confused patients → simple, gentle
        elif emotion == EmotionalState.CONFUSED:
            tags.extend([ToneTag.SIMPLE, ToneTag.GENTLE])

        # Skeptical patients → professional, evidence-based
        elif emotion == EmotionalState.SKEPTICAL:
            tags.extend([ToneTag.PROFESSIONAL, ToneTag.DIRECT])

        # Default → professional
        else:
            tags.append(ToneTag.PROFESSIONAL)

        # Age-based adjustments
        if context["is_elderly"]:
            tags.append(ToneTag.GENTLE)
            if ToneTag.SIMPLE not in tags:
                tags.append(ToneTag.SIMPLE)

        if context["is_child"]:
            tags.append(ToneTag.GENTLE)

        # Follow-up adjustments
        if context["is_followup"] and context["is_repeated"]:
            # Patient is repeating concern → be more reassuring
            tags.append(ToneTag.REASSURING)
            tags.append(ToneTag.ENCOURAGING)

        return list(dict.fromkeys(tags))  # Deduplicate, preserve order

    def format_response(self, clinical_answer: str, tone_tags: list[ToneTag] = None) -> str:
        """Format a clinical answer with appropriate conversational tone.

        Like Fish Audio injects [whisper], [excited] tags into generated speech,
        we inject conversational elements into clinical responses.
        """
        if tone_tags is None:
            tone_tags = self.determine_tone()

        context = self.conversation.build_clinical_context()
        lines = []

        # Opening line based on emotion
        emotion = context["emotion"]
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
            lines.append("Okay, I don note wetin you talk before.\n")

        # Add the clinical answer
        lines.append(clinical_answer)

        # Closing based on tone
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

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation for the LLM context."""
        context = self.conversation.build_clinical_context()
        lines = [
            f"Conversation turns: {context['turn_count']}",
            f"Patient emotion: {context['emotion'].value}",
            f"Is follow-up: {context['is_followup']}",
            f"Is repeated concern: {context['is_repeated']}",
        ]
        if context["is_elderly"]:
            lines.append("Patient is elderly (>60)")
        if context["is_child"]:
            lines.append("Patient is a child (<12)")
        return "\n".join(lines)

    def should_ask_followup(self) -> bool:
        """Determine if we should ask follow-up questions.

        Like Fish Audio uses multi-turn context to improve responses,
        we use conversation history to know when to probe deeper.
        """
        context = self.conversation.build_clinical_context()

        # Don't ask too many follow-ups
        if context["turn_count"] > 8:
            return False

        # If patient is distressed/urgent, give answer first
        if context["emotion"] in (EmotionalState.URGENT, EmotionalState.DISTRESSED):
            return False

        # If it's a repeated concern, they want an answer, not more questions
        if context["is_repeated"]:
            return False

        return True


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_flow_instance: Optional[ConversationalFlow] = None


def get_conversational_flow() -> ConversationalFlow:
    """Get or create the singleton conversational flow engine."""
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

    print("Conversational Flow Engine — CLI Test\n")

    # Simulate a conversation
    test_conversations = [
        # Anxious patient
        [
            ("patient", "my pikin get hot body i dey scared"),
            ("patient", "e dey vomit too"),
            ("patient", "is it serious? please help me"),
        ],
        # Calm patient with follow-up
        [
            ("patient", "i get headache"),
            ("patient", "the headache still dey"),
            ("patient", "i don take paracetamol e no work"),
        ],
        # Elderly patient
        [
            ("patient", "my mama knee dey pain she be 70 years"),
            ("patient", "e dey swell too"),
        ],
    ]

    for conv in test_conversations:
        print(f"{'='*60}")
        for role, text in conv:
            if role == "patient":
                msg = flow.process_patient_input(text)
                print(f"Patient: {text}")
                print(f"  Emotion: {msg.emotion.value}")
            else:
                print(f"Healthworker: {text}")

        tone = flow.determine_tone()
        print(f"\nDetermined tone: {[t.value for t in tone]}")

        # Format a sample clinical answer
        sample_answer = "Paracetamol 10mg/kg every 4-6 hours. Keep the child hydrated."
        formatted = flow.format_response(sample_answer, tone)
        print(f"\nFormatted response:\n{formatted}")
        print()
