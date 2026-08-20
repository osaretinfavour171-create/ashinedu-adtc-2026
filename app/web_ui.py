"""Simple web UI for PidginPharma.

A lightweight Flask web interface that makes PidginPharma accessible
to community health workers who don't use the terminal.

Features:
  - Chat-style interface (like WhatsApp)
  - Pidgin/English toggle
  - Voice input button (uses browser Speech API)
  - Voice output button (uses browser TTS)
  - Quick symptom buttons for common queries
  - Works on phones, tablets, laptops
  - Served on localhost only (127.0.0.1:5000)

Usage:
    python app/web_ui.py [--port 5000] [--host 127.0.0.1]
"""

import argparse
import json
import os
import sys
import time
import uuid

# Add app/ to path
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

try:
    from flask import Flask, render_template_string, request, jsonify
except ImportError:
    print("Flask not installed. Run: pip install flask")
    print("Then run: python app/web_ui.py")
    sys.exit(1)

from orchestrator import Orchestrator
from inference import infer_context, get_question_prompt

app = Flask(__name__)

# Global orchestrator instance
orch = None

# HTML template — single-page chat UI
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PidginPharma - Clinical Decision Support</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f0f2f5; height: 100vh; display: flex; flex-direction: column; }

  .header { background: #1a73e8; color: white; padding: 12px 16px;
            display: flex; align-items: center; gap: 12px; }
  .header h1 { font-size: 18px; font-weight: 600; }
  .header .subtitle { font-size: 12px; opacity: 0.8; }

  .quick-actions { background: white; padding: 8px 16px; display: flex; gap: 8px;
                   overflow-x: auto; border-bottom: 1px solid #e0e0e0; }
  .quick-btn { background: #e8f0fe; border: 1px solid #1a73e8; border-radius: 20px;
               padding: 6px 14px; font-size: 13px; cursor: pointer; white-space: nowrap;
               color: #1a73e8; }
  .quick-btn:hover { background: #1a73e8; color: white; }

  .chat { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; }

  .msg { max-width: 80%; padding: 10px 14px; border-radius: 12px;
         font-size: 14px; line-height: 1.5; word-wrap: break-word; }
  .msg.user { align-self: flex-end; background: #1a73e8; color: white;
              border-bottom-right-radius: 4px; }
  .msg.bot { align-self: flex-start; background: white; color: #333;
             border-bottom-left-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
  .msg.system { align-self: center; background: transparent; color: #666;
                font-size: 12px; font-style: italic; }
  .msg .source { font-size: 11px; color: #888; margin-top: 4px; }
  .msg.user .source { color: rgba(255,255,255,0.7); }

  .intake { background: #fff3cd; border: 1px solid #ffc107; border-radius: 12px;
            padding: 12px 16px; align-self: flex-start; max-width: 80%; }
  .intake .q { margin: 8px 0; }
  .intake input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 8px;
                  font-size: 14px; margin-top: 4px; }
  .intake button { background: #1a73e8; color: white; border: none; border-radius: 8px;
                   padding: 8px 16px; cursor: pointer; margin-top: 8px; font-size: 14px; }

  .input-area { background: white; padding: 12px 16px; display: flex; gap: 8px;
                border-top: 1px solid #e0e0e0; }
  .input-area input { flex: 1; padding: 10px 14px; border: 1px solid #ddd;
                      border-radius: 24px; font-size: 14px; outline: none; }
  .input-area input:focus { border-color: #1a73e8; }
  .input-area button { background: #1a73e8; color: white; border: none; border-radius: 50%;
                       width: 42px; height: 42px; cursor: pointer; font-size: 18px; }
  .input-area .voice-btn { background: #34a853; }

  .loading { display: flex; gap: 4px; padding: 10px 14px; background: white;
             border-radius: 12px; align-self: flex-start; }
  .loading span { width: 8px; height: 8px; background: #999; border-radius: 50%;
                 animation: bounce 1.4s infinite both; }
  .loading span:nth-child(2) { animation-delay: 0.2s; }
  .loading span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce { 0%,80%,100% { transform: scale(0); } 40% { transform: scale(1); } }
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>&#x1F3E5; PidginPharma</h1>
    <div class="subtitle">Offline Clinical Decision Support for Nigerian CHEWs</div>
  </div>
</div>

<div class="quick-actions">
  <button class="quick-btn" onclick="send('my pikin get hot body and dey vomit')">&#x1F321; Fever child</button>
  <button class="quick-btn" onclick="send('treatment for acute diarrhoea')">&#x1F9A0; Diarrhoea</button>
  <button class="quick-btn" onclick="send('metronidazole plus warfarin')">&#x1F48A; Drug interaction</button>
  <button class="quick-btn" onclick="send('paracetamol dose for 10kg child')">&#x1F4CF; Drug dose</button>
  <button class="quick-btn" onclick="send('treatment for malaria')">&#x1F423; Malaria</button>
  <button class="quick-btn" onclick="send('ORS preparation')">&#x1F4A7; ORS</button>
</div>

<div class="chat" id="chat">
  <div class="msg system">Welcome to PidginPharma. Type your question in English or Pidgin.</div>
</div>

<div class="input-area">
  <input type="text" id="input" placeholder="Type your question..." onkeypress="if(event.key==='Enter')sendMsg()">
  <button class="voice-btn" onclick="startVoice()" title="Voice input">&#x1F3A4;</button>
  <button onclick="sendMsg()">&#x27A4;</button>
</div>

<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');

function addMsg(text, cls, source) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = text;
  if (source) {
    const src = document.createElement('div');
    src.className = 'source';
    src.textContent = source;
    div.appendChild(src);
  }
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function addLoading() {
  const div = document.createElement('div');
  div.className = 'loading';
  div.id = 'loading';
  div.innerHTML = '<span></span><span></span><span></span>';
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function removeLoading() {
  const el = document.getElementById('loading');
  if (el) el.remove();
}

function send(text) {
  input.value = text;
  sendMsg();
}

function sendMsg() {
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  addMsg(text, 'user');
  addLoading();

  fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: text})
  })
  .then(r => r.json())
  .then(data => {
    removeLoading();
    if (data.intake) {
      showIntake(data.questions, data.session_id);
    } else {
      addMsg(data.answer, 'bot', data.source);
    }
  })
  .catch(err => {
    removeLoading();
    addMsg('Something dey wrong. Try again.', 'system');
  });
}

function showIntake(questions, sessionId) {
  const div = document.createElement('div');
  div.className = 'intake';
  div.innerHTML = '<strong>&#x1F3E5; Make I ask you some questions:</strong>';
  const form = document.createElement('div');
  questions.forEach((q, i) => {
    const qDiv = document.createElement('div');
    qDiv.className = 'q';
    qDiv.innerHTML = `<label>${i+1}. ${q.prompt}</label>
      <input type="text" data-field="${q.field}" placeholder="Your answer (or skip)">`;
    form.appendChild(qDiv);
  });
  const btn = document.createElement('button');
  btn.textContent = 'Submit';
  btn.onclick = () => submitIntake(form, sessionId);
  form.appendChild(btn);
  div.appendChild(form);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function submitIntake(form, sessionId) {
  const answers = {};
  form.querySelectorAll('input[data-field]').forEach(inp => {
    answers[inp.dataset.field] = inp.value || 'skip';
  });
  addLoading();

  fetch('/api/intake', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({answers: answers, session_id: sessionId})
  })
  .then(r => r.json())
  .then(data => {
    removeLoading();
    addMsg(data.answer, 'bot', data.source);
  });
}

// Voice input using Web Speech API
function startVoice() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    addMsg('Voice input not supported in this browser. Try Chrome.', 'system');
    return;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-NG';  // Nigerian English
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  input.placeholder = 'Listening...';
  recognition.onresult = (event) => {
    const text = event.results[0][0].transcript;
    input.value = text;
    input.placeholder = 'Type your question...';
    sendMsg();
  };
  recognition.onerror = () => {
    input.placeholder = 'Type your question...';
  };
  recognition.start();
}

// Voice output using Web Speech API
function speak(text) {
  if (!('speechSynthesis' in window)) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = 'en-NG';
  utter.rate = 0.9;
  speechSynthesis.speak(utter);
}
</script>
</body>
</html>'''


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"answer": "Tell me wetin dey worry di patient.", "source": "system"})

    # Run inference
    normalized = orch.normalizer.normalize(message)
    inference = infer_context(normalized)

    if inference.should_ask and orch.intake_enabled:
        # Need to ask questions
        session_id = str(uuid.uuid4())[:8]
        questions = []
        for field in inference.questions_to_ask[:5]:
            questions.append({
                "field": field,
                "prompt": get_question_prompt(field, orch.lang),
            })
        # Store session
        if not hasattr(app, '_sessions'):
            app._sessions = {}
        app._sessions[session_id] = {
            "query": message,
            "normalized": normalized,
            "inference": inference,
            "answers": {},
        }
        return jsonify({
            "intake": True,
            "questions": questions,
            "session_id": session_id,
        })
    else:
        # Can answer directly
        patient_ctx = None
        if inference.already_known:
            from inference import build_patient_context_from_query
            patient_ctx = build_patient_context_from_query(message)

        start = time.time()
        answer, source = orch.answer(message, patient_ctx=patient_ctx)
        elapsed = time.time() - start

        source_labels = {
            "cache": "\u26a1 instant",
            "docreader": "\U0001f4da from guidelines",
            "llm": "\U0001f9e0 from clinical brain",
            "fallback": "\u26a0\ufe0f basic info",
        }
        return jsonify({
            "answer": answer,
            "source": source_labels.get(source, source),
        })


@app.route("/api/intake", methods=["POST"])
def intake_submit():
    data = request.get_json()
    answers = data.get("answers", {})
    session_id = data.get("session_id", "")

    # Get session
    session = app._sessions.get(session_id, {})
    original_query = session.get("query", "")
    inference = session.get("inference")

    # Build patient context from answers
    from intake import PatientContext
    from inference import _set_ctx_field as _set_field
    ctx = PatientContext()

    # Actually we need the helper from orchestrator
    from intake import _parse_age, _parse_weight, _parse_gender, _parse_temperature
    for field, answer in answers.items():
        if answer.lower() in ("skip", "i no know", "idk", ""):
            continue
        if field == "age":
            display, years = _parse_age(answer)
            if display:
                ctx.age = display
                ctx.age_years = years
        elif field == "weight":
            kg, _ = _parse_weight(answer)
            if kg:
                ctx.weight_kg = kg
        elif field == "gender":
            g = _parse_gender(answer)
            if g:
                ctx.gender = g
        elif field == "symptoms":
            ctx.symptoms = answer
        elif field == "duration":
            ctx.duration = answer
        elif field == "temperature":
            t = _parse_temperature(answer)
            if t:
                ctx.temperature = t
        elif field == "allergies":
            ctx.allergies = answer
        elif field == "current_meds":
            ctx.current_meds = answer
        elif field == "history":
            ctx.history = answer

    # Answer with context
    query = ctx.symptoms if ctx.symptoms else original_query
    start = time.time()
    answer, source = orch.answer(query, patient_ctx=ctx)
    elapsed = time.time() - start

    # Clean up session
    app._sessions.pop(session_id, None)

    source_labels = {
        "cache": "\u26a1 instant",
        "docreader": "\U0001f4da from guidelines",
        "llm": "\U0001f9e0 from clinical brain",
        "fallback": "\u26a0\ufe0f basic info",
    }
    return jsonify({
        "answer": answer,
        "source": source_labels.get(source, source),
    })


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "service": "PidginPharma Web UI"})


def main():
    parser = argparse.ArgumentParser(description="PidginPharma Web UI")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-model", action="store_true")
    parser.add_argument("--no-docreader", action="store_true")
    args = parser.parse_args()

    global orch
    orch = Orchestrator(
        use_model=not args.no_model,
        use_docreader=not args.no_docreader,
    )

    print(f"\n  PidginPharma Web UI starting on http://{args.host}:{args.port}")
    print(f"  Open in your browser to use the clinical assistant.\n")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
