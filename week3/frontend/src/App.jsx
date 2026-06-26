import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

// Vite proxy forwards /upload, /chat, /reset → http://localhost:8000
const API = ''

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── File upload ─────────────────────────────────────────────────────────────
  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const form = new FormData();
    form.append('file', file);

    try {
      const res = await fetch(`${API}/upload`, { method: 'POST', body: form });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || 'Upload failed');

      setUploadedFile(file.name);
      addMessage('system', `✅ ${data.message}`);
    } catch (err) {
      addMessage('system', `❌ Upload error: ${err.message}`);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  // ── Send message ─────────────────────────────────────────────────────────────
  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    addMessage('user', text);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || 'Chat error');

      addMessage('assistant', data.answer, {
        score: data.score,
        relevant: data.relevant,
      });
    } catch (err) {
      addMessage('assistant', `❌ ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  // ── Reset collection ──────────────────────────────────────────────────────────
  async function handleReset() {
    if (!window.confirm('Clear all uploaded data?')) return;
    try {
      const res = await fetch(`${API}/reset`, { method: 'DELETE' });
      const data = await res.json();
      setUploadedFile(null);
      setMessages([]);
      addMessage('system', `🗑️ ${data.message}`);
    } catch {
      addMessage('system', '❌ Reset failed.');
    }
  }

  function addMessage(role, text, meta = {}) {
    setMessages(prev => [...prev, { id: Date.now() + Math.random(), role, text, ...meta }]);
  }

  return (
    <div className="layout">
      {/* ── Sidebar ─────────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="logo">📄 RAG Chat</span>
        </div>

        <div className="upload-section">
          <p className="section-label">Upload a text file</p>

          <button
            className="upload-btn"
            onClick={() => fileRef.current.click()}
            disabled={uploading}
          >
            {uploading ? 'Uploading…' : '+ Upload .txt'}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".txt"
            style={{ display: 'none' }}
            onChange={handleUpload}
          />

          {uploadedFile && (
            <div className="file-badge">
              <span>📎 {uploadedFile}</span>
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          <button className="reset-btn" onClick={handleReset}>
            🗑️ Clear Data
          </button>
        </div>
      </aside>

      {/* ── Main chat ──────────────────────────────────────────────────────── */}
      <main className="chat-area">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>Upload a <strong>.txt</strong> file, then ask questions about it.</p>
            </div>
          )}

          {messages.map(msg => (
            <div key={msg.id} className={`bubble-wrap ${msg.role}`}>
              <div className={`bubble ${msg.role}`}>
                {msg.role === 'assistant'
                  ? <ReactMarkdown>{msg.text}</ReactMarkdown>
                  : <p>{msg.text}</p>
                }
                {msg.score !== undefined && (
                  <span className={`score-badge ${msg.relevant ? 'relevant' : 'irrelevant'}`}>
                    {msg.relevant ? `${(msg.score * 100).toFixed(0)}% match` : 'No match'}
                  </span>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="bubble-wrap assistant">
              <div className="bubble assistant typing">
                <span /><span /><span />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* ── Input bar ───────────────────────────────────────────────────── */}
        <form className="input-bar" onSubmit={handleSend}>
          <input
            type="text"
            placeholder="Ask something about your document…"
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </main>
    </div>
  );
}
