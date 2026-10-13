from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

REGISTER_PATH = Path("data/manifests/stage9_5_parameter_register_v1_7.json")

MATERIAL_RE = re.compile(
    r"(boundary|latenc|window|stride|remainder|threshold|fusion|seed|rng|"
    r"support|covered|precision|fidelity|stability|complexity|bootstrap|replay|"
    r"anchor|reservoir|batch|learning.?rate|\blr\b|weight.?decay|epoch|patience|"
    r"delta|clock|max.?bucket|min.?window|grace|top.?k|depth|leaf|opportun|periodic|"
    r"feature|dropout|pos.?weight|wilson|\bz\b|cooldown|confirm|persistence|"
    r"overlap|redundan|refinement|conflict|retire|demot|maturity|label|checkpoint|"
    r"rows?|(?:^|[^a-z])arm(?:s)?(?:$|[^a-z])|phases?|conditions?|groups?|metrics?|"
    r"primary.?weights?|neural.?weight|min.?instances|alpha|\bmode\b|(?:^|_)weight$|"
    r"hidden|activation|initialization|optimizer|\bloss\b|calibration|workers?|"
    r"background|attribution|selected.?features|min.?samples|source.?rows|"
    r"train|development|post.?benign|drift|lambda)",
    re.I,
)
HASH_RE = re.compile(r"^[0-9a-f]{40,64}$", re.I)
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)?\.\d+|\d{1,3}(?:,\d{3})+|\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")
EXPRESSION_CONTEXT_RE = re.compile(
    r"(generation|validation|replay|latenc|window|threshold|fusion|lambda|periodic|"
    r"opportun|detector|gate|bootstrap|support|precision|fidelity|stability|"
    r"weight|boundary|maturity|label)",
    re.I,
)


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


def _verify_scan_scope(root: Path, register: dict[str, Any]) -> dict[str, Any]:
    bindings = register.get("scan_scope_bindings")
    if not bindings:
        return {"bound": False, "expected_python_sources": [], "actual_python_sources": list(register["scan_roots"]["scientific_source"])}
    expected: set[str] = set()
    manifests = list(bindings["scientific_source_manifests"])
    for relative in manifests:
        payload = json.loads((root / relative).read_text(encoding="utf-8"))
        hashes = payload.get("scientific_source_hashes")
        if not isinstance(hashes, dict):
            raise ValueError(f"Missing scientific_source_hashes in {relative}.")
        expected.update(str(path) for path in hashes if str(path).endswith(".py"))
    expected_list = sorted(expected)
    actual_list = sorted(str(path) for path in register["scan_roots"]["scientific_source"])
    if actual_list != expected_list:
        missing = sorted(set(expected_list) - set(actual_list))
        extra = sorted(set(actual_list) - set(expected_list))
        raise ValueError(
            "Stage 9.5 scientific-source scan scope differs from accepted hash-bound source union. "
            f"missing={missing}, extra={extra}"
        )
    return {
        "bound": True,
        "binding_manifests": manifests,
        "expected_python_sources": expected_list,
        "actual_python_sources": actual_list,
    }


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


def _value_equal(value: Any, item: Any) -> bool:
    if isinstance(value, bool) or isinstance(item, bool):
        return isinstance(value, bool) and isinstance(item, bool) and value is item
    if isinstance(value, (int, float)) and isinstance(item, (int, float)):
        return float(value) == float(item)
    if isinstance(value, str) and isinstance(item, str):
        return value == item
    return False


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
        if patterns and not any(re.search(pattern, locator) for pattern in patterns):
            continue
        accepted = _flatten_values(entry.get("scan_values", entry["accepted_value"]))
        if any(_value_equal(value, item) for item in accepted):
            hits.append(entry["id"])
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
    if name in {"drift_detected", "total_rows", "best_epoch", "stale_epochs"}:
        return "runtime state/sentinel initialization, not a scientific parameter"
    if name == "mode" and isinstance(value, str) and value in {"r", "rb", "w", "wb", "a", "ab", "x", "xb"}:
        return "file I/O mode, not a scientific parameter"
    if isinstance(value, int) and value in {-1, 0, 1, 2} and not MATERIAL_RE.search(name):
        return "common indexing/control literal without material semantic name"
    if isinstance(value, str) and (not value or HASH_RE.match(value)):
        return "empty/hash identity handled by provenance audit"
    return None


