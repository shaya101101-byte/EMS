# Minimal type stub for ultralytics to satisfy editor/static analysis.
# This file is only used by type checkers / editors. It does not affect runtime behavior.
from typing import Any, Iterable, List, Optional

class Box:
    xyxy: Any
    cls: Any
    conf: Any

class Result:
    boxes: Optional[Iterable[Box]]

class YOLO:
    def __init__(self, weights: Optional[str] = None) -> None: ...
    def __call__(self, image: Any, conf: float = 0.25, iou: float = 0.45) -> List[Result]: ...
    def train(self, *args: Any, **kwargs: Any) -> Any: ...
    def export(self, *args: Any, **kwargs: Any) -> Any: ...
