import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, AlertTriangle, Bot, User, Paperclip, X, FileText, CheckCircle, Loader } from 'lucide-react';
import { sendChat, uploadDocument } from '../api';
import CitationCard from '../components/CitationCard';
import type { ChatResponse } from '../api';

type UploadStatus = 'pending' | 'uploading' | 'done' | 'error';
interface AttachedFile {
  file: File;
  status: UploadStatus;
  error?: string;
}

interface Message {
  role: 'user' | 'ai';
  text: string;
  response?: ChatResponse;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'ai',
      text: 'Guten Tag! Ich bin Ihr Nova KI-Assistent für Fragen zur Energiewende und Wärmeplanung. Stellen Sie mir eine Frage zu Ihren Dokumenten.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [attachments, setAttachments] = useState<AttachedFile[]>([]);
  const [uploadNotice, setUploadNotice] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleAttach = (files: FileList | null) => {
    if (!files) return;
    const newFiles: AttachedFile[] = Array.from(files).map(f => ({ file: f, status: 'pending' }));
    setAttachments(prev => [...prev, ...newFiles]);
  };

  const removeAttachment = (idx: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSend = async () => {
    const q = input.trim();
    if ((!q && attachments.length === 0) || loading) return;
    setInput('');

    // Upload any pending attachments first
    const pendingFiles = attachments.filter(a => a.status === 'pending');
    if (pendingFiles.length > 0) {
      // Show uploading state
      setAttachments(prev =>
        prev.map(a => a.status === 'pending' ? { ...a, status: 'uploading' } : a)
      );
      const uploadResults = await Promise.all(
        pendingFiles.map(async (a, relIdx) => {
          try {
            await uploadDocument(a.file, 'additional_documents');
            return { relIdx, success: true };
          } catch {
            return { relIdx, success: false };
          }
        })
      );
      // Mark done/error
      setAttachments(prev => {
        let pendingIdx = 0; // Move it INSIDE the updater function so it resets on every run
        return prev.map(a => {
          if (a.status === 'uploading') {
            const r = uploadResults[pendingIdx++];
            // Added optional chaining (r?.success) as an extra safety measure
            return { ...a, status: r?.success ? 'done' : 'error' }; 
          }
          return a;
        });
      });
      const doneCount = uploadResults.filter(r => r.success).length;
      if (doneCount > 0) {
        setUploadNotice(`${doneCount} Dokument(e) hochgeladen und indiziert.`);
        setTimeout(() => setUploadNotice(''), 4000);
      }
    }

    if (!q) return; // only uploaded, no question

    // Mention attached file names in the user bubble
    const fileNames = attachments.map(a => a.file.name).join(', ');
    const displayText = fileNames
      ? `${q}\n\n📎 Anhang: ${fileNames}`
      : q;

    setMessages(prev => [...prev, { role: 'user', text: displayText }]);
    setAttachments([]);
    setLoading(true);
    try {
      const res = await sendChat(q);
      setMessages(prev => [...prev, { role: 'ai', text: res.answer, response: res }]);
    } catch (e) {
      setMessages(prev => [
        ...prev,
        {
          role: 'ai',
          text: 'Fehler bei der Verbindung zum Server. Bitte stellen Sie sicher, dass das Backend läuft.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-layout">
      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`msg ${msg.role === 'user' ? 'msg-user' : `msg-ai${msg.response?.is_uncertain ? ' msg-uncertain' : ''}`}`}>
            <div className={`msg-avatar ${msg.role === 'user' ? 'msg-avatar-user' : 'msg-avatar-ai'}`}>
              {msg.role === 'user' ? <User size={15} /> : <Bot size={15} />}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', maxWidth: '72%' }}>
              <div className="msg-bubble">
                <ReactMarkdown>{msg.text}</ReactMarkdown>
              </div>

              {/* Uncertain banner */}
              {msg.response?.is_uncertain && msg.response.clarification_request && (
                <div className="uncertain-banner">
                  <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>{msg.response.clarification_request}</span>
                </div>
              )}

              {/* Citations */}
              {msg.response?.citations && msg.response.citations.length > 0 && (
                <CitationCard citations={msg.response.citations} />
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="msg msg-ai">
            <div className="msg-avatar msg-avatar-ai">
              <Bot size={15} />
            </div>
            <div className="msg-bubble" style={{ background: '#fff', border: '1px solid #e5e7eb' }}>
              <div className="typing-indicator">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Upload notice */}
      {uploadNotice && (
        <div style={{ background: '#dcfce7', color: '#166534', borderTop: '1px solid #bbf7d0', padding: '6px 16px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <CheckCircle size={13} />
          {uploadNotice}
        </div>
      )}

      {/* Attachment chips */}
      {attachments.length > 0 && (
        <div style={{ borderTop: '1px solid #e5e7eb', padding: '6px 16px 0', display: 'flex', flexWrap: 'wrap', gap: 6, background: '#fff' }}>
          {attachments.map((a, idx) => (
            <div key={idx} style={{
              display: 'flex', alignItems: 'center', gap: 5,
              background: a.status === 'error' ? '#fee2e2' : a.status === 'done' ? '#dcfce7' : '#eff6ff',
              border: `1px solid ${a.status === 'error' ? '#fca5a5' : a.status === 'done' ? '#86efac' : '#bfdbfe'}`,
              borderRadius: 20, padding: '3px 10px 3px 8px', fontSize: 12,
              color: a.status === 'error' ? '#dc2626' : a.status === 'done' ? '#166534' : '#1d4ed8',
            }}>
              {a.status === 'uploading'
                ? <Loader size={11} style={{ animation: 'spin .7s linear infinite' }} />
                : a.status === 'done'
                ? <CheckCircle size={11} />
                : <FileText size={11} />}
              <span style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.file.name}</span>
              {a.status !== 'uploading' && (
                <button onClick={() => removeAttachment(idx)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center', color: 'inherit', opacity: .7 }}>
                  <X size={11} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="chat-input-row">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.xlsx,.xls"
          multiple
          style={{ display: 'none' }}
          onChange={e => { handleAttach(e.target.files); e.target.value = ''; }}
        />
        {/* Paperclip button */}
        <button
          className="btn btn-secondary"
          style={{ padding: '7px 10px', flexShrink: 0 }}
          title="Zusatzdokument anhängen (PDF, DOCX, XLSX)"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
        >
          <Paperclip size={16} />
        </button>
        <textarea
          rows={1}
          placeholder="Frage eingeben… (Enter zum Senden, Shift+Enter für Zeilenumbruch)"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={loading || (!input.trim() && attachments.length === 0)}
        >
          <Send size={15} />
          Senden
        </button>
      </div>
    </div>
  );
}
