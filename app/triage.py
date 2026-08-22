"""Smart Triage Engine for Ashinedu.

Instead of asking 13 generic questions for every complaint, this system:
  1. Detects the condition type from the initial query
  2. Asks ONLY the questions that matter for THAT condition
  3. Scores severity based on answers
  4. Routes to the right treatment path: conservative care, drugs, or referral

This is how a real CHEW works:
  - "I get cold" → Ask about fever, breathing, duration → Usually rest + water
  - "My head dey pain" → Ask about severity, fever, neck stiffness → May need paracetamol or refer
  - "I dey tired" → Ask about duration, weight loss, fever → Could be anaemia, TB, or just stress

Decision graph:
  Query → Detect Condition → Ask Targeted Questions → Score Severity → Route

Each condition has:
  - A set of CONDITION-SPECIFIC questions (not generic ones)
  - Severity thresholds that determine the treatment path
  - A decision function that maps answers to outcomes
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Callable


# ---------------------------------------------------------------------------
# Triage question definitions
# ---------------------------------------------------------------------------

@dataclass
class TriageQuestion:
    """A single triage question with parser."""
    key: str
    prompt_pidgin: str
    prompt_english: str
    parser: str          # "yes_no", "severity", "duration", "temperature", "text"
    weight: float = 1.0  # How much this question affects severity score


@dataclass
class TriagePathway:
    """Defines the questions and decision logic for a condition type."""
    name: str
    questions: list[TriageQuestion]

    # Severity thresholds (score ranges → treatment path)
    # Each threshold is (max_score, treatment_path)
    thresholds: list[tuple[float, str]] = field(default_factory=list)

    # Decision function: takes all answers, returns treatment path
    decision_fn: Optional[Callable] = None


# ---------------------------------------------------------------------------
# Parser functions
# ---------------------------------------------------------------------------

def _parse_yes_no(text: str) -> Optional[bool]:
    """Parse yes/no answer."""
    t = text.lower().strip()
    if any(w in t for w in ("yes", "yeah", "yes o", "na so", "true", "dey", "e dey")):
        return True
    if any(w in t for w in ("no", "no o", "no way", "false", "no dey", "e no dey")):
        return False
    return None


def _parse_severity(text: str) -> float:
    """Parse severity description into a 0-1 score."""
    t = text.lower().strip()
    # High severity
    if any(w in t for w in ("very", "extreme", "severe", "terrible", "worst",
                              "unbearable", "can't", "cant", "no fit",
                              "serious", "very bad", "too much")):
        return 1.0
    # Moderate severity
    if any(w in t for w in ("bad", "strong", "dey worry", "dey pain",
                              "moderate", "noticeable")):
        return 0.6
    # Mild severity
    if any(w in t for w in ("small", "mild", "little", "light",
                              "manageable", "e dey OK", "not too bad")):
        return 0.3
    # No/minimal
    if any(w in t for w in ("no", "nothing", "fine", "normal", "okay")):
        return 0.0
    return 0.3  # Default mild


def _parse_duration(text: str) -> float:
    """Parse duration into severity weight (longer = potentially more serious)."""
    t = text.lower().strip()
    # Acute (< 3 days) = low concern
    if any(w in t for w in ("today", "just now", "this morning", "few hours")):
        return 0.1
    if any(w in t for w in ("yesterday", "1 day", "one day", "2 days")):
        return 0.2
    # Subacute (3-7 days) = moderate concern
    if any(w in t for w in ("3 days", "4 days", "5 days", "a week",
                              "few days", "some days", "since last week")):
        return 0.5
    # Chronic (> 1 week) = higher concern
    if any(w in t for w in ("2 weeks", "weeks", "month", "months",
                              "long time", "很久", "for ages")):
        return 0.8
    return 0.3


def _parse_temperature(text: str) -> float:
    """Parse temperature reading into severity weight."""
    t = text.lower().strip()
    m = re.search(r"(\d{2,3}(?:\.\d+)?)", t)
    if m:
        temp = float(m.group(1))
        if temp >= 40.0:
            return 1.0   # Very high
        elif temp >= 38.5:
            return 0.7   # High
        elif temp >= 37.5:
            return 0.4   # Low-grade
        else:
            return 0.0   # Normal
    # Qualitative
    if any(w in t for w in ("very hot", "high", "too much")):
        return 0.8
    if any(w in t for w in ("hot", "warm", "mild")):
        return 0.4
    return 0.0


def _parse_text(text: str) -> str:
    """Just return the text as-is."""
    return text.strip()


PARSERS = {
    "yes_no": _parse_yes_no,
    "severity": _parse_severity,
    "duration": _parse_duration,
    "temperature": _parse_temperature,
    "text": _parse_text,
}


# ---------------------------------------------------------------------------
# Condition-specific pathways
# ---------------------------------------------------------------------------

# Each condition defines: which questions to ask, and how to decide the treatment.

TRIAGE_PATHWAYS = {
    # ======================================================================
    # COMMON COLD / UPPER RESPIRATORY
    # ======================================================================
    "cold": TriagePathway(
        name="cold",
        questions=[
            TriageQuestion(
                key="has_fever",
                prompt_pidgin="E get fever? (body dey hot?)",
                prompt_english="Is there a fever? (Is the body hot?)",
                parser="yes_no",
                weight=2.0,  # Fever significantly changes management
            ),
            TriageQuestion(
                key="breathing",
                prompt_pidgin="E dey breathe well? Or e dey find it hard to breathe?",
                prompt_english="Is the patient breathing normally, or having difficulty?",
                parser="yes_no",
                weight=3.0,  # Breathing difficulty = escalate immediately
            ),
            TriageQuestion(
                key="duration",
                prompt_pidgin="How long e don dey like this?",
                prompt_english="How long has this been going on?",
                parser="duration",
                weight=1.0,
            ),
            TriageQuestion(
                key="eating_drinking",
                prompt_pidgin="E dey chop and drink? Or e no want?",
                prompt_english="Is the patient eating and drinking, or refusing food/fluids?",
                parser="yes_no",
                weight=1.5,
            ),
        ],
        decision_fn=lambda answers: (
            "refer" if answers.get("breathing") is True
            else "drugs" if answers.get("has_fever") is True
            else "conservative"
        ),
    ),

    # ======================================================================
    # HEADACHE
    # ======================================================================
    "headache": TriagePathway(
        name="headache",
        questions=[
            TriageQuestion(
                key="severity",
                prompt_pidgin="How e dey? Mild, moderate, or e dey very bad?",
                prompt_english="How bad is the headache? Mild, moderate, or severe?",
                parser="severity",
                weight=2.0,
            ),
            TriageQuestion(
                key="fever_stiff_neck",
                prompt_pidgin="E get fever plus neck dey stiff? (e no fit turn neck?)",
                prompt_english="Is there fever plus stiff neck? (Can't turn the neck?)",
                parser="yes_no",
                weight=3.0,  # Meningitis red flag
            ),
            TriageQuestion(
                key="vomiting",
                prompt_pidgin="E dey vomit?",
                prompt_english="Is the patient vomiting?",
                parser="yes_no",
                weight=2.0,
            ),
            TriageQuestion(
                key="duration",
                prompt_pidgin="How long e don dey like this?",
                prompt_english="How long has the headache lasted?",
                parser="duration",
                weight=1.0,
            ),
        ],
        decision_fn=lambda answers: (
            "refer" if answers.get("fever_stiff_neck") is True
            else "refer" if answers.get("vomiting") is True and answers.get("severity", 0) > 0.6
            else "drugs" if answers.get("severity", 0) > 0.5
            else "conservative"
        ),
    ),

    # ======================================================================
    # FATIGUE / Tiredness / WEAKNESS
    # ======================================================================
    "fatigue": TriagePathway(
        name="fatigue",
        questions=[
            TriageQuestion(
                key="duration",
                prompt_pidgin="How long you don dey feel like this?",
                prompt_english="How long have you felt this way?",
                parser="duration",
                weight=2.0,
            ),
            TriageQuestion(
                key="weight_loss",
                prompt_pidgin="You don loss weight? Or e dey same?",
                prompt_english="Have you lost weight recently, or stayed the same?",
                parser="yes_no",
                weight=2.0,
            ),
            TriageQuestion(
                key="night_sweats",
                prompt_pidgin="You dey sweat for night? (even when e no dey hot?)",
                prompt_english="Do you sweat at night? (even when it's not hot?)",
                parser="yes_no",
                weight=2.0,
            ),
            TriageQuestion(
                key="fever",
                prompt_pidgin="You get any fever? (body dey hot?)",
                prompt_english="Any fever? (Is the body hot?)",
                parser="yes_no",
                weight=1.5,
            ),
            TriageQuestion(
                key="eating",
                prompt_pidgin="You dey chop well? Or no want food?",
                prompt_english="Are you eating well, or lost appetite?",
                parser="yes_no",
                weight=1.0,
            ),
        ],
        decision_fn=lambda answers: (
            "refer" if (answers.get("weight_loss") is True and
                        answers.get("night_sweats") is True)
            else "refer" if (answers.get("fever") is True and
                             answers.get("duration", 0) > 0.5)
            else "drugs" if (answers.get("fever") is True or
                             answers.get("duration", 0) > 0.5)
            else "conservative"
        ),
    ),

    # ======================================================================
    # DEHYDRATION / DIARRHOEA / VOMITING
    # ======================================================================
    "dehydration": TriagePathway(
        name="dehydration",
        questions=[
            TriageQuestion(
                key="can_drink",
                prompt_pidgin="E fit drink? Or e no fit keep water?",
                prompt_english="Can the patient drink, or can't keep fluids down?",
                parser="yes_no",
                weight=3.0,
            ),
            TriageQuestion(
                key="urine",
                prompt_pidgin="E still dey wee-wee? Or e no dey come out?",
                prompt_english="Is the patient still passing urine, or stopped?",
                parser="yes_no",
                weight=2.5,
            ),
            TriageQuestion(
                key="severity",
                prompt_pidgin="How e dey now? E still dey walk? Or e dey weak well well?",
                prompt_english="How is the patient now? Still walking, or very weak?",
                parser="severity",
                weight=2.0,
            ),
            TriageQuestion(
                key="blood",
                prompt_pidgin="You see any blood for vomit or stool?",
                prompt_english="Any blood in vomit or stool?",
                parser="yes_no",
                weight=3.0,
            ),
        ],
        decision_fn=lambda answers: (
            "refer" if answers.get("blood") is True
            else "refer" if answers.get("can_drink") is False
            else "refer" if answers.get("urine") is False
            else "drugs" if answers.get("severity", 0) > 0.6
            else "conservative"
        ),
    ),

    # ======================================================================
    # MUSCLE / BODY PAIN (non-joint)
    # ======================================================================
    "body_pain": TriagePathway(
        name="body_pain",
        questions=[
            TriageQuestion(
                key="severity",
                prompt_pidgin="How e dey pain? Mild or e dey very bad?",
                prompt_english="How severe is the pain? Mild or very bad?",
                parser="severity",
                weight=2.0,
            ),
            TriageQuestion(
                key="fever",
                prompt_pidgin="E get fever?",
                prompt_english="Is there a fever?",
                parser="yes_no",
                weight=1.5,
            ),
            TriageQuestion(
                key="swelling",
                prompt_pidgin="Any swelling? Or e dey red/hot for one place?",
                prompt_english="Any swelling, redness, or warmth in one area?",
                parser="yes_no",
                weight=2.0,
            ),
            TriageQuestion(
                key="cause",
                prompt_pidgin="Wetin you think cause am? Exercise? Work? Injury?",
                prompt_english="What do you think caused it? Exercise? Work? Injury?",
                parser="text",
                weight=0.5,
            ),
        ],
        decision_fn=lambda answers: (
            "refer" if (answers.get("swelling") is True and
                        answers.get("fever") is True)
            else "drugs" if answers.get("severity", 0) > 0.5
            else "conservative"
        ),
    ),

    # ======================================================================
    # STRESS / MENTAL HEALTH
    # ======================================================================
    "stress": TriagePathway(
        name="stress",
        questions=[
            TriageQuestion(
                key="duration",
                prompt_pidgin="How long you don dey feel like this?",
                prompt_english="How long have you felt this way?",
                parser="duration",
                weight=2.0,
            ),
            TriageQuestion(
                key="sleep",
                prompt_pidgin="You dey sleep well? Or you no fit sleep?",
                prompt_english="Are you sleeping well, or can't sleep?",
                parser="yes_no",
                weight=1.5,
            ),
            TriageQuestion(
                key="appetite",
                prompt_pidgin="You dey chop well? Or no want food?",
                prompt_english="Are you eating well, or lost appetite?",
                parser="yes_no",
                weight=1.0,
            ),
            TriageQuestion(
                key="hopeless",
                prompt_pidgin="You ever feel like life no dey worth am? Or you wan hurt yourself?",
                prompt_english="Have you ever felt life isn't worth living, or thought about hurting yourself?",
                parser="yes_no",
                weight=3.0,  # Suicidal ideation = immediate referral
            ),
        ],
        decision_fn=lambda answers: (
            "refer" if answers.get("hopeless") is True
            else "refer" if (answers.get("duration", 0) > 0.7 and
                             answers.get("sleep") is False and
                             answers.get("appetite") is False)
            else "conservative"
        ),
    ),

    # ======================================================================
    # HEAT / SUN EXPOSURE
    # ======================================================================
    "heat": TriagePathway(
        name="heat",
        questions=[
            TriageQuestion(
                key="conscious",
                prompt_pidgin="E still dey talk and know wetin dey happen? Or e dey confuse?",
                prompt_english="Is the patient still alert and talking, or confused?",
                parser="yes_no",
                weight=3.0,
            ),
            TriageQuestion(
                key="temperature",
                prompt_pidgin="You get thermometer? How e dey?",
                prompt_english="Do you have a thermometer? What does it read?",
                parser="temperature",
                weight=2.0,
            ),
            TriageQuestion(
                key="sweating",
                prompt_pidgin="E still dey sweat? Or e don stop?",
                prompt_english="Is the patient still sweating, or stopped?",
                parser="yes_no",
                weight=2.0,
            ),
        ],
        decision_fn=lambda answers: (
            "refer" if answers.get("conscious") is False
            else "refer" if (answers.get("temperature", 0) >= 0.8 and
                             answers.get("sweating") is False)
            else "conservative"
        ),
    ),

    # ======================================================================
    # STOMACH / ABDOMINAL
    # ======================================================================
    "stomach": TriagePathway(
        name="stomach",
        questions=[
            TriageQuestion(
                key="severity",
                prompt_pidgin="How e dey pain? Small or e dey very bad?",
                prompt_english="How severe is the pain? Mild or very bad?",
                parser="severity",
                weight=2.0,
            ),
            TriageQuestion(
                key="blood",
                prompt_pidgin="You see any blood for vomit or poo?",
                prompt_english="Any blood in vomit or stool?",
                parser="yes_no",
                weight=3.0,
            ),
            TriageQuestion(
                key="can_drink",
                prompt_pidgin="E fit drink water? Or e dey vomit everything?",
                prompt_english="Can the patient drink water, or vomiting everything?",
                parser="yes_no",
                weight=2.5,
            ),
            TriageQuestion(
                key="duration",
                prompt_pidgin="How long e don dey like this?",
                prompt_english="How long has this been going on?",
                parser="duration",
                weight=1.0,
            ),
        ],
        decision_fn=lambda answers: (
            "refer" if answers.get("blood") is True
            else "refer" if answers.get("can_drink") is False
            else "drugs" if answers.get("severity", 0) > 0.6
            else "conservative"
        ),
    ),
}


# ---------------------------------------------------------------------------
# Condition detection for triage
# ---------------------------------------------------------------------------

_TRIAGE_KEYWORDS = {
    "cold": ["cold", "catarrh", "sneez", "runny nose", "stuffy nose",
             "sore throat", "mild cough", "no get temperature"],
    "headache": ["headache", "head dey pain", "head pain", "migraine"],
    "fatigue": ["tired", "weak", "no strength", "exhaust", "fatigue",
                "dey tire", "body dey weak", "no get strength"],
    "dehydration": ["diarrhoea", "diarrhea", "vomit", "run stomach",
                    "thirsty", "dehydrat", "no drink", "dry mouth"],
    "body_pain": ["body pain", "body ache", "muscle pain", "back pain",
                  "body dey pain", "muscle dey pain", "sore"],
    "stress": ["stress", "anxiety", "worried", "pressure", "burnout",
               "no sleep", "can't sleep", "insomnia", "too much work"],
    "heat": ["heat", "sun", "sunstroke", "hot weather", "heat stroke",
             "sun dey beat"],
    "stomach": ["stomach", "belly", "abdomen", "gastritis", "heartburn",
                "bloating", "belly dey pain", "stomach dey pain"],
}


def detect_triage_condition(query: str) -> Optional[str]:
    """Detect which triage pathway to use from the initial query."""
    q = query.lower()
    scores = {}
    for condition, keywords in _TRIAGE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > 0:
            scores[condition] = score

    if not scores:
        return None
    return max(scores, key=scores.get)


# ---------------------------------------------------------------------------
# Triage session state
# ---------------------------------------------------------------------------

@dataclass
class TriageSession:
    """Tracks the state of an ongoing triage session."""
    condition: str
    pathway: TriagePathway
    answers: dict = field(default_factory=dict)
    current_question: int = 0
    complete: bool = False
    treatment_path: str = ""  # "conservative", "drugs", or "refer"

    def get_next_question(self) -> Optional[TriageQuestion]:
        """Get the next question to ask."""
        if self.current_question >= len(self.pathway.questions):
            return None
        return self.pathway.questions[self.current_question]

    def record_answer(self, answer: str) -> Optional[str]:
        """Record an answer and return the next question prompt (or None if done).

        Returns the next question prompt in the appropriate language.
        """
        question = self.get_next_question()
        if question is None:
            return None

        # Parse the answer
        parser_fn = PARSERS.get(question.parser, _parse_text)
        parsed = parser_fn(answer)

        # Store the answer
        self.answers[question.key] = parsed
        self.current_question += 1

        # Check if we can decide early (skip remaining questions)
        if self._can_decide_early():
            self.complete = True
            self.treatment_path = self._make_decision()
            return None

        # Check if we've asked all questions
        if self.current_question >= len(self.pathway.questions):
            self.complete = True
            self.treatment_path = self._make_decision()
            return None

        # Return next question
        next_q = self.get_next_question()
        if next_q is None:
            self.complete = True
            self.treatment_path = self._make_decision()
            return None
        return next_q.prompt_pidgin  # TODO: use lang parameter

    def _can_decide_early(self) -> bool:
        """Check if we have enough info to decide without more questions."""
        # If any critical red flag is hit, decide immediately
        if self.answers.get("breathing") is True:  # difficulty breathing
            return True
        if self.answers.get("blood") is True:  # blood in stool/vomit
            return True
        if self.answers.get("hopeless") is True:  # suicidal ideation
            return True
        if self.answers.get("conscious") is False:  # unconscious/confused
            return True
        if self.answers.get("can_drink") is False:  # can't keep fluids down
            return True
        if self.answers.get("urine") is False:  # not passing urine
            return True
        if self.answers.get("fever_stiff_neck") is True:  # meningitis sign
            return True
        return False

    def _make_decision(self) -> str:
        """Apply the decision function to determine treatment path."""
        if self.pathway.decision_fn:
            try:
                result = self.pathway.decision_fn(self.answers)
                if result in ("conservative", "drugs", "refer"):
                    return result
            except Exception:
                pass
        return "conservative"  # Default to conservative if decision fails


# ---------------------------------------------------------------------------
# Triage entry point
# ---------------------------------------------------------------------------

def start_triage(query: str) -> Optional[TriageSession]:
    """Start a triage session for a query.

    Returns a TriageSession if the query matches a triage pathway,
    or None if the query should go through the normal pipeline.
    """
    condition = detect_triage_condition(query)
    if condition is None:
        return None

    pathway = TRIAGE_PATHWAYS.get(condition)
    if pathway is None:
        return None

    session = TriageSession(condition=condition, pathway=pathway)
    return session


def get_triage_summary(session: TriageSession) -> str:
    """Get a summary of the triage answers for clinical context."""
    parts = [f"TRIAGE: {session.condition}"]
    for q in session.pathway.questions:
        answer = session.answers.get(q.key)
        if answer is not None:
            parts.append(f"  {q.key}: {answer}")
    parts.append(f"  DECISION: {session.treatment_path}")
    return "\n".join(parts)