def _expression_exclusion_reason(
    *,
    function_name: str,
    line: str,
    value: int | float,
) -> str | None:
    semantic_line = re.sub(
        r"\blambda\s+[A-Za-z_][A-Za-z0-9_]*\s*:",
        "anonymous_function:",
        line,
    )
    stripped = semantic_line.strip()
    if re.search(r"\belse\s+[-+]?0(?:\.0+)?\b", stripped):
        return "mathematical/probability zero fallback"
    if re.search(r"np\.clip\([^)]*,\s*0(?:\.0+)?,\s*1(?:\.0+)?\)", stripped):
        return "probability-domain clipping bound"
    if re.search(r"0(?:\.0+)?\s*<=.*<=\s*1(?:\.0+)?", stripped):
        return "probability-domain validation bound"
    if "where=" in stripped and float(value) == 0.0:
        return "safe division zero fallback/guard"
    if "2.0 * precision * recall" in stripped or "2 * precision * recall" in stripped:
        return "F1 arithmetic identity"
    if re.search(r"1(?:\.0+)?\s*-\s*.*weight", stripped, re.I):
        return "complementary fusion-weight arithmetic"
    if "perf_counter_ns" in stripped and float(value) == 1_000_000_000.0:
        return "nanosecond-to-second unit conversion"
    if "historical" in function_name.lower():
        return "historical failed-run/provenance identity check"
    return None


