import { useState, useRef } from 'react';
import { Upload, Download, CheckCircle, AlertCircle, HelpCircle, FileSpreadsheet } from 'lucide-react';
import { analyzeTemplate, updateTemplateFields, exportTemplate } from '../api';
import type { TemplateAnalysis, TemplateField } from '../api';

const STATUS_ICON: Record<string, JSX.Element> = {
  filled:           <CheckCircle size={14} color="#057a55" />,
  uncertain:        <AlertCircle  size={14} color="#c27803" />,
  needs_user_input: <HelpCircle   size={14} color="#c81e1e" />,
};
const STATUS_LABEL: Record<string, string> = {
  filled:           'Ausgefüllt',
  uncertain:        'Unsicher',
  needs_user_input: 'Eingabe nötig',
};
const STATUS_BADGE: Record<string, string> = {
  filled:           'badge-green',
  uncertain:        'badge-yellow',
  needs_user_input: 'badge-red',
};

export default function Templates() {
  const [analysis, setAnalysis] = useState<TemplateAnalysis | null>(null);
  const [userEdits, setUserEdits] = useState<Record<string, string>>({});
  const [loading, setLoading]   = useState(false);
  const [saving,  setSaving]    = useState(false);
  const [exporting, setExporting] = useState(false);
  const [msg, setMsg]           = useState('');
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const notify = (m: string) => { setMsg(m); setTimeout(() => setMsg(''), 5000); };

  const handleFile = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setLoading(true);
    setAnalysis(null);
    setUserEdits({});
    try {
      const result = await analyzeTemplate(files[0]);
      setAnalysis(result);
      notify('Template analysiert. Bitte überprüfen und fehlende Felder ausfüllen.');
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      notify(msg || 'Fehler beim Analysieren des Templates.');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (fieldId: string, value: string) => {
    setUserEdits(prev => ({ ...prev, [fieldId]: value }));
  };

  const handleSaveEdits = async () => {
    if (!analysis) return;
    setSaving(true);
    try {
      const result = await updateTemplateFields(analysis.session_id, userEdits);
      setAnalysis(prev => prev ? { ...prev, fields: result.fields } : null);
      setUserEdits({});
      notify('Eingaben gespeichert.');
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async () => {
    if (!analysis) return;
    // First save any pending edits
    if (Object.keys(userEdits).length > 0) await handleSaveEdits();
    setExporting(true);
    try {
      const blob = await exportTemplate(analysis.session_id);
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `ausgefüllt_${analysis.filename}`;
      a.click();
      URL.revokeObjectURL(url);
      notify('Template exportiert.');
    } catch {
      notify('Fehler beim Exportieren.');
    } finally {
      setExporting(false);
    }
  };

  const fields      = analysis?.fields ?? [];
  const filledCount    = fields.filter(f => f.status === 'filled').length;
  const uncertainCount = fields.filter(f => f.status === 'uncertain').length;
  const missingCount   = fields.filter(f => f.status === 'needs_user_input').length;

  return (
    <div className="page-content">
      {/* Upload */}
      {!analysis && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header"><h3>Template hochladen</h3></div>
          <div className="card-body">
            <div
              className={`drop-zone ${dragging ? 'drag' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files); }}
              onClick={() => fileRef.current?.click()}
            >
              <FileSpreadsheet size={28} style={{ color: 'var(--neutral-400)', margin: '0 auto', display: 'block' }} />
              <p>Template hier ablegen oder klicken</p>
              <p style={{ fontSize: 11, marginTop: 4, color: 'var(--neutral-400)' }}>XLSX, DOCX oder PDF (ausfüllbares Formular)</p>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.xls,.docx,.doc,.pdf"
              style={{ display: 'none' }}
              onChange={e => handleFile(e.target.files)}
            />
          </div>
        </div>
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: '48px 0' }}>
          <div className="spinner" style={{ margin: '0 auto 12px' }} />
          <p style={{ color: 'var(--neutral-500)', fontSize: 13 }}>Template wird analysiert und Felder werden befüllt…</p>
        </div>
      )}

      {msg && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6, padding: '8px 14px', fontSize: 13, color: '#1e40af', marginBottom: 16 }}>
          {msg}
        </div>
      )}

      {analysis && (
        <>
          {/* Stats + actions */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 600 }}>{analysis.filename}</h3>
              <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                <span className="badge badge-green">{filledCount} ausgefüllt</span>
                <span className="badge badge-yellow">{uncertainCount} unsicher</span>
                <span className="badge badge-red">{missingCount} fehlend</span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => { setAnalysis(null); setUserEdits({}); }}
              >
                Neues Template
              </button>
              {Object.keys(userEdits).length > 0 && (
                <button className="btn btn-secondary btn-sm" onClick={handleSaveEdits} disabled={saving}>
                  {saving ? 'Speichert…' : 'Speichern'}
                </button>
              )}
              <button className="btn btn-primary btn-sm" onClick={handleExport} disabled={exporting}>
                <Download size={13} />
                {exporting ? 'Exportiert…' : 'Exportieren'}
              </button>
            </div>
          </div>

          <div className="card">
            <div className="card-body" style={{ padding: 0 }}>
              <table className="field-table">
                <thead>
                  <tr>
                    <th style={{ width: '22%' }}>Feld</th>
                    <th style={{ width: '15%' }}>Position</th>
                    <th style={{ width: '33%' }}>KI-Vorschlag / Eingabe</th>
                    <th style={{ width: '20%' }}>Quelle</th>
                    <th style={{ width: '10%' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {fields.map(field => (
                    <tr key={field.field_id}>
                      <td style={{ fontWeight: 500, color: 'var(--neutral-700)' }}>{field.label}</td>
                      <td style={{ color: 'var(--neutral-500)', fontSize: 11 }}>{field.location}</td>
                      <td>
                        {field.status === 'needs_user_input' || field.field_id in userEdits ? (
                          <input
                            className="field-input"
                            value={userEdits[field.field_id] ?? field.filled_value ?? ''}
                            placeholder="Wert eingeben…"
                            onChange={e => handleEdit(field.field_id, e.target.value)}
                          />
                        ) : (
                          <div style={{ fontSize: 12, color: 'var(--neutral-700)' }}>
                            {field.filled_value || <span style={{ color: 'var(--neutral-400)' }}>—</span>}
                            <button
                              style={{ marginLeft: 6, fontSize: 11, color: 'var(--primary)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
                              onClick={() => handleEdit(field.field_id, field.filled_value ?? '')}
                            >
                              bearbeiten
                            </button>
                          </div>
                        )}
                      </td>
                      <td style={{ fontSize: 11, color: 'var(--neutral-500)' }}>
                        {field.citation || '—'}
                        {field.confidence > 0 && (
                          <span className={`badge ${field.confidence >= 0.7 ? 'badge-green' : 'badge-yellow'}`} style={{ marginLeft: 4 }}>
                            {Math.round(field.confidence * 100)}%
                          </span>
                        )}
                      </td>
                      <td>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          {STATUS_ICON[field.status]}
                          <span className={`badge ${STATUS_BADGE[field.status]}`}>
                            {STATUS_LABEL[field.status]}
                          </span>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
