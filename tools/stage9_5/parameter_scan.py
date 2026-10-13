from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

REGISTER_PATH = Path("data/manifests/stage9_5_parameter_register_v1_2.json")

MATERIAL_RE = re.compile(
    r"(boundary|latenc|window|stride|remainder|threshold|lambda|fusion|seed|rng|"
    r"support|covered|precision|fidelity|stability|complexity|bootstrap|replay|"
    r"anchor|reservoir|batch|learning.?rate|\blr\b|weight.?decay|epoch|patience|"
    r"delta|clock|max.?bucket|min.?window|grace|top.?k|depth|leaf|opportun|periodic|"
    r"feature|dropout|pos.?weight|wilson|\bz\b|cooldown|confirm|persistence|"
    r"overlap|redundan|refinement|conflict|retire|demot|maturity|label|checkpoint)",
    re.I,
)
HASH_RE = re.compile(r"^[0-9a-f]{40,64}$", re.I)
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:(?:\\d{1,3}(?:,\\d{3})+|\\d+)?\\.\\d+|\\d{1,3}(?:,\\d{3})+|\\d+)(?:[eE][-+]?\\d+)?(?![A-Za-z0-9_])")


@dataclass(frozen=True)
class Candidate:
    path: str
    line: int | None
    locator: str
    value: Any
    source_kind: str
    material_reason: str
    registered_ids: tuple[str, ...]
    leverage: str
    excluded: bool = False
    exclusion_reason: str | None = None


def _canonical_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _load_register(root: Path) -> dict[str, Any]:
    payload = json.loads((root / REGISTER_PATH).read_text(encoding="utf-8"))
    if payload.get("protocol_id") != "stage9.5-q1-assurance-v1":
        raise ValueError("Unexpected Stage 9.5 protocol identity in parameter register.")
    return payload


