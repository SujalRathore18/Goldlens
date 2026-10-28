from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass(frozen=True)
class EngineConfig:
    executable_price_policy: str = "turnover_or_open"
    slippage_bps: float = 0.0
    minimum_observations: int = 20

    def run_manifest(self) -> dict[str, object]:
        return asdict(self)


def load_contracts(path: str | Path) -> list[dict[str, object]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["contracts"]
