"""Only the settings required by the copied quality module; no .env loading."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    quality_dir: Path

    @property
    def baseline_quality_report(self) -> Path:
        return self.quality_dir / "baseline_quality_report.json"


@dataclass(frozen=True)
class Settings:
    paths: Paths
    freshness_threshold_days: int = 180


def load_settings(project_dir: Path | None = None) -> Settings:
    root = Path(project_dir or Path(__file__).resolve().parents[2]).resolve()
    return Settings(paths=Paths(quality_dir=root / "outputs"))
