"""
DVE800 Module 7: compliance_review — shot_matcher
タイムコード→`MosaicRegion`のマッチングインターフェース。

実装は次スプリント送り。ここではインターフェースのみ定義する。
"""

from dve800.types import MosaicRegion, ReviewNote


def match_note_to_regions(
    note: ReviewNote,
    regions: list[MosaicRegion],
) -> list[MosaicRegion]:
    """審査ノートのタイムコードに対応する検出候補領域を返す。"""
    raise NotImplementedError
