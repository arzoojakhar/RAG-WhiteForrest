import { useState, useEffect, useRef } from 'react';
import {
  Upload, Trash2, RefreshCw, FileText, Database, BookOpen,
} from 'lucide-react';
import {
  fetchDocuments, uploadDocument, deleteDocument, reindexDocuments,
} from '../api';
import type { DocumentInfo } from '../api';

export default function Dashboard() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [tab, setTab] = useState<'knowledge_base' | 'additional_documents'>('knowledge_base');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [msg, setMsg] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchDocuments();
      setDocs(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = docs.filter(d => d.doc_type === tab);
  const kbCount    = docs.filter(d => d.doc_type === 'knowledge_base').length;
  const extraCount = docs.filter(d => d.doc_type === 'additional_documents').length;
  const totalChunks = docs.reduce((s, d) => s + d.chunks, 0);

  const notify = (m: string) => {
    setMsg(m);
    setTimeout(() => setMsg(''), 4000);
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file, tab);
      }
      notify(`${files.length} Datei(en) hochgeladen und indiziert.`);
      await load();
    } catch {
      notify('Fehler beim Hochladen.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (doc: DocumentInfo) => {
    if (!confirm(`„${doc.filename}" wirklich löschen?`)) return;
    try {
      await deleteDocument(doc.doc_type, doc.filename);
      notify('Dokument entfernt.');
      await load();
    } catch {
      notify('Fehler beim Löschen.');
    }
  };

  const handleReindex = async () => {
    setLoading(true);
    try {
      await reindexDocuments();
      notify('Neuindizierung abgeschlossen.');
      await load();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-content">
      {/* Stats */}
      <div className="stat-row">
        <div className="stat-card">
          <div className="value">{kbCount}</div>
          <div className="label">Wissensbasis-Dokumente</div>
        </div>
        <div className="stat-card">
          <div className="value">{extraCount}</div>
          <div className="label">Zusatzdokumente</div>
        </div>
        <div className="stat-card">
          <div className="value">{totalChunks}</div>
          <div className="label">Indizierte Textabschnitte</div>
        </div>
      </div>

      {/* Notification */}
      {msg && (
        <div style={{ background: '#dcfce7', color: '#166534', border: '1px solid #86efac', borderRadius: 6, padding: '8px 14px', fontSize: 13, marginBottom: 16 }}>
          {msg}
        </div>
      )}

      {/* Tabs + Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 0 }}>
        <div className="tab-bar" style={{ marginBottom: 0 }}>
          <div
            className={`tab ${tab === 'knowledge_base' ? 'active' : ''}`}
            onClick={() => setTab('knowledge_base')}
          >
            <BookOpen size={13} style={{ display: 'inline', marginRight: 5 }} />
            Wissensbasis ({kbCount})
          </div>
          <div
            className={`tab ${tab === 'additional_documents' ? 'active' : ''}`}
            onClick={() => setTab('additional_documents')}
          >
            <Database size={13} style={{ display: 'inline', marginRight: 5 }} />
            Zusatzdokumente ({extraCount})
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, paddingBottom: 2 }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleReindex}
            disabled={loading}
          >
            <RefreshCw size={13} />
            Neu indizieren
          </button>
        </div>
      </div>

      {/* Document table */}
      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-header">
          <h3>
            {tab === 'knowledge_base' ? 'Wissensbasis-Dokumente' : 'Zusatzdokumente'}
          </h3>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            <Upload size={13} />
            {uploading ? 'Lädt hoch…' : 'Hochladen'}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.doc,.xlsx,.xls"
            multiple
            style={{ display: 'none' }}
            onChange={e => handleUpload(e.target.files)}
          />
        </div>

        {/* Drop zone */}
        <div
          className={`drop-zone ${dragging ? 'drag' : ''}`}
          style={{ margin: '12px 16px', padding: '20px' }}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => { e.preventDefault(); setDragging(false); handleUpload(e.dataTransfer.files); }}
          onClick={() => fileRef.current?.click()}
        >
          <Upload size={20} style={{ color: 'var(--neutral-400)', margin: '0 auto', display: 'block' }} />
          <p>Dateien hier ablegen oder klicken zum Auswählen</p>
          <p style={{ fontSize: 11, marginTop: 4, color: 'var(--neutral-400)' }}>
            Unterstützt: PDF, DOCX, XLSX
          </p>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state"><div className="spinner" style={{ margin: '0 auto' }} /></div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <FileText size={32} />
              <p style={{ marginTop: 8 }}>Noch keine Dokumente vorhanden.</p>
              <p style={{ fontSize: 12, marginTop: 4 }}>Laden Sie Dateien hoch, um sie zu indizieren.</p>
            </div>
          ) : (
            <table className="doc-table">
              <thead>
                <tr>
                  <th>Dateiname</th>
                  <th>Textabschnitte</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(doc => (
                  <tr key={doc.filename}>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <FileText size={14} style={{ color: 'var(--primary)', flexShrink: 0 }} />
                        {doc.filename}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-blue">{doc.chunks}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(doc)}
                      >
                        <Trash2 size={12} />
                        Löschen
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
