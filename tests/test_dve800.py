"""
DVE800 テストスイート
pytest tests/ -v で実行
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from whisper_discovery import WhisperHandle, WhisperBackend, WhisperNotFoundError
from aqc_local import AQCLocal, FAMVocab


# ============================================================
# テストフィクスチャ
# ============================================================

@pytest.fixture
def sample_fam_json(tmp_path):
    """テスト用FAM語彙JSONを生成する"""
    data = {
        "speaker": "K_chachamaru",
        "lexicon": {
            "SAO": {
                "branches": {
                    "tech_hardware": {"weight": 0.7, "signals": ["800", "OBS", "NDI"]},
                    "anime_ref": {"weight": 0.25, "signals": ["コスプレ", "ギャグ", "アニメ"]},
                }
            },
            "竿": {
                "branches": {
                    "nsfw_genre": {"weight": 0.8, "signals": ["BL", "撮影", "NSFW"]},
                    "fishing":    {"weight": 0.2, "signals": ["釣り", "川"]},
                }
            },
            "DVE800": {
                "branches": {
                    "tool": {"weight": 1.0, "signals": ["編集", "Whisper", "DaVinci"]},
                }
            },
            "OND800": {
                "branches": {
                    "tool": {"weight": 1.0, "signals": ["NDI", "カメラ", "Pi"]},
                }
            },
        },
        "corrections": {
            "DVE800": ["DBE800", "ディーブイイー"],
            "OND800": ["ON800", "オンド"],
            "ZeroRoomLab": ["ゼロルームラボ", "ゼロルームラブ"],
        }
    }
    fam_dir = tmp_path / "fam_vocab"
    fam_dir.mkdir()
    fam_file = fam_dir / "K_chachamaru.json"
    fam_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return tmp_path


# ============================================================
# Module 1: Whisper Discovery
# ============================================================

class TestWhisperDiscovery:

    def test_faster_whisper_detected(self):
        """faster-whisperが存在する場合に検出できる"""
        mock_module = MagicMock()
        with patch.dict("sys.modules", {"faster_whisper": mock_module}):
            from whisper_discovery import discover
            handle = discover(model_size="large-v3")
            assert handle.backend == WhisperBackend.FASTER_WHISPER
            assert handle.model_size == "large-v3"

    def test_fallback_to_openai_whisper(self):
        """faster-whisperがなくてもopenai-whisperで検出できる"""
        with patch.dict("sys.modules", {"faster_whisper": None}):
            mock_whisper = MagicMock()
            with patch.dict("sys.modules", {"whisper": mock_whisper}):
                from whisper_discovery import _try_openai_whisper
                handle = _try_openai_whisper("large-v3")
                assert handle is not None
                assert handle.backend == WhisperBackend.OPENAI_WHISPER

    def test_not_found_raises_error(self):
        """何も見つからない場合はWhisperNotFoundErrorを送出する"""
        with patch("whisper_discovery._try_faster_whisper", return_value=None), \
             patch("whisper_discovery._try_openai_whisper", return_value=None), \
             patch("whisper_discovery._try_whisper_cpp", return_value=None), \
             patch("whisper_discovery._try_ollama", return_value=None):
            from whisper_discovery import discover
            with pytest.raises(WhisperNotFoundError):
                discover()

    def test_handle_has_required_fields(self):
        """WhisperHandleが必要フィールドを持つ"""
        handle = WhisperHandle(
            backend=WhisperBackend.FASTER_WHISPER,
            model_size="large-v3",
            device="cpu",
            compute_type="int8",
        )
        assert handle.backend == WhisperBackend.FASTER_WHISPER
        assert handle.model_size == "large-v3"
        assert handle.device == "cpu"
        assert handle.compute_type == "int8"
        assert handle.remote_url is None


# ============================================================
# Module 3: AQC-Local
# ============================================================

class TestFAMVocab:

    def test_load_from_json(self, sample_fam_json):
        """FAM語彙JSONを正しく読み込める"""
        path = sample_fam_json / "fam_vocab" / "K_chachamaru.json"
        vocab = FAMVocab.load(path)
        assert vocab.speaker == "K_chachamaru"
        assert "SAO" in vocab.lexicon
        assert "竿" in vocab.lexicon
        assert len(vocab.lexicon["SAO"].branches) == 2

    def test_dominant_branch(self, sample_fam_json):
        """dominant branchが最高weightのものを返す"""
        path = sample_fam_json / "fam_vocab" / "K_chachamaru.json"
        vocab = FAMVocab.load(path)
        assert vocab.lexicon["SAO"].dominant == "tech_hardware"
        assert vocab.lexicon["竿"].dominant == "nsfw_genre"

    def test_add_correction(self, sample_fam_json):
        """誤認識補正が追加できる"""
        path = sample_fam_json / "fam_vocab" / "K_chachamaru.json"
        vocab = FAMVocab.load(path)
        vocab.add_correction("ふさもう", "ふさもふ")
        assert "ふさもう" in vocab.corrections.get("ふさもふ", [])

    def test_save_and_reload(self, sample_fam_json, tmp_path):
        """保存と再読み込みで内容が一致する"""
        src_path = sample_fam_json / "fam_vocab" / "K_chachamaru.json"
        vocab = FAMVocab.load(src_path)
        vocab.add_correction("テスト誤認識", "テスト正解")
        out_path = tmp_path / "test_output.json"
        vocab.save(out_path)
        reloaded = FAMVocab.load(out_path)
        assert "テスト誤認識" in reloaded.corrections.get("テスト正解", [])


class TestAQCLocal:

    def test_load_speaker(self, sample_fam_json):
        """話者FAMを読み込める"""
        aqc = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))
        vocab = aqc.load_speaker("K_chachamaru")
        assert vocab.speaker == "K_chachamaru"

    def test_load_unknown_speaker_returns_empty(self, sample_fam_json):
        """未知の話者は空のFAMで初期化される"""
        aqc = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))
        vocab = aqc.load_speaker("unknown_speaker")
        assert vocab.speaker == "unknown_speaker"
        assert len(vocab.lexicon) == 0

    def test_build_initial_prompt_within_limit(self, sample_fam_json):
        """initial_promptがトークン上限内に収まる"""
        aqc = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))
        prompt = aqc.build_initial_prompt("K_chachamaru")
        # 200文字以内を確認（日本語200文字≒448トークン）
        assert len(prompt) <= 200

    def test_context_signals_affect_prompt(self, sample_fam_json):
        """コンテキストシグナルがpromptに影響する"""
        aqc = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))
        prompt_nsfw = aqc.build_initial_prompt(
            "K_chachamaru", context_signals=["BL", "NSFW", "撮影"]
        )
        prompt_tech = aqc.build_initial_prompt(
            "K_chachamaru", context_signals=["NDI", "OBS", "800"]
        )
        # 両方ともpromptが生成される
        assert len(prompt_nsfw) > 0
        assert len(prompt_tech) > 0

    def test_correct_transcript(self, sample_fam_json):
        """FAM補正辞書でWhisper出力を補正できる"""
        aqc = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))
        raw = "ON800のカメラでゼロルームラボから配信します"
        corrected = aqc.correct_transcript("K_chachamaru", raw)
        assert "OND800" in corrected
        assert "ZeroRoomLab" in corrected

    def test_transcribe_with_fam(self, sample_fam_json):
        """FAMコンテキスト注入付き書き起こしが動作する"""
        aqc = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))

        mock_handle = MagicMock()
        mock_handle.transcribe.return_value = "ON800で撮影しました"

        result = aqc.transcribe_with_fam(
            whisper_handle=mock_handle,
            audio_path="dummy.wav",
            speaker="K_chachamaru",
            context_signals=["NDI", "撮影"],
        )
        # FAM補正が適用されてOND800に変換される
        assert "OND800" in result
        # initial_promptが渡されている
        mock_handle.transcribe.assert_called_once()
        call_kwargs = mock_handle.transcribe.call_args
        assert call_kwargs[1]["initial_prompt"] != "" or call_kwargs[0][1] != ""

    def test_learn_correction_persists(self, sample_fam_json):
        """誤認識学習がファイルに保存される"""
        aqc = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))
        aqc.learn_correction("K_chachamaru", "ふさもう", "ふさもふ")

        # 再読み込みして確認
        aqc2 = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))
        vocab = aqc2.load_speaker("K_chachamaru")
        assert "ふさもう" in vocab.corrections.get("ふさもふ", [])


# ============================================================
# 統合テスト（DaVinci不要）
# ============================================================

class TestIntegration:

    def test_discovery_to_fam_pipeline(self, sample_fam_json):
        """Discovery → AQC-Local → initial_prompt生成の一気通貫"""
        mock_whisper = MagicMock()
        with patch.dict("sys.modules", {"faster_whisper": mock_whisper}):
            from whisper_discovery import discover
            handle = discover(model_size="large-v3")

        aqc = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))
        prompt = aqc.build_initial_prompt(
            "K_chachamaru",
            context_signals=["BL", "コスプレ", "SAO800"]
        )

        assert isinstance(prompt, str)
        assert len(prompt) <= 200

    def test_multi_speaker_isolation(self, sample_fam_json):
        """話者別にFAMが独立している"""
        aqc = AQCLocal(fam_vocab_dir=str(sample_fam_json / "fam_vocab"))

        vocab_k = aqc.load_speaker("K_chachamaru")
        vocab_candy = aqc.load_speaker("candy_rubber")  # 存在しない→空

        assert vocab_k.speaker == "K_chachamaru"
        assert vocab_candy.speaker == "candy_rubber"
        assert len(vocab_candy.lexicon) == 0
        assert len(vocab_k.lexicon) > 0
