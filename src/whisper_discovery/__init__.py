"""
DVE800 Module 1: Whisper Discovery
既存のWhisper実装を環境から検出する

検出優先順位：
1. faster-whisper（VRAM効率最良）
2. openai-whisper（オリジナル）
3. whisper.cpp（バイナリ）
4. ollama経由whisper
5. ネットワーク越しOND800上のwhisper-server
"""

import logging
import subprocess
import importlib
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class WhisperBackend(Enum):
    FASTER_WHISPER = "faster-whisper"
    OPENAI_WHISPER = "openai-whisper"
    WHISPER_CPP = "whisper.cpp"
    OLLAMA = "ollama"
    REMOTE = "remote"


@dataclass
class WhisperHandle:
    """検出されたWhisper実装のハンドル"""
    backend: WhisperBackend
    model_size: str
    device: str
    compute_type: str
    remote_url: Optional[str] = None

    def transcribe(self, audio_path: str, initial_prompt: str = "") -> str:
        """音声ファイルを書き起こす"""
        if self.backend == WhisperBackend.FASTER_WHISPER:
            return _transcribe_faster_whisper(self, audio_path, initial_prompt)
        elif self.backend == WhisperBackend.OPENAI_WHISPER:
            return _transcribe_openai_whisper(self, audio_path, initial_prompt)
        elif self.backend == WhisperBackend.REMOTE:
            return _transcribe_remote(self, audio_path, initial_prompt)
        else:
            raise NotImplementedError(f"Backend {self.backend} transcribe未実装")


def discover(
    model_size: str = "large-v3",
    device: str = "auto",
    compute_type: str = "int8",
    remote_url: Optional[str] = None,
) -> WhisperHandle:
    """
    利用可能なWhisperを検出して返す。
    見つからない場合はwhisper_installerに委譲することを想定。

    Raises:
        WhisperNotFoundError: どのバックエンドも見つからない場合
    """
    logger.info("Whisper環境を検出中...")

    # 1. faster-whisper
    handle = _try_faster_whisper(model_size, device, compute_type)
    if handle:
        logger.info(f"faster-whisper を検出: device={handle.device}")
        return handle

    # 2. openai-whisper
    handle = _try_openai_whisper(model_size)
    if handle:
        logger.info("openai-whisper を検出")
        return handle

    # 3. whisper.cpp
    handle = _try_whisper_cpp(model_size)
    if handle:
        logger.info("whisper.cpp を検出")
        return handle

    # 4. ollama
    handle = _try_ollama(model_size)
    if handle:
        logger.info("ollama経由Whisperを検出")
        return handle

    # 5. リモート（OND800上のwhisper-server）
    if remote_url:
        handle = _try_remote(remote_url, model_size)
        if handle:
            logger.info(f"リモートWhisperを検出: {remote_url}")
            return handle

    raise WhisperNotFoundError(
        "Whisperが見つかりません。`python -m dve800.setup` を実行してください。"
    )


class WhisperNotFoundError(Exception):
    pass


def _try_faster_whisper(
    model_size: str, device: str, compute_type: str
) -> Optional[WhisperHandle]:
    try:
        import faster_whisper  # noqa: F401
        resolved_device = _resolve_device(device)
        return WhisperHandle(
            backend=WhisperBackend.FASTER_WHISPER,
            model_size=model_size,
            device=resolved_device,
            compute_type=compute_type,
        )
    except ImportError:
        return None


def _try_openai_whisper(model_size: str) -> Optional[WhisperHandle]:
    try:
        import whisper  # noqa: F401
        return WhisperHandle(
            backend=WhisperBackend.OPENAI_WHISPER,
            model_size=model_size,
            device="cpu",
            compute_type="float32",
        )
    except ImportError:
        return None


def _try_whisper_cpp(model_size: str) -> Optional[WhisperHandle]:
    try:
        result = subprocess.run(
            ["whisper-cpp", "--version"],
            capture_output=True, timeout=5
        )
        if result.returncode == 0:
            return WhisperHandle(
                backend=WhisperBackend.WHISPER_CPP,
                model_size=model_size,
                device="cpu",
                compute_type="float32",
            )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _try_ollama(model_size: str) -> Optional[WhisperHandle]:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        if "whisper" in result.stdout.lower():
            return WhisperHandle(
                backend=WhisperBackend.OLLAMA,
                model_size=model_size,
                device="cpu",
                compute_type="float32",
            )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _try_remote(url: str, model_size: str) -> Optional[WhisperHandle]:
    try:
        import urllib.request
        urllib.request.urlopen(f"{url}/health", timeout=3)
        return WhisperHandle(
            backend=WhisperBackend.REMOTE,
            model_size=model_size,
            device="remote",
            compute_type="remote",
            remote_url=url,
        )
    except Exception:
        return None


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def _transcribe_faster_whisper(
    handle: WhisperHandle, audio_path: str, initial_prompt: str
) -> str:
    from faster_whisper import WhisperModel
    model = WhisperModel(
        handle.model_size,
        device=handle.device,
        compute_type=handle.compute_type
    )
    segments, _ = model.transcribe(
        audio_path,
        initial_prompt=initial_prompt,
        language="ja",
    )
    return "".join(seg.text for seg in segments)


def _transcribe_openai_whisper(
    handle: WhisperHandle, audio_path: str, initial_prompt: str
) -> str:
    import whisper
    model = whisper.load_model(handle.model_size)
    result = model.transcribe(
        audio_path,
        initial_prompt=initial_prompt,
        language="ja",
    )
    return result["text"]


def _transcribe_remote(
    handle: WhisperHandle, audio_path: str, initial_prompt: str
) -> str:
    import urllib.request
    import json
    payload = json.dumps({
        "audio_path": audio_path,
        "initial_prompt": initial_prompt,
        "language": "ja",
    }).encode()
    req = urllib.request.Request(
        f"{handle.remote_url}/transcribe",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())["text"]
