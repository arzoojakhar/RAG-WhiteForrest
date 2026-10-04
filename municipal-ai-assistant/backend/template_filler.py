"""
Template filling module.
Supports Excel (.xlsx), Word (.docx) and fillable PDF forms.
For each field/cell, attempts to fill via RAG; marks unknowns for user review.
"""
from __future__ import annotations

import copy
import io
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

from openpyxl import load_workbook
from docx import Document as DocxDocument

import config
from rag_chain import answer_question

# ── Field model ───────────────────────────────────────────────────────────────

PLACEHOLDER_RE = re.compile(
    r"\{\{([^}]+)\}\}|"          # {{FieldName}}
    r"\[([A-ZÄÖÜ][^\]]{2,})\]|"  # [FELDNAME]
    r"_{3,}",                     # _____ (blank lines)
    re.IGNORECASE,
)


@dataclass
class TemplateField:
    field_id:   str
    label:      str                # human-readable description
    location:   str                # sheet/row/col or paragraph index
    current_value: Optional[str]   # existing value if any
    filled_value:  Optional[str]   = None
    citation:      Optional[str]   = None
    confidence:    float           = 0.0
    status: Literal["filled", "uncertain", "needs_user_input"] = "needs_user_input"


@dataclass
class FilledTemplate:
    original_filename: str
    fields: list[TemplateField] = field(default_factory=list)
    filled_path: Optional[Path] = None


# ── Excel ─────────────────────────────────────────────────────────────────────

def _extract_excel_fields(path: Path) -> list[TemplateField]:
    wb = load_workbook(str(path), data_only=True)
    fields = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                val = cell.value
                if val is None:
                    continue
                val_str = str(val).strip()
                if PLACEHOLDER_RE.search(val_str) or val_str == "":
                    coord = f"{sheet_name}!{cell.coordinate}"
                    # Look at header row to build a label
                    header = ws.cell(row=1, column=cell.column).value or cell.coordinate
                    label = f"{header} (Zeile {cell.row})" if cell.row > 1 else str(header)
                    fields.append(TemplateField(
                        field_id=coord,
                        label=str(label),
                        location=coord,
                        current_value=val_str if val_str else None,
                    ))
    return fields


def _fill_excel(path: Path, fields: list[TemplateField]) -> Path:
    wb = load_workbook(str(path))
    field_map = {f.field_id: f for f in fields}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                coord = f"{sheet_name}!{cell.coordinate}"
                f = field_map.get(coord)
                if f and f.filled_value is not None:
                    cell.value = f.filled_value
                    if f.citation:
                        # Write citation as comment
                        try:
                            from openpyxl.comments import Comment
                            cell.comment = Comment(f"Quelle: {f.citation}", "KI-Assistent")
                        except Exception:
                            pass

    out_path = config.FILLED_OUTPUT_DIR / f"filled_{path.name}"
    wb.save(str(out_path))
    return out_path


# ── Word ──────────────────────────────────────────────────────────────────────

def _extract_docx_fields(path: Path) -> list[TemplateField]:
    doc = DocxDocument(str(path))
    fields = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text
        for match in PLACEHOLDER_RE.finditer(text):
            label = (match.group(1) or match.group(2) or f"Leerzeile in Absatz {i+1}").strip()
            fields.append(TemplateField(
                field_id=f"para_{i}_{match.start()}",
                label=label,
                location=f"Absatz {i+1}",
                current_value=match.group(0),
            ))
    # Also check tables
    for ti, table in enumerate(doc.tables):
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                for match in PLACEHOLDER_RE.finditer(cell.text):
                    label = (match.group(1) or match.group(2) or "Tabellenzelle").strip()
                    fields.append(TemplateField(
                        field_id=f"table_{ti}_row{ri}_col{ci}",
                        label=label,
                        location=f"Tabelle {ti+1}, Zeile {ri+1}, Spalte {ci+1}",
                        current_value=match.group(0),
                    ))
    return fields


def _fill_docx(path: Path, fields: list[TemplateField]) -> Path:
    doc = DocxDocument(str(path))
    field_map = {f.field_id: f for f in fields if f.filled_value}

    def _replace_in_text(text: str, f: TemplateField) -> str:
        if f.current_value:
            replacement = f.filled_value or f.current_value
            if f.citation:
                replacement += f" [Quelle: {f.citation}]"
            return text.replace(f.current_value, replacement)
        return text

    for i, para in enumerate(doc.paragraphs):
        for fid, f in field_map.items():
            if fid.startswith(f"para_{i}_"):
                para.text = _replace_in_text(para.text, f)

    for ti, table in enumerate(doc.tables):
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                for fid, f in field_map.items():
                    if fid == f"table_{ti}_row{ri}_col{ci}":
                        for para in cell.paragraphs:
                            para.text = _replace_in_text(para.text, f)

    out_path = config.FILLED_OUTPUT_DIR / f"filled_{path.name}"
    doc.save(str(out_path))
    return out_path


