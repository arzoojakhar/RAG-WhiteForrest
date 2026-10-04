import { useState } from "react";
import { 
  MessageSquare, 
  Database, 
  FileSpreadsheet, 
  Shield, 
  Building2, 
  ChevronDown, 
  Trash2, 
  Plus 
} from "lucide-react";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Templates from "./pages/Templates";
import "./index.css";

type Page = "chat" | "dashboard" | "templates";

type Municipality = {
  id: string;
  name: string;
};

const NAV = [
  { id: "chat" as Page,       label: "Chat",               icon: MessageSquare   },
  { id: "dashboard" as Page,  label: "Wissensbasis",         icon: Database        },
  { id: "templates" as Page,  label: "Vorlagen ausfüllen",   icon: FileSpreadsheet },
];

const PAGE_TITLES: Record<Page, string> = {
  chat:      "Nova - Assistent",
  dashboard: "Wissensbasis verwalten",
  templates: "Vorlagen ausfüllen",
};

const DEFAULT_MUNICIPALITY_ID = "default";

export default function App() {
  const [page, setPage] = useState<Page>("chat");

  // ── UI-Only Municipality State ─────────────────────────────────────────────
  const [municipalities, setMunicipalities] = useState<Municipality[]>([
    { id: DEFAULT_MUNICIPALITY_ID, name: "Freiburg" }
  ]);
  const [activeMunicipalityId, setActiveMunicipalityId] = useState<string>(DEFAULT_MUNICIPALITY_ID);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [muniMsg, setMuniMsg] = useState("");

  const activeMunicipality = municipalities.find(m => m.id === activeMunicipalityId);

  const notify = (msg: string) => {
    setMuniMsg(msg);
    setTimeout(() => setMuniMsg(""), 3500);
  };

  const handleCreate = () => {
    const name = newName.trim();
    if (!name) return;
    
    // Simulate backend ID creation
    const newMuni: Municipality = { id: Date.now().toString(), name };
    
    setMunicipalities(prev => [...prev, newMuni]);
    setActiveMunicipalityId(newMuni.id);
    setNewName("");
    setCreating(false);
    notify(`Gemeinde „${name}“ angelegt.`);
  };

  const handleDelete = (m: Municipality) => {
    if (!window.confirm(`Gemeinde „${m.name}“ wirklich löschen?`)) return;
    
    setMunicipalities(prev => {
      const filtered = prev.filter(x => x.id !== m.id);
      // Reset active ID if the deleted one was currently active
      if (activeMunicipalityId === m.id) {
        setActiveMunicipalityId(filtered.length > 0 ? filtered[0].id : "");
      }
      return filtered;
    });
    
    notify(`Gemeinde „${m.name}“ gelöscht.`);
  };

  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="sidebar-logo">
          <h1>🏛️ Nova KI-Assistent</h1>
          <p>Energiewende &amp; Wärmeplanung</p>
        </div>

        {/* ── Municipality Selector ────────────────────────────────────────── */}
        <div className="municipality-section">
          <div className="municipality-label">
            <Building2 size={13} style={{ display: "inline", marginRight: 5 }} />
            Aktive Gemeinde
          </div>

          {/* Dropdown trigger */}
          <div
            className="municipality-select"
            onClick={() => setDropdownOpen(o => !o)}
          >
            <span className="municipality-select-name">
              {activeMunicipality?.name ?? "Keine Gemeinde"}
            </span>
            <ChevronDown size={14} style={{ flexShrink: 0 }} />
          </div>

          {/* Dropdown list */}
          {dropdownOpen && (
            <div className="municipality-dropdown">
              {municipalities.map(m => (
                <div
                  key={m.id}
                  className={`municipality-option ${m.id === activeMunicipalityId ? "active" : ""}`}
                >
                  <span
                    className="municipality-option-name"
                    onClick={() => { setActiveMunicipalityId(m.id); setDropdownOpen(false); }}
                  >
                    {m.name}
                  </span>
                  {(
                    <button
                      className="municipality-delete-btn"
                      title="Gemeinde löschen"
                      onClick={e => { e.stopPropagation(); setDropdownOpen(false); handleDelete(m); }}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              ))}

              {/* Create new */}
              {creating ? (
                <div className="municipality-create-form">
                  <input
                    autoFocus
                    className="municipality-input"
                    placeholder="Name der Gemeinde…"
                    value={newName}
                    onChange={e => setNewName(e.target.value)}
                    onKeyDown={e => { 
                      if (e.key === "Enter") handleCreate(); 
                      if (e.key === "Escape") { setCreating(false); setNewName(""); }
                    }}
                  />
                  <div style={{ display: "flex", gap: 4, marginTop: 4 }}>
                    <button className="btn btn-primary btn-sm" style={{ flex: 1 }} onClick={handleCreate}>Erstellen</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setCreating(false); setNewName(""); }}>Abbrechen</button>
                  </div>
                </div>
              ) : (
                <div
                  className="municipality-add-btn"
                  onClick={() => setCreating(true)}
                >
                  <Plus size={13} />
                  Neue Gemeinde
                </div>
              )}
            </div>
          )}

          {muniMsg && (
            <div className="municipality-msg">{muniMsg}</div>
          )}
        </div>
        {/* ─────────────────────────────────────────────────────────────────── */}

        <div className="sidebar-nav">
          {NAV.map(item => (
            <div key={item.id} className={`nav-item ${page === item.id ? "active" : ""}`} onClick={() => setPage(item.id)}>
              <item.icon size={16} />
              {item.label}
            </div>
          ))}
        </div>
        <div className="sidebar-footer">
          <Shield size={30} /*style={{ display: "inline", marginRight: 4 }}*/ />
          <span>Lokal &amp; DSGVO-konform</span><br />
          Keine Daten verlassen Ihr System
        </div>
      </nav>
      <div className="main">
        <div className="topbar">
          <h2>{PAGE_TITLES[page]}</h2>
          <span className="badge badge-green">● Lokal</span>
          <span className="badge badge-green">● Mistral</span>
          
          {/* Badge that displays the active municipality */}
          {activeMunicipality && (
            <span className="badge" style={{ background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" }}>
              🏛 {activeMunicipality.name}
            </span>
          )}
        </div>
        
        {/* Pass ID if needed in your components, removed for exact mapping to your snippet */}
        {page === "chat"      && <Chat />}
        {page === "dashboard" && <Dashboard />}
        {page === "templates" && <Templates />}
      </div>
    </div>
  );
}