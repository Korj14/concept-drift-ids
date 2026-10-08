from __future__ import annotations

import hashlib
import json
import os
import platform
from importlib import metadata
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PRIMARY_THREAD_ENV = {
    "PYTHONHASHSEED": "0",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}

def verify_locked_distributions(
    lock_path: Path = PROJECT_ROOT / "requirements-lock.txt",
) -> dict[str, str]:
    if not lock_path.is_file():
        raise FileNotFoundError(f"Missing frozen dependency lock: {lock_path}")
    expected: dict[str, str] = {}
    for raw_line in lock_path.read_text(
        encoding="utf-8-sig"
    ).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ValueError(
                f"Unsupported non-exact dependency lock entry: {line}"
            )
        name, version = line.split("==", 1)
        name = name.strip()
        version = version.strip()
        if not name or not version:
            raise ValueError(f"Malformed dependency lock entry: {line}")
        if name in expected:
            raise ValueError(f"Duplicate dependency lock entry: {name}")
        expected[name] = version

    actual: dict[str, str] = {}
    mismatches: list[str] = []
    for name, expected_version in expected.items():
        try:
            actual_version = metadata.version(name)
        except metadata.PackageNotFoundError:
            mismatches.append(f"{name}=MISSING expected={expected_version}")
            continue
        actual[name] = actual_version
        if actual_version != expected_version:
            mismatches.append(
                f"{name}={actual_version} expected={expected_version}"
            )
    if mismatches:
        raise RuntimeError(
            "Primary C/D installed dependency versions differ from the "
            "frozen lock: " + "; ".join(mismatches)
        )
    return dict(sorted(actual.items()))


def _distribution_identity(versions: dict[str, str]) -> str:
    encoded = json.dumps(
        versions,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_primary_environment() -> None:
    mismatches = {
        key: os.environ.get(key)
        for key, expected in PRIMARY_THREAD_ENV.items()
        if os.environ.get(key) != expected
    }
    if mismatches:
        detail = ", ".join(
            f"{key}={value!r}" for key, value in sorted(mismatches.items())
        )
        raise RuntimeError(
            "Primary C/D runtime environment is not frozen before numerical "
            f"initialization: {detail}"
        )


def configure_torch_primary_runtime() -> dict[str, Any]:
    require_primary_environment()
    locked_distributions = verify_locked_distributions()

    import torch
    from threadpoolctl import threadpool_info

    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        if torch.get_num_interop_threads() != 1:
            raise
    torch.use_deterministic_algorithms(True, warn_only=True)

    pools = threadpool_info()
    violations = [
        pool
        for pool in pools
        if pool.get("num_threads") not in (None, 1)
        and pool.get("user_api") in {"blas", "openmp"}
    ]
    if violations:
        raise RuntimeError(
            "Primary C/D runtime detected a numerical thread pool using more "
            f"than one thread: {violations}"
        )

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_implementation": platform.python_implementation(),
        "torch_version": torch.__version__,
        "torch_num_threads": torch.get_num_threads(),
        "torch_num_interop_threads": torch.get_num_interop_threads(),
        "torch_deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "thread_environment": dict(PRIMARY_THREAD_ENV),
        "locked_distributions": locked_distributions,
        "locked_distributions_sha256": _distribution_identity(
            locked_distributions
        ),
        "threadpool_info": pools,
    }