# ── PDF (fillable AcroForm) ───────────────────────────────────────────────────

def _extract_pdf_fields(path: Path) -> list[TemplateField]:
    """Extract AcroForm field names from a fillable PDF."""
    try:
        import pdfrw
        template = pdfrw.PdfReader(str(path))
        fields = []
        annotations = template.pages
        for page_num, page in enumerate(template.pages, start=1):
            annots = page.get("/Annots")
            if not annots:
                continue
            for annot in annots:
                field_type = annot.get("/FT")
                name = annot.get("/T")
                if name:
                    name_str = str(name).strip("()")
                    fields.append(TemplateField(
                        field_id=name_str,
                        label=name_str,
                        location=f"Seite {page_num}",
                        current_value=str(annot.get("/V", "")).strip("()") or None,
                    ))
        return fields
    except Exception:
        return []


def _fill_pdf(path: Path, fields: list[TemplateField]) -> Path:
    """Fill a PDF AcroForm with the provided field values."""
    try:
        import pdfrw
        ANNOT_KEY = "/Annots"
        ANNOT_FIELD_KEY = "/T"
        ANNOT_VAL_KEY = "/V"
        ANNOT_RECT_KEY = "/Rect"
        SUBTYPE_KEY = "/Subtype"
        WIDGET_SUBTYPE_KEY = "/Widget"

        field_map = {f.field_id: f for f in fields if f.filled_value}
        template = pdfrw.PdfReader(str(path))

        for page in template.pages:
            annots = page.get(ANNOT_KEY)
            if not annots:
                continue
            for annot in annots:
                name = annot.get(ANNOT_FIELD_KEY)
                if name:
                    name_str = str(name).strip("()")
                    if name_str in field_map:
                        f = field_map[name_str]
                        annot.update(pdfrw.PdfDict(
                            V=f.filled_value,
                            AP="",
                        ))

        template.Root.AcroForm.update(pdfrw.PdfDict(NeedAppearances=pdfrw.PdfObject("true")))
        out_path = config.FILLED_OUTPUT_DIR / f"filled_{path.name}"
        pdfrw.PdfWriter().write(str(out_path), template)
        return out_path
    except Exception as e:
        raise RuntimeError(f"PDF-Ausfüllen fehlgeschlagen: {e}")


# ── RAG-based field filling ───────────────────────────────────────────────────

def _build_query_for_field(label: str, context_hint: str = "") -> str:
    base = f"Was ist der Wert für das Feld '{label}' in der kommunalen Wärmeplanung?"
    if context_hint:
        base += f" Kontext: {context_hint}"
    return base


def fill_fields_with_rag(fields: list[TemplateField]) -> list[TemplateField]:
    """
    For each field, query RAG. Fill confident answers; mark rest as needs_user_input.
    """
    for f in fields:
        query = _build_query_for_field(f.label)
        result = answer_question(query)

        if result.is_uncertain or not result.citations:
            f.status = "needs_user_input"
            f.filled_value = None
        else:
            # Only fill if the answer is non-trivial and not "ICH WEISS ES NICHT"
            answer = result.answer.strip()
            if "ICH WEISS ES NICHT" in answer.upper() or len(answer) < 5:
                f.status = "needs_user_input"
            else:
                f.filled_value = answer[:500]  # cap length for form fields
                if result.citations:
                    c = result.citations[0]
                    f.citation = f"{c.source_file}, S.{c.page}"
                f.confidence = result.citations[0].relevance_score if result.citations else 0.0
                f.status = "filled" if f.confidence >= config.MIN_RELEVANCE_SCORE else "uncertain"
    return fields


def apply_user_input(fields: list[TemplateField], updates: dict[str, str]) -> list[TemplateField]:
    """Apply user-provided values to fields that needed input."""
    for f in fields:
        if f.field_id in updates:
            f.filled_value = updates[f.field_id]
            f.status = "filled"
            f.citation = "Manuelle Eingabe"
    return fields


# ── Public API ────────────────────────────────────────────────────────────────

def extract_fields(path: Path) -> list[TemplateField]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return _extract_excel_fields(path)
    elif suffix in {".docx", ".doc"}:
        return _extract_docx_fields(path)
    elif suffix == ".pdf":
        return _extract_pdf_fields(path)
    return []


def produce_filled_file(path: Path, fields: list[TemplateField]) -> Path:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return _fill_excel(path, fields)
    elif suffix in {".docx", ".doc"}:
        return _fill_docx(path, fields)
    elif suffix == ".pdf":
        return _fill_pdf(path, fields)
    raise ValueError(f"Nicht unterstütztes Dateiformat: {suffix}")
