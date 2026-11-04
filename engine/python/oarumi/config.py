"""Engine configuration, sourced from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EngineConfig:
    home: Path
    strict_parity: bool
    dev_models: bool
    offline: bool
    log_level: str

    @classmethod
    def from_env(cls) -> EngineConfig:
        home = Path(os.environ.get("OARUMI_HOME", ".")).resolve()
        return cls(
            home=home,
            strict_parity=os.environ.get("OARUMI_STRICT_PARITY", "0") == "1",
            dev_models=os.environ.get("OARUMI_DEV_MODELS", "1") == "1",
            offline=os.environ.get("OARUMI_OFFLINE", "0") == "1",
            log_level=os.environ.get("OARUMI_LOG_LEVEL", "INFO"),
        )

    @property
    def db_path(self) -> Path:
        return self.home / "language" / "oarumi.db"