def _python_candidates(root: Path, path: str, register: dict[str, Any]) -> tuple[list[Candidate], list[Candidate]]:
    if path.startswith("tests/"):
        return [], [
            Candidate(
                path=path,
                line=None,
                locator="<verification-fixture-file>",
                value="<file>",
                source_kind="python_test_fixture",
                material_reason="excluded",
                registered_ids=(),
                leverage="medium",
                excluded=True,
                exclusion_reason="hash-bound verification fixture; test literal values are not scientific parameter declarations",
            )
        ]
    source = (root / path).read_text(encoding="utf-8")
    source_lines = source.splitlines()
    tree = ast.parse(source, filename=path)
    found: list[Candidate] = []
    excluded: list[Candidate] = []
    emitted_line_values: set[tuple[int | None, str]] = set()

    def _value_key(value: Any) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)

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
        emitted_line_values.add((candidate.line, _value_key(value)))
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

    class ExpressionVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.functions: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()

        def visit_Constant(self, node: ast.Constant) -> None:
            value = node.value
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return
            lineno = getattr(node, "lineno", None)
            if (lineno, _value_key(value)) in emitted_line_values:
                return
            line = source_lines[lineno - 1] if lineno and lineno <= len(source_lines) else ""
            function_name = self.functions[-1] if self.functions else ""
            semantic_line = re.sub(
                r"\blambda\s+[A-Za-z_][A-Za-z0-9_]*\s*:",
                "anonymous_function:",
                line,
            )
            line_material = bool(MATERIAL_RE.search(semantic_line))
            context_material = bool(EXPRESSION_CONTEXT_RE.search(function_name))
            context = f"{function_name} {semantic_line}"
            explicit_exclusion = _expression_exclusion_reason(
                function_name=function_name,
                line=line,
                value=value,
            )
            if explicit_exclusion is not None:
                excluded.append(
                    Candidate(
                        path=path,
                        line=lineno,
                        locator=f"{function_name or '<module>'} :: {line.strip()[:160]}",
                        value=value,
                        source_kind="python_expression",
                        material_reason="excluded",
                        registered_ids=(),
                        leverage=_leverage(context, path),
                        excluded=True,
                        exclusion_reason=explicit_exclusion,
                    )
                )
                return
            if not line_material and not (context_material and abs(float(value)) >= 3.0):
                return
            if abs(float(value)) <= 2.0 and not re.search(
                r"(lambda|weight|threshold|support|precision|fidelity|stability|alpha|delta)",
                context,
                re.I,
            ):
                excluded.append(
                    Candidate(
                        path=path,
                        line=lineno,
                        locator=f"{function_name or '<module>'} :: {line.strip()[:160]}",
                        value=value,
                        source_kind="python_expression",
                        material_reason="excluded",
                        registered_ids=(),
                        leverage=_leverage(context, path),
                        excluded=True,
                        exclusion_reason="small expression literal treated as indexing/state bookkeeping absent parameter semantics",
                    )
                )
                return
            locator = f"{function_name or '<module>'} :: {line.strip()[:160]}"
            found.append(
                Candidate(
                    path=path,
                    line=lineno,
                    locator=locator,
                    value=value,
                    source_kind="python_expression",
                    material_reason="material expression literal",
                    registered_ids=_registered_ids(register, path, locator, value),
                    leverage=_leverage(locator, path),
                )
            )

    ExpressionVisitor().visit(tree)
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
        line = re.sub(r"\bStage[- ]?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?\b", "Stage", line, flags=re.I)
        line = re.sub(r"\bSection\s+\d+(?:\.\d+)?\b", "Section", line, flags=re.I)
        line = re.sub(r"<\s*\d+\s*\.\.\s*\d+\s*>", "<range>", line)
        line = re.sub(r"\b\d+\s*\.\.\s*\d+\b", "<range>", line)
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
    scan_scope_verification = _verify_scan_scope(root, register)
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
    ambiguous = [c for c in material if len(c.registered_ids) > 1]
    high_unclassified = [c for c in unclassified if c.leverage == "high"]

    report = {
        "audit_id": "stage9.5-0-parameter-control-completeness-v1_7",
        "protocol_id": register["protocol_id"],
        "upstream_closure_head": register["upstream_closure_head"],
        "parameter_register_sha256": hashlib.sha256((root / REGISTER_PATH).read_bytes()).hexdigest(),
        "scan_roots": roots,
        "scan_scope_verification": scan_scope_verification,
        "counts": {
            "registered_entries": len(register["entries"]),
            "material_candidates": len(material),
            "excluded_candidates": len(excluded),
            "unclassified_material_candidates": len(unclassified),
            "ambiguous_material_candidates": len(ambiguous),
            "unclassified_high_leverage_candidates": len(high_unclassified),
        },
        "pass": len(unclassified) == 0 and len(ambiguous) == 0,
        "material_candidates": [asdict(c) for c in material],
        "unclassified_material_candidates": [asdict(c) for c in unclassified],
        "ambiguous_material_candidates": [asdict(c) for c in ambiguous],
        "unclassified_high_leverage_candidates": [asdict(c) for c in high_unclassified],
        "exclusion_log": [asdict(c) for c in excluded],
    }
    report["canonical_sha256"] = _canonical_sha256(report)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "parameter_scan_report.json"
    md_path = output_dir / "PARAMETER_SCAN_REPORT.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Stage 9.5-0 Parameter/Control Completeness Scan v1.7",
        "",
        f"- protocol: `{report['protocol_id']}`",
        f"- upstream closure head: `{report['upstream_closure_head']}`",
        f"- register SHA-256: `{report['parameter_register_sha256']}`",
        f"- material candidates: **{report['counts']['material_candidates']}**",
        f"- unclassified material candidates: **{report['counts']['unclassified_material_candidates']}**",
        f"- ambiguous material candidates: **{report['counts']['ambiguous_material_candidates']}**",
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

    if fail_on_unclassified_high and (unclassified or ambiguous):
        raise SystemExit(
            f"Stage 9.5-0 blocked: {len(unclassified)} unclassified material "
            f"candidates ({len(high_unclassified)} high-leverage) and "
            f"{len(ambiguous)} ambiguous material mappings."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("results/audits/stage9_5_v1_7"))
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args()
    run(args.root.resolve(), args.output_dir, fail_on_unclassified_high=not args.no_fail)


if __name__ == "__main__":
    main()