def _flatten_values(value: Any) -> list[Any]:
    out: list[Any] = []
    if isinstance(value, dict):
        for item in value.values():
            out.extend(_flatten_values(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            out.extend(_flatten_values(item))
    else:
        out.append(value)
    return out


def _registered_ids(
    register: dict[str, Any],
    path: str,
    locator: str,
    value: Any,
) -> tuple[str, ...]:
    hits: list[str] = []
    for entry in register["entries"]:
        if path not in entry["source_locations"]:
            continue
        patterns = entry.get("locator_patterns", [])
        if patterns and any(re.search(pattern, locator) for pattern in patterns):
            hits.append(entry["id"])
            continue
        accepted = _flatten_values(entry["accepted_value"])
        for item in accepted:
            if isinstance(value, bool) and isinstance(item, bool) and value is item:
                hits.append(entry["id"])
                break
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if isinstance(item, (int, float)) and not isinstance(item, bool):
                    if float(value) == float(item):
                        hits.append(entry["id"])
                        break
            if isinstance(value, str) and isinstance(item, str):
                if value == item or value in item:
                    hits.append(entry["id"])
                    break
    return tuple(sorted(set(hits)))


def _leverage(locator: str, path: str) -> str:
    text = f"{path} {locator}".lower()
    high = (
        "boundary", "label_latency", "latency", "threshold", "lambda", "fusion",
        "checkpoint", "seed", "rng", "replay", "generation", "validation",
        "precision", "fidelity", "stability", "lifecycle", "demot", "retire",
        "overlap", "conflict", "opportun", "periodic", "window", "endpoint",
        "maturity", "prediction", "detector", "adwin", "page_hinkley",
    )
    return "high" if any(token in text for token in high) else "medium"


def _is_trivial_python_literal(name: str, value: Any) -> str | None:
    if name.startswith("__"):
        return "dunder/internal constant"
    if isinstance(value, int) and value in {-1, 0, 1, 2} and not MATERIAL_RE.search(name):
        return "common indexing/control literal without material semantic name"
    if isinstance(value, str) and (not value or HASH_RE.match(value)):
        return "empty/hash identity handled by provenance audit"
    return None


def _python_candidates(root: Path, path: str, register: dict[str, Any]) -> tuple[list[Candidate], list[Candidate]]:
    source = (root / path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path)
    found: list[Candidate] = []
    excluded: list[Candidate] = []

    def emit(name: str, node: ast.AST, value: Any) -> None:
        reason = _is_trivial_python_literal(name, value)
        material = bool(MATERIAL_RE.search(name))
        if not material and reason is None:
            reason = "literal not attached to a material semantic name"
        candidate = Candidate(
            path=path,
            line=getattr(node, "lineno", None),
            locator=name,
            value=value,
            source_kind="python",
            material_reason="semantic-name match" if material else "excluded",
            registered_ids=_registered_ids(register, path, name, value) if material else (),
            leverage=_leverage(name, path),
            excluded=reason is not None,
            exclusion_reason=reason,
        )
        (excluded if candidate.excluded else found).append(candidate)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: list[ast.expr] = []
            value_node: ast.expr | None = None
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
                value_node = node.value
            else:
                targets = [node.target]
                value_node = node.value
            if value_node is None:
                continue
            try:
                value = ast.literal_eval(value_node)
            except Exception:
                continue
            names: list[str] = []
            for target in targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)
                elif isinstance(target, ast.Attribute):
                    names.append(target.attr)
            for name in names:
                if isinstance(value, (str, int, float, bool)):
                    emit(name, node, value)
                elif isinstance(value, (list, tuple, dict)):
                    for item in _flatten_values(value):
                        if isinstance(item, (str, int, float, bool)):
                            emit(name, node, item)

        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if not kw.arg:
                    continue
                try:
                    value = ast.literal_eval(kw.value)
                except Exception:
                    continue
                if isinstance(value, (str, int, float, bool)):
                    emit(kw.arg, kw, value)

    return found, excluded


def _walk_json(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            locator = f"{prefix}.{key}" if prefix else key
            yield from _walk_json(item, locator)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            locator = f"{prefix}[{index}]"
            yield from _walk_json(item, locator)
    else:
        yield prefix, value


def _json_exclusion_reason(locator: str, value: Any) -> str | None:
    provenance_prefixes = (
        "primary_runtime_reference.",
        "runtime.",
        "requirements.",
        "scientific_source_hashes.",
        "source_hashes.",
        "preparation.",
        "correction.",
        "correction_scope.",
        "historical_v1_execution.",
        "frozen_primary_contract.contract.",
    )
    if locator.startswith(provenance_prefixes):
        return "provenance/runtime/corrected-contract mirror; audited by identity/hash assurance rather than counted as a distinct parameter"
    low = locator.lower()
    if any(token in low for token in ("sha256", "commit", "tree_sha", "manifest_sha", "payload_hash", "file_hash")):
        return "provenance/hash identity handled by reconstruction and hash audit"
    if isinstance(value, str) and HASH_RE.match(value):
        return "hash identity handled by reconstruction and hash audit"
    return None


def _json_candidates(root: Path, path: str, register: dict[str, Any]) -> tuple[list[Candidate], list[Candidate]]:
    payload = json.loads((root / path).read_text(encoding="utf-8"))
    found: list[Candidate] = []
    excluded: list[Candidate] = []
    for locator, value in _walk_json(payload):
        if not isinstance(value, (str, int, float, bool)):
            continue
        material = bool(MATERIAL_RE.search(locator))
        reason: str | None = _json_exclusion_reason(locator, value)
        if reason is None and isinstance(value, str) and not value:
            reason = "empty value"
        elif reason is None and not material:
            reason = "JSON scalar key path does not match material semantic patterns"
        candidate = Candidate(
            path=path,
            line=None,
            locator=locator,
            value=value,
            source_kind="json",
            material_reason="semantic-key match" if material else "excluded",
            registered_ids=_registered_ids(register, path, locator, value) if material and reason is None else (),
            leverage=_leverage(locator, path),
            excluded=reason is not None,
            exclusion_reason=reason,
        )
        (excluded if candidate.excluded else found).append(candidate)
    return found, excluded


def _markdown_candidates(root: Path, path: str, register: dict[str, Any]) -> tuple[list[Candidate], list[Candidate]]:
    found: list[Candidate] = []
    excluded: list[Candidate] = []
    declaration = re.compile(
        r"(?:=|>=|<=|\bexact\b|\bprimary\b|\bfixed\b|\bfrozen\b|"
        r"\bthreshold\b|\blatency\b|\bwindow\b|\bseeds?\b|\bclocks?\b|"
        r"\bsupport\b|\bprecision\b|\bfidelity\b|\bstability\b|"
        r"\bcomplexity\b|\bbootstrap\b|PYTHONHASHSEED|\bmutant)",
        re.I,
    )
    for lineno, raw_line in enumerate((root / path).read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        line = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", raw_line)
        line = re.sub(r"\bStage[- ]?\d+(?:\.\d+)?\b", "Stage", line, flags=re.I)
        line = re.sub(r"\bSection\s+\d+(?:\.\d+)?\b", "Section", line, flags=re.I)
        if not MATERIAL_RE.search(line) or not declaration.search(line):
            continue
        if re.search(
            r"(observed|result|mean|median|confidence interval|approximately|workflow run|"
            r"commit|sha-?256|completed sensitivity|evidence commit)",
            line,
            re.I,
        ):
            excluded.append(Candidate(
                path=path,
                line=lineno,
                locator=stripped[:180],
                value="<line>",
                source_kind="markdown",
                material_reason="excluded",
                registered_ids=(),
                leverage=_leverage(line, path),
                excluded=True,
                exclusion_reason="historical outcome/provenance statement, not an explicit control declaration",
            ))
            continue
        for match in NUMBER_RE.finditer(line):
            raw = match.group(0)
            normalized = raw.replace(",", "")
            try:
                value: Any = (
                    float(normalized)
                    if any(ch in normalized.lower() for ch in ".e")
                    else int(normalized)
                )
            except ValueError:
                continue
            locator = stripped[:180]
            candidate = Candidate(
                path=path,
                line=lineno,
                locator=locator,
                value=value,
                source_kind="markdown",
                material_reason="explicit parameter/control declaration",
                registered_ids=_registered_ids(register, path, locator, value),
                leverage=_leverage(locator, path),
            )
            found.append(candidate)
    return found, excluded


def run(root: Path, output_dir: Path, fail_on_unclassified_high: bool = True) -> dict[str, Any]:
    register = _load_register(root)
    material: list[Candidate] = []
    excluded: list[Candidate] = []

    roots = register["scan_roots"]
    for path in roots["scientific_source"]:
        a, b = _python_candidates(root, path, register)
        material.extend(a); excluded.extend(b)
    for path in roots["manifests"]:
        a, b = _json_candidates(root, path, register)
        material.extend(a); excluded.extend(b)
    for path in roots["protocols"]:
        a, b = _markdown_candidates(root, path, register)
        material.extend(a); excluded.extend(b)

    # Deduplicate exact scan occurrences while preserving distinct lines/locators.
    unique: dict[tuple[Any, ...], Candidate] = {}
    for c in material:
        key = (c.path, c.line, c.locator, json.dumps(c.value, sort_keys=True))
        unique[key] = c
    material = sorted(unique.values(), key=lambda c: (c.path, c.line or 0, c.locator, repr(c.value)))

    unclassified = [c for c in material if not c.registered_ids]
    high_unclassified = [c for c in unclassified if c.leverage == "high"]

    report = {
        "audit_id": "stage9.5-0-parameter-control-completeness-v1_2",
        "protocol_id": register["protocol_id"],
        "upstream_closure_head": register["upstream_closure_head"],
        "parameter_register_sha256": hashlib.sha256((root / REGISTER_PATH).read_bytes()).hexdigest(),
        "scan_roots": roots,
        "counts": {
            "registered_entries": len(register["entries"]),
            "material_candidates": len(material),
            "excluded_candidates": len(excluded),
            "unclassified_material_candidates": len(unclassified),
            "unclassified_high_leverage_candidates": len(high_unclassified),
        },
        "pass": len(high_unclassified) == 0,
        "material_candidates": [asdict(c) for c in material],
        "unclassified_material_candidates": [asdict(c) for c in unclassified],
        "unclassified_high_leverage_candidates": [asdict(c) for c in high_unclassified],
        "exclusion_log": [asdict(c) for c in excluded],
    }
    report["canonical_sha256"] = _canonical_sha256(report)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "parameter_scan_report.json"
    md_path = output_dir / "PARAMETER_SCAN_REPORT.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Stage 9.5-0 Parameter/Control Completeness Scan v1.2",
        "",
        f"- protocol: `{report['protocol_id']}`",
        f"- upstream closure head: `{report['upstream_closure_head']}`",
        f"- register SHA-256: `{report['parameter_register_sha256']}`",
        f"- material candidates: **{report['counts']['material_candidates']}**",
        f"- unclassified material candidates: **{report['counts']['unclassified_material_candidates']}**",
        f"- unclassified high-leverage candidates: **{report['counts']['unclassified_high_leverage_candidates']}**",
        f"- status: **{'PASS' if report['pass'] else 'BLOCKED'}**",
        "",
        "## Unclassified high-leverage candidates",
        "",
    ]
    if high_unclassified:
        for c in high_unclassified:
            lines.append(f"- `{c.path}:{c.line or '-'}` — `{c.locator}` = `{c.value!r}`")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Interpretation",
        "",
        "A blocked scan is preserved as audit evidence. It does not invalidate Stage 8/9 by itself; each candidate must be dispositioned as Class A, B, C, or a registry-completeness correction before Stage 9.5 can close.",
        "",
        "The JSON report retains the full material candidate list and exclusion log.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if fail_on_unclassified_high and high_unclassified:
        raise SystemExit(
            f"Stage 9.5-0 blocked: {len(high_unclassified)} unclassified high-leverage candidates."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("results/audits/stage9_5_v1_2"))
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args()
    run(args.root.resolve(), args.output_dir, fail_on_unclassified_high=not args.no_fail)


if __name__ == "__main__":
    main()