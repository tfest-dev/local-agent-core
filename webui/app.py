# webui/app.py

import logging
import os
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string
from requests.exceptions import RequestException

from agent import Agent
from memory import OpenMemoryStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Default alias for routing
DEFAULT_ALIAS = "general"

# Shared agent instance for all web requests. The memory store is configured
# from the environment; it will only be used for aliases that opt-in via
# router.yaml.
_web_memory_store = OpenMemoryStore.from_env()
web_agent = Agent(
    default_alias=DEFAULT_ALIAS,
    debug=True,  # Enable debug logs (including memory) while iterating.
    memory_store=_web_memory_store,
    user_id=None,  # Hook here for per-user memory spaces later.
)

# Simple, self-contained HTML template
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Local Agent Core</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      padding: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f172a;
      color: #e5e7eb;
      display: flex;
      justify-content: center;
      align-items: stretch;
      min-height: 100vh;
    }
    .app-container {
      width: 100%;
      max-width: 1100px;
      margin: 16px;
      background: #020617;
      border-radius: 16px;
      border: 1px solid #1e293b;
      display: flex;
      flex-direction: row;
      overflow: hidden;
      box-shadow: 0 18px 45px rgba(0,0,0,0.5);
    }
    .left-pane, .right-pane {
      padding: 16px;
    }
    .left-pane {
      flex: 3;
      border-right: 1px solid #1e293b;
      display: flex;
      flex-direction: column;
    }
    .right-pane {
      flex: 2;
      background: #020617;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .brand-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .brand-title {
      font-size: 1.1rem;
      font-weight: 600;
    }
    .brand-tagline {
      font-size: 0.8rem;
      color: #9ca3af;
    }
    .brand-badge {
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid #4b5563;
      font-size: 0.7rem;
      color: #9ca3af;
    }
    .chat-box {
      flex: 1;
      border-radius: 12px;
      border: 1px solid #1e293b;
      background: radial-gradient(circle at top left, #0b1120, #020617);
      padding: 12px;
      overflow-y: auto;
      font-size: 0.9rem;
    }
    .chat-message {
      margin-bottom: 8px;
      line-height: 1.4;
    }
    .chat-message strong {
      font-size: 0.85rem;
    }
    .chat-message.user {
      color: #38bdf8;
    }
    .chat-message.agent {
      color: #a5b4fc;
    }
    .chat-message.system {
      color: #9ca3af;
      font-style: italic;
    }
    .input-row {
      display: flex;
      gap: 8px;
      margin-top: 10px;
    }
    .input-row input[type="text"] {
      flex: 1;
      padding: 9px 10px;
      border-radius: 999px;
      border: 1px solid #1f2937;
      background: #020617;
      color: #e5e7eb;
      font-size: 0.9rem;
      outline: none;
    }
    .input-row input[type="text"]:focus {
      border-color: #38bdf8;
    }
    .input-row button {
      padding: 9px 14px;
      border-radius: 999px;
      border: none;
      background: linear-gradient(135deg, #22c55e, #16a34a);
      color: white;
      font-size: 0.9rem;
      font-weight: 500;
      cursor: pointer;
    }
    .input-row button:disabled {
      opacity: 0.6;
      cursor: default;
    }
    .settings-section-title {
      font-size: 0.85rem;
      font-weight: 600;
      text-transform: uppercase;
      margin-bottom: 8px;
      letter-spacing: 0.06em;
      color: #9ca3af;
    }
    .settings-card {
      border-radius: 12px;
      border: 1px solid #1e293b;
      padding: 12px;
      background: #020617;
    }
    .settings-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      font-size: 0.85rem;
    }
    .settings-row:last-child {
      margin-bottom: 0;
    }
    .pill {
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid #374151;
      font-size: 0.7rem;
      color: #9ca3af;
    }
    select {
      background: #020617;
      color: #e5e7eb;
      border-radius: 999px;
      border: 1px solid #374151;
      padding: 4px 8px;
      font-size: 0.8rem;
      outline: none;
    }
    .hint {
      font-size: 0.75rem;
      color: #6b7280;
      margin-top: 4px;
    }
    @media (max-width: 800px) {
      .app-container {
        flex-direction: column;
      }
      .left-pane {
        border-right: none;
        border-bottom: 1px solid #1e293b;
      }
    }
  </style>
</head>
<body>
  <div class="app-container">
    <div class="left-pane">
      <div class="brand-header">
        <div>
          <div class="brand-title">Local Agent Core</div>
          <div class="brand-tagline">Your branding can sit here.</div>
        </div>
        <div class="brand-badge">Self-hosted • Private</div>
      </div>
      <div id="chat" class="chat-box">
        <div class="chat-message system">
          <strong>System</strong>: This is a local, self-hosted AI agent. Type a message below to start a conversation.
        </div>
      </div>
      <div class="input-row">
        <input id="userInput" type="text" placeholder="Ask something..." autocomplete="off" />
        <button id="sendBtn" onclick="sendMessage()">Send</button>
      </div>
      <div class="hint">Clients can customise colours, logo, and layout to match their brand.</div>
    </div>

    <div class="right-pane">
      <div>
        <div class="settings-section-title">Agent Settings</div>
        <div class="settings-card">
          <div class="settings-row">
            <span>Route alias</span>
            <select id="aliasSelect">
              <option value="general">general</option>
              <option value="gpt-oss">gpt-oss</option>
              <option value="code-python">code-python</option>
            </select>
          </div>
          <div class="settings-row">
            <span>Speech output</span>
            <span class="pill">Hook available</span>
          </div>
          <div class="hint">
            The backend already supports a TTS hook. This panel can be expanded with per-client options (voices, modes, etc.).
          </div>
        </div>
      </div>

      <div>
        <div class="settings-section-title">Status</div>
        <div class="settings-card" id="statusCard">
          <div id="statusText" class="hint">
            Ready. Messages will be sent via your configured local route.
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
  async function sendMessage() {
    const inputField = document.getElementById("userInput");
    const sendBtn = document.getElementById("sendBtn");
    const chatBox = document.getElementById("chat");
    const aliasSelect = document.getElementById("aliasSelect");
    const statusText = document.getElementById("statusText");

    const text = inputField.value.trim();
    if (!text) return;

    // Show user message
    const userMsg = document.createElement("div");
    userMsg.className = "chat-message user";
    userMsg.innerHTML = "<strong>You:</strong> " + text;
    chatBox.appendChild(userMsg);
    chatBox.scrollTop = chatBox.scrollHeight;

    inputField.value = "";
    inputField.focus();
    sendBtn.disabled = true;
    statusText.textContent = "Sending request to local agent…";

    try {
      const resp = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input: text,
          alias: aliasSelect.value
        }),
      });

      const data = await resp.json();

      if (!data.ok) {
        const errMsg = document.createElement("div");
        errMsg.className = "chat-message system";
        errMsg.innerHTML = "<strong>System:</strong> " + (data.error || "Request failed.");
        chatBox.appendChild(errMsg);
        statusText.textContent = "Error from model endpoint.";
      } else {
        const agentMsg = document.createElement("div");
        agentMsg.className = "chat-message agent";
        agentMsg.innerHTML = "<strong>Agent:</strong> " + data.response;
        chatBox.appendChild(agentMsg);
        statusText.textContent = "Response received from local agent.";
      }

      chatBox.scrollTop = chatBox.scrollHeight;
    } catch (err) {
      const errMsg = document.createElement("div");
      errMsg.className = "chat-message system";
      errMsg.innerHTML = "<strong>System:</strong> Failed to reach /chat endpoint.";
      chatBox.appendChild(errMsg);
      statusText.textContent = "Failed to contact backend.";
    } finally {
      sendBtn.disabled = false;
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const inputField = document.getElementById("userInput");
    inputField.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
      }
    });
  });
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_input = (data.get("input") or "").strip()
    alias = (data.get("alias") or DEFAULT_ALIAS).strip() or DEFAULT_ALIAS

    if not user_input:
        return jsonify({"ok": False, "error": "Empty input."}), 400

    try:
        response_text = web_agent.respond(user_input, alias=alias)
    except ValueError:
        # Should already be caught by the empty-input check, but keep this
        # defensive branch to avoid leaking internal errors.
        return jsonify({"ok": False, "error": "Empty input."}), 400
    except Exception as e:
        # Preserve existing behaviour: distinguish between routing errors and
        # connectivity issues where possible.
        if isinstance(e, RequestException):
            logger.exception("LLM request failed")
            return jsonify({"ok": False, "error": "Model endpoint not reachable."}), 502

        logger.exception("Routing or agent error")
        return jsonify({"ok": False, "error": f"Unknown alias '{alias}'"}), 400

    response_text = (response_text or "").strip()
    if not response_text:
        response_text = "[No response from model]"

    return jsonify({"ok": True, "response": response_text})


def main():
    """Start the Flask web UI.

    Host and port can be configured via environment variables:
    - LAC_WEB_HOST (default: ******* )
    - LAC_WEB_PORT (default: 5001)
    """
    host = os.getenv("LAC_WEB_HOST", "*******")
    port = int(os.getenv("LAC_WEB_PORT", "5001"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
