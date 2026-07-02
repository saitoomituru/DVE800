"""
DVE800 共通型定義
Module間の境界オブジェクトをここに集約する。
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class MosaicRegion:
    """Module 8の出力。フレーム単位の検出候補座標。"""
    frame_number: int
    polygon: tuple[tuple[float, float], ...]  # 正規化座標点列
    confidence: float
    source_model: str  # "lada-yolo11m-seg" 等、由来を明示（ライセンス追跡用）


@dataclass(frozen=True)
class ShotContext:
    distance: Literal["wide", "medium", "close"]
    angle_note: Optional[str] = None


@dataclass(frozen=True)
class ReviewNote:
    """Module 7の出力。審査フィードバックの正規化結果。"""
    timecode: float
    verdict: Literal["pass", "insufficient", "reject"]
    reviewer_comment: str
    shot_context: Optional[ShotContext] = None
