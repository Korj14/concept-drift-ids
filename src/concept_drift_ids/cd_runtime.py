from __future__ import annotations

import os
import platform
from typing import Any


PRIMARY_THREAD_ENV = {
    "PYTHONHASHSEED": "0",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}


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
        "threadpool_info": pools,
    }
