"""
DVE800 Module 4: DaVinci API Bridge
DaVinci Resolve Python API（無料版対応）でタイムラインを自動構築する

DaVinci Resolve無料版でフル動作。Studio版機能への依存禁止。
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DaVinciNotRunningError(Exception):
    pass


class DaVinciBridge:
    """
    DaVinci Resolve Python APIのブリッジ。
    Resolveが起動していない場合はDaVinciNotRunningErrorを送出する。
    """

    def __init__(self):
        self._resolve = None
        self._project = None
        self._media_pool = None

    def connect(self) -> None:
        """DaVinci Resolveに接続する"""
        module_path = os.environ.get("DAVINCI_MODULE_PATH", "")
        if module_path and module_path not in sys.path:
            sys.path.append(module_path)

        try:
            import DaVinciResolveScript as dvr
            self._resolve = dvr.scriptapp("Resolve")
            if not self._resolve:
                raise DaVinciNotRunningError(
                    "DaVinci Resolveが起動していません。Resolveを起動してから再実行してください。"
                )
            self._project = self._resolve.GetProjectManager().GetCurrentProject()
            self._media_pool = self._project.GetMediaPool()
            logger.info("DaVinci Resolve接続成功")
        except ImportError:
            raise DaVinciNotRunningError(
                "DaVinciResolveScriptが見つかりません。"
                "DAVINCI_MODULE_PATHを確認してください。"
            )

    @property
    def resolve(self):
        if not self._resolve:
            raise DaVinciNotRunningError("connect()を先に呼んでください")
        return self._resolve

    def import_media(self, folder_path: str) -> list:
        """フォルダ内の素材をメディアプールにインポートする"""
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"素材フォルダが見つかりません: {folder_path}")

        extensions = {".mp4", ".mov", ".mxf", ".avi", ".mkv", ".wav", ".mp3", ".aac"}
        files = [
            str(f) for f in folder.iterdir()
            if f.suffix.lower() in extensions
        ]
        if not files:
            logger.warning(f"インポート対象ファイルなし: {folder_path}")
            return []

        clips = self._media_pool.ImportMedia(files)
        logger.info(f"メディアインポート: {len(clips)}クリップ")
        return clips

    def create_timeline(
        self,
        name: str,
        clips: Optional[list] = None,
        framerate: str = "29.97",
        resolution: tuple = (1920, 1080),
    ):
        """タイムラインを作成してクリップを追加する"""
        timeline = self._media_pool.CreateEmptyTimeline(name)
        if not timeline:
            raise RuntimeError(f"タイムライン作成失敗: {name}")

        self._project.SetCurrentTimeline(timeline)

        if clips:
            self._media_pool.AppendToTimeline(clips)
            logger.info(f"タイムライン構築: {name} ({len(clips)}クリップ)")

        return timeline

    def import_srt(self, srt_path: str, timeline=None) -> bool:
        """SRTファイルをタイムラインにインポートする（字幕トラック）"""
        if not Path(srt_path).exists():
            logger.error(f"SRTファイルが見つかりません: {srt_path}")
            return False

        timeline = timeline or self._project.GetCurrentTimeline()
        if not timeline:
            logger.error("アクティブなタイムラインがありません")
            return False

        # DaVinci無料版でのSRTインポート（メディアプール経由）
        clips = self._media_pool.ImportMedia([srt_path])
        if clips:
            logger.info(f"SRTインポート成功: {srt_path}")
            return True

        logger.warning(f"SRTインポート失敗: {srt_path}")
        return False

    def add_marker(
        self,
        frame: int,
        color: str = "Yellow",
        name: str = "",
        note: str = "",
        timeline=None,
    ) -> bool:
        """タイムラインにマーカーを追加する"""
        timeline = timeline or self._project.GetCurrentTimeline()
        if not timeline:
            return False
        return timeline.AddMarker(frame, color, name, note, 1)

    def render_to_queue(
        self,
        output_path: str,
        preset_name: str = "H.264 Master",
    ) -> bool:
        """レンダーキューに追加する（実行はユーザーが行う）"""
        render_settings = {
            "SelectAllFrames": True,
            "TargetDir": str(Path(output_path).parent),
            "CustomName": Path(output_path).stem,
        }
        self._project.SetRenderSettings(render_settings)
        job_id = self._project.AddRenderJob()
        if job_id:
            logger.info(f"レンダーキュー追加: {output_path}")
            return True
        return False

    def get_status(self) -> dict:
        """現在の接続状態を返す"""
        if not self._resolve:
            return {"connected": False}
        return {
            "connected": True,
            "project": self._project.GetName() if self._project else None,
            "timeline": (
                self._project.GetCurrentTimeline().GetName()
                if self._project and self._project.GetCurrentTimeline()
                else None
            ),
        }
