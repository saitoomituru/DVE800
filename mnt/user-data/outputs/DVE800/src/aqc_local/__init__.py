"""
DVE800 Module 3: AQC-Local
FAM多義性マップの管理・ChromaDB統合・Whisper initial_prompt生成

AQC（Astro Quantaril Cloud）の思想的後継として、
ベンダー封鎖された注意関数介入をローカルWhisperで再実装する。
責任はDVE800運用者にある。
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_PROMPT_TOKENS = 448  # Whisper-L有効上限


@dataclass
class FAMBranch:
    weight: float
    signals: list[str]


@dataclass
class FAMLexicon:
    branches: dict[str, FAMBranch]

    @property
    def dominant(self) -> str:
        return max(self.branches, key=lambda k: self.branches[k].weight)


@dataclass
class FAMVocab:
    """話者別FAM多義性マップ"""
    speaker: str
    lexicon: dict[str, FAMLexicon] = field(default_factory=dict)
    corrections: dict[str, list[str]] = field(default_factory=dict)
    # corrections: {正: [誤認識候補, ...]}

    @classmethod
    def load(cls, path: Path) -> "FAMVocab":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        vocab = cls(speaker=data["speaker"])
        for word, lex_data in data.get("lexicon", {}).items():
            branches = {
                k: FAMBranch(
                    weight=v["weight"],
                    signals=v.get("signals", [])
                )
                for k, v in lex_data["branches"].items()
            }
            vocab.lexicon[word] = FAMLexicon(branches=branches)
        vocab.corrections = data.get("corrections", {})
        return vocab

    def save(self, path: Path) -> None:
        data = {
            "speaker": self.speaker,
            "lexicon": {
                word: {
                    "branches": {
                        k: {"weight": b.weight, "signals": b.signals}
                        for k, b in lex.branches.items()
                    }
                }
                for word, lex in self.lexicon.items()
            },
            "corrections": self.corrections,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_correction(self, wrong: str, correct: str) -> None:
        """誤認識フィードバックをFAMに学習させる"""
        if correct not in self.corrections:
            self.corrections[correct] = []
        if wrong not in self.corrections[correct]:
            self.corrections[correct].append(wrong)
            logger.info(f"FAM学習: '{wrong}' → '{correct}'")


class AQCLocal:
    """
    FAM多義性マップを管理し、Whisper-L用initial_promptを動的生成する。

    GPTs SDK 3.5が持っていたLoRA的注意関数介入の精神的後継。
    ベンダーの封鎖を迂回してローカルWhisperで実装する。
    """

    def __init__(self, fam_vocab_dir: str = "./fam_vocab"):
        self.vocab_dir = Path(fam_vocab_dir)
        self._cache: dict[str, FAMVocab] = {}

    def load_speaker(self, speaker: str) -> FAMVocab:
        """話者のFAM語彙を読み込む"""
        if speaker in self._cache:
            return self._cache[speaker]
        path = self.vocab_dir / f"{speaker}.json"
        if not path.exists():
            logger.warning(f"FAM語彙が見つかりません: {path}。空で初期化します。")
            vocab = FAMVocab(speaker=speaker)
        else:
            vocab = FAMVocab.load(path)
            logger.info(f"FAM語彙ロード: {speaker} ({len(vocab.lexicon)}語彙)")
        self._cache[speaker] = vocab
        return vocab

    def build_initial_prompt(
        self,
        speaker: str,
        context_signals: Optional[list[str]] = None,
    ) -> str:
        """
        現在のコンテキストシグナルからWhisper-L用initial_promptを生成する。
        Whisper-Lの有効上限（448トークン≒約200文字）以内に収める。
        """
        vocab = self.load_speaker(speaker)
        context_signals = context_signals or []

        # コンテキストシグナルに反応するFoldを優先的に選出
        prioritized: list[tuple[str, float]] = []
        for word, lex in vocab.lexicon.items():
            max_weight = 0.0
            for branch in lex.branches.values():
                signal_hit = any(s in context_signals for s in branch.signals)
                w = branch.weight * (1.5 if signal_hit else 1.0)
                max_weight = max(max_weight, w)
            prioritized.append((word, max_weight))

        prioritized.sort(key=lambda x: x[1], reverse=True)

        # corrections（誤認識補正語彙）を追加
        correction_terms = list(vocab.corrections.keys())

        # プロンプト構築（トークン上限内に収める）
        lines = ["以下の語彙・固有名詞が登場します："]
        chars = len(lines[0])
        char_limit = 180  # 日本語200文字≒448トークン（余裕を持たせる）

        for word, _ in prioritized:
            entry = f"{word}"
            if chars + len(entry) + 1 > char_limit:
                break
            lines.append(entry)
            chars += len(entry) + 1

        if correction_terms:
            lines.append("（補正語彙）" + "、".join(correction_terms[:10]))

        prompt = "、".join(lines[1:]) if len(lines) > 1 else ""
        logger.debug(f"initial_prompt生成: {len(prompt)}文字")
        return prompt

    def correct_transcript(self, speaker: str, text: str) -> str:
        """FAM補正辞書でWhisper出力を後処理する"""
        vocab = self.load_speaker(speaker)
        for correct, wrongs in vocab.corrections.items():
            for wrong in wrongs:
                text = text.replace(wrong, correct)
        return text

    def learn_correction(
        self, speaker: str, wrong: str, correct: str
    ) -> None:
        """誤認識をFAMに学習させてファイルに保存する"""
        vocab = self.load_speaker(speaker)
        vocab.add_correction(wrong, correct)
        path = self.vocab_dir / f"{speaker}.json"
        vocab.save(path)

    def transcribe_with_fam(
        self,
        whisper_handle,
        audio_path: str,
        speaker: str,
        context_signals: Optional[list[str]] = None,
    ) -> str:
        """
        FAMコンテキストを注入してWhisperで書き起こし、後処理補正も適用する。
        DVE800のコア処理。
        """
        prompt = self.build_initial_prompt(speaker, context_signals)
        logger.info(f"書き起こし開始: speaker={speaker}, prompt={prompt[:50]}...")
        raw = whisper_handle.transcribe(audio_path, initial_prompt=prompt)
        corrected = self.correct_transcript(speaker, raw)
        if raw != corrected:
            logger.info("FAM補正適用済み")
        return corrected
