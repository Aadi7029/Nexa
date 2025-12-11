import React, { useEffect, useState, useRef } from "react";
import "./index.css";

/* API base from Vite env */
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  return res.json();
}

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  return res.json();
}

/* --- Connect component (request link) --- */
function ConnectTelegram({ userId, onLinked }) {
  const [loading, setLoading] = useState(false);
  const [linkInfo, setLinkInfo] = useState(null);
  const [error, setError] = useState(null);

  async function requestLink() {
    setError(null);
    setLoading(true);
    setLinkInfo(null);
    try {
      const data = await apiPost("/platforms/telegram/request_link", { user_id: Number(userId) });
      setLinkInfo(data);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h3>Connect Telegram</h3>
      <p className="muted">Generate a short code and send it to the Nexa Telegram bot.</p>

      <div className="row">
        <input className="small-input" value={userId} readOnly />
        <button className="btn" onClick={requestLink} disabled={loading}>
          {loading ? "Generating…" : "Generate Code"}
        </button>
      </div>

      {error && <div className="error">Error: {error}</div>}

      {linkInfo && (
        <div className="link-box">
          <div><strong>Code:</strong> <code>{linkInfo.code}</code></div>
          <div style={{ marginTop: 6 }}>{linkInfo.instructions}</div>
          <div style={{ marginTop: 8 }}>
            <button className="btn-ghost" onClick={() => onLinked && onLinked()}>
              I sent the code — refresh status
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* --- Message composer --- */
function MessageComposer({ userId, onSent }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  async function send() {
    if (!text.trim()) return;
    setSending(true);
    setError(null);
    try {
      await apiPost("/platforms/telegram/send", { user_id: Number(userId), text: text.trim() });
      onSent && onSent({ id: `local-${Date.now()}`, text: text.trim(), direction: "outbound", created_at: new Date().toISOString() });
      setText("");
    } catch (err) {
      setError(String(err));
    } finally {
      setSending(false);
    }
  }

  return (
    <div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a message..." className="composer-text" />
      <div className="row" style={{ marginTop: 8 }}>
        <button className="btn" onClick={send} disabled={sending || !text.trim()}>{sending ? "Sending…" : "Send"}</button>
        {error && <div className="error small">{error}</div>}
      </div>
    </div>
  );
}

/* --- Message list --- */
function MessageList({ messages }) {
  return (
    <div className="message-list">
      {messages.length === 0 && <div className="muted">No messages yet.</div>}
      {messages.map((m) => (
        <div key={m.id} className={`message ${m.direction === "outbound" ? "out" : "in"}`}>
          <div className="meta">
            <span className="sender">{m.sender_name || (m.direction === "outbound" ? "You" : "Unknown")}</span>
            {m.created_at && <span className="time">{new Date(m.created_at).toLocaleString()}</span>}
          </div>
          <div className="text">{m.text}</div>
        </div>
      ))}
    </div>
  );
}

/* --- Unified inbox (polling) --- */
function UnifiedInbox({ userId }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  async function fetchMessages() {
    setError(null);
    try {
      const data = await apiGet(`/messages?user_id=${encodeURIComponent(Number(userId))}`);
      setMessages(Array.isArray(data) ? data : []);
    } catch (err) {
      setError("Could not load messages. Backend may not expose GET /messages?user_id=<id> yet.");
    }
  }

  useEffect(() => {
    setLoading(true);
    fetchMessages().finally(() => setLoading(false));
    pollRef.current = setInterval(fetchMessages, 3000);
    return () => clearInterval(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  function onSent(newMessage) {
    setMessages((prev) => [...prev, newMessage]);
  }

  return (
    <div className="card">
      <h3>Unified Inbox</h3>
      <p className="muted">Polling backend for messages every 3s.</p>
      <div style={{ minHeight: 160 }}>
        {loading ? <div className="muted">Loading messages…</div> : <MessageList messages={messages} />}
      </div>

      <div style={{ marginTop: 12 }}>
        <MessageComposer userId={userId} onSent={onSent} />
      </div>

      {error && <div className="error small" style={{ marginTop: 8 }}>{error}</div>}
    </div>
  );
}

/* --- Main app --- */
export default function App() {
  const [userId, setUserId] = useState(1);
  const [linked, setLinked] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  async function checkLinkStatus() {
    try {
      const res = await apiGet(`/platforms/telegram/status?user_id=${Number(userId)}`);
      setLinked(Boolean(res && res.linked));
      setStatusMsg(res && res.detail ? res.detail : null);
    } catch (err) {
      setStatusMsg(null);
    }
  }

  useEffect(() => { checkLinkStatus(); }, [userId]);

  async function onUnlink() {
    try {
      await apiPost("/platforms/telegram/unlink", { user_id: Number(userId) });
      setLinked(false);
      setStatusMsg("Unlinked");
    } catch (err) {
      setStatusMsg("Unlink failed: " + String(err));
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>Nexa — Unified Messaging</h1>
        <div className="userbox">
          <label>User ID:</label>
          <input className="small-input" value={userId} onChange={(e) => setUserId(e.target.value)} />
          <span className="status">{linked ? "Telegram: linked" : "Telegram: not linked"}</span>
          <button className="btn-ghost" onClick={checkLinkStatus}>Refresh</button>
        </div>
      </header>

      <main className="grid">
        <section>
          <ConnectTelegram userId={userId} onLinked={() => { setLinked(true); checkLinkStatus(); }} />
          <div style={{ marginTop: 12 }}>
            <button className="btn-danger" onClick={onUnlink}>Unlink Telegram</button>
            {statusMsg && <div className="muted small" style={{ marginTop: 8 }}>{statusMsg}</div>}
          </div>
        </section>

        <section>
          <UnifiedInbox userId={userId} />
        </section>
      </main>

      <footer className="foot muted">API Base: {API_BASE}</footer>
    </div>
  );
}
