"""
DVE800 Module 7: compliance_review — review_ingest
審査フィードバック（STL/SRT/自由記述テキスト等）を`ReviewNote`に正規化する。

担当者依存でフォーマットが揺れることを前提に、固定パーサーではなく
ReviewFormatAdapterプロトコル＋レジストリで拡張可能にする。
"""

from pathlib import Path
from typing import Protocol

from dve800.types import ReviewNote


class ReviewFormatAdapter(Protocol):
    def parse(self, raw: str | Path) -> list[ReviewNote]: ...


ADAPTER_REGISTRY: dict[str, ReviewFormatAdapter] = {}
# STLAdapter / SRTAdapter / FreeformTextAdapter は実データが集まり次第、個別Issueで実装する
