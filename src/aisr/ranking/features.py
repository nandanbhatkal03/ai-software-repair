from __future__ import annotations
from dataclasses import dataclass, asdict
from ..repair.candidates import Patch
from ..validation.pipeline import ValidationResult

@dataclass
class Features:
    fl_score: float          # suspiciousness of the patched location, [0,1]
    regression_clean: float  # 1.0 if regression stage passed
    static_improvement: float  # in [0,1]; 0.5 neutral/unknown
    patch_size: float        # 1/(1+changed_lines): smaller patches preferred
    mutation_score: float    # [0,1], 0.5 neutral/unknown
    llm_origin: float        # reserved feature: 1 if proposed by a model (lets ablations test origin bias)
    def as_dict(self) -> dict: return asdict(self)

def extract(patch: Patch, v: ValidationResult, fl_score: float) -> Features:
    static = 0.5 if v.static_delta is None else (1.0 if v.static_delta < 0 else 0.5 if v.static_delta == 0 else 0.0)
    return Features(fl_score, 1.0 if v.stages.get("regression") else 0.0, static,
                    1.0 / (1 + patch.changed_lines), 0.5 if v.mutation_score is None else v.mutation_score,
                    1.0 if patch.origin.startswith("llm") else 0.0)
