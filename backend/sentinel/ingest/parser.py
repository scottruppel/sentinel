from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

import openpyxl
import structlog

from sentinel.ingest.normalizer import normalize_mpn

log = structlog.get_logger()

COLUMN_MAPPINGS: dict[str, list[str]] = {
    "mpn": [
        "mpn", "manufacturer part number", "mfr part", "mfg part",
        "part number", "mfr pn", "mfg pn", "component part number",
    ],
    "manufacturer": [
        "manufacturer", "mfr", "mfg", "vendor", "mfr name", "manufacturer name",
    ],
    "reference_designator": [
        "reference", "ref des", "refdes", "designator",
        "ref designator", "references",
    ],
    "quantity": ["qty", "quantity", "count", "amount"],
    "description": ["description", "desc", "part description", "component description"],
    "value": ["value", "val", "nominal"],
    "package": ["package", "footprint", "case", "case/package", "pkg"],
    "category": ["category", "type", "part type", "component type"],
}


@dataclass
class ParseWarning:
    row: int | None
    warning: str


@dataclass
class ParsedComponent:
    mpn: str
    mpn_normalized: str
    manufacturer: str | None = None
    reference_designator: str | None = None
    quantity: int = 1
    description: str | None = None
    value: str | None = None
    package: str | None = None
    category: str | None = None


@dataclass
class ParseResult:
    components: list[ParsedComponent] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)
    column_map: dict[str, str] = field(default_factory=dict)


def _detect_columns(headers: list[str]) -> tuple[dict[str, int], list[ParseWarning]]:
    """Map header names to internal field names using fuzzy matching."""
    warnings: list[ParseWarning] = []
    mapping: dict[str, int] = {}
    lower_headers = [h.strip().lower() for h in headers]

    for field_name, candidates in COLUMN_MAPPINGS.items():
        for candidate in candidates:
            for idx, header in enumerate(lower_headers):
                if header == candidate:
                    mapping[field_name] = idx
                    break
            if field_name in mapping:
                break

    if "mpn" not in mapping:
        for idx, header in enumerate(lower_headers):
            if "part" in header and "number" in header:
                mapping["mpn"] = idx
                warnings.append(ParseWarning(
                    row=None,
                    warning=f"Could not identify MPN column — used '{headers[idx]}'",
                ))
                break

    if "mpn" not in mapping:
        raise ValueError("Cannot identify a manufacturer part number column in the BOM headers")

    log.info("column_detection_complete", mapping={k: headers[v] for k, v in mapping.items()})
    return mapping, warnings


def _parse_quantity(val: str | None) -> int:
    if not val:
        return 1
    try:
        return max(1, int(float(str(val).strip())))
    except (ValueError, TypeError):
        return 1


def _parse_rows(
    rows: list[list[str]], col_map: dict[str, int], start_row: int = 2
) -> tuple[list[ParsedComponent], list[ParseWarning]]:
    components: list[ParsedComponent] = []
    warnings: list[ParseWarning] = []
    seen_keys: dict[str, int] = {}

    for row_idx, row in enumerate(rows, start=start_row):
        mpn_idx = col_map["mpn"]
        if mpn_idx >= len(row) or not row[mpn_idx] or not str(row[mpn_idx]).strip():
            continue

        raw_mpn = str(row[mpn_idx]).strip()
        mpn_norm = normalize_mpn(raw_mpn)
        if not mpn_norm:
            continue

        ref_des = str(row[col_map["reference_designator"]]).strip() if "reference_designator" in col_map and col_map["reference_designator"] < len(row) and row[col_map["reference_designator"]] else None
        dedup_key = f"{mpn_norm}|{ref_des or ''}"

        if dedup_key in seen_keys:
            orig_idx = seen_keys[dedup_key]
            components[orig_idx].quantity += _parse_quantity(
                str(row[col_map["quantity"]]).strip() if "quantity" in col_map and col_map["quantity"] < len(row) else None
            )
            warnings.append(ParseWarning(row=row_idx, warning=f"Duplicate MPN: {raw_mpn} (merged quantities)"))
            continue

        seen_keys[dedup_key] = len(components)

        def _get(field: str) -> str | None:
            if field not in col_map or col_map[field] >= len(row):
                return None
            v = row[col_map[field]]
            return str(v).strip() if v else None

        components.append(ParsedComponent(
            mpn=raw_mpn,
            mpn_normalized=mpn_norm,
            manufacturer=_get("manufacturer"),
            reference_designator=ref_des,
            quantity=_parse_quantity(_get("quantity")),
            description=_get("description"),
            value=_get("value"),
            package=_get("package"),
            category=_get("category"),
        ))

    return components, warnings


def parse_csv(content: bytes) -> ParseResult:
    """Parse a CSV BOM file."""
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    if len(rows) < 2:
        raise ValueError("CSV file must have at least a header row and one data row")

    headers = [str(h).strip() for h in rows[0]]
    col_map, detect_warnings = _detect_columns(headers)
    data_rows = [r for r in rows[1:] if any(str(c).strip() for c in r)]
    components, parse_warnings = _parse_rows(data_rows, col_map)

    log.info("csv_parsed", component_count=len(components), warning_count=len(detect_warnings) + len(parse_warnings))

    return ParseResult(
        components=components,
        warnings=detect_warnings + parse_warnings,
        column_map={k: headers[v] for k, v in col_map.items()},
    )


def parse_excel(content: bytes) -> ParseResult:
    """Parse an Excel BOM file."""
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        raise ValueError("Excel file has no active worksheet")

    all_rows = list(ws.iter_rows(values_only=True))
    if len(all_rows) < 2:
        raise ValueError("Excel file must have at least a header row and one data row")

    headers = [str(h).strip() if h else "" for h in all_rows[0]]
    col_map, detect_warnings = _detect_columns(headers)

    data_rows = []
    for row in all_rows[1:]:
        str_row = [str(c).strip() if c is not None else "" for c in row]
        if any(str_row):
            data_rows.append(str_row)

    components, parse_warnings = _parse_rows(data_rows, col_map)

    wb.close()
    log.info("excel_parsed", component_count=len(components), warning_count=len(detect_warnings) + len(parse_warnings))

    return ParseResult(
        components=components,
        warnings=detect_warnings + parse_warnings,
        column_map={k: headers[v] for k, v in col_map.items()},
    )


def parse_bom(filename: str, content: bytes) -> ParseResult:
    """Route to the correct parser based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "csv":
        return parse_csv(content)
    elif ext in ("xlsx", "xls"):
        return parse_excel(content)
    else:
        raise ValueError(f"Unsupported file format: .{ext}. Use .csv or .xlsx")
