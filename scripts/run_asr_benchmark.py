"""Run isolated local-ASR benchmarks without changing the production Registry."""
from __future__ import annotations

import argparse
import json
import re
import resource
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = ROOT / "backend" / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

import benchmark_asr_providers as scorer
from zhijian.providers.asr import WhisperCppProvider

PROVIDERS = (
    "WHISPER_CPP_BASE",
    "WHISPER_CPP_LARGE_V3_TURBO_Q5",
    "SENSEVOICE_SHERPA_ONNX_INT8",
    "QWEN3_ASR_MLX_0_6B",
)
RUN_DIRECTORY_NAMES = {
    "WHISPER_CPP_BASE": "whisper-base",
    "WHISPER_CPP_LARGE_V3_TURBO_Q5": "whisper-turbo",
    "SENSEVOICE_SHERPA_ONNX_INT8": "sensevoice",
    "QWEN3_ASR_MLX_0_6B": "qwen3-asr",
}
MIN_REVIEWED_SAMPLES = 20
MIN_LONG_FORM_DURATION_MS = 15 * 60 * 1000


class BenchmarkAdapter(Protocol):
    def transcribe(self, media: Path, context_hints: list[str]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class WhisperBenchmarkAdapter:
    binary: str
    model: Path

    def transcribe(self, media: Path, context_hints: list[str]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
        del context_hints
        text, segments = WhisperCppProvider(self.binary, self.model).transcribe(media)
        return text, segments, {}


@dataclass(frozen=True, slots=True)
class CommandBenchmarkAdapter:
    """Run a temporary engine adapter that prints the shared transcript JSON contract."""

    command_template: str

    def transcribe(self, media: Path, context_hints: list[str]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
        values = {"input": str(media), "context": "\n".join(context_hints)}
        command = [part.format(**values) for part in shlex.split(self.command_template)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=3600, check=False)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout or "本地 Adapter 失败")[-500:])
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Benchmark Adapter 必须将 transcript JSON 写入 stdout") from exc
        text = str(payload.get("text") or "").strip()
        segments = payload.get("segments")
        if not text or not isinstance(segments, list):
            raise RuntimeError("Benchmark Adapter 未返回 text 与 segments")
        metrics = dict(payload.get("metrics") or {})
        metrics.update(
            {
                "model_id": payload.get("model"),
                "backend_id": payload.get("backend"),
                "runtime_version": payload.get("runtime_version"),
            }
        )
        return text, [_normalize_segment(item) for item in segments], metrics


def validate_manifest(manifest: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    reviewed_by = str(manifest.get("ground_truth_reviewed_by") or "").strip()
    reviewed_at = str(manifest.get("ground_truth_reviewed_at") or "").strip()
    if not reviewed_by or not reviewed_at:
        raise ValueError("manifest 必须填写人工核对人和核对时间，不能用另一 ASR 输出代替 Ground Truth")
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("manifest.samples 必须是非空数组")
    seen_ids: set[str] = set()
    categories: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw in samples:
        if not isinstance(raw, dict):
            raise TypeError("manifest.samples 的每项必须是对象")
        sample = dict(raw)
        sample_id = str(sample.get("id") or "").strip()
        category = str(sample.get("category") or "").strip()
        audio = str(sample.get("audio") or "").strip()
        reference_text = str(sample.get("reference_text") or "").strip()
        if not sample_id or sample_id in seen_ids:
            raise ValueError("每个 Benchmark sample 必须有唯一 id")
        if category not in scorer.REQUIRED_CATEGORIES:
            raise ValueError(f"sample {sample_id} 的 category 不在冻结六类场景中")
        if not audio or not (manifest_path.parent / audio).is_file():
            raise ValueError(f"sample {sample_id} 的 audio 不存在：{audio}")
        if not reference_text:
            raise ValueError(f"sample {sample_id} 缺少人工核对的 reference_text")
        if not isinstance(sample.get("reference_segments"), list) or not sample["reference_segments"]:
            raise ValueError(f"sample {sample_id} 缺少人工核对的 reference_segments")
        if int(sample.get("duration_ms") or 0) <= 0:
            raise ValueError(f"sample {sample_id} 缺少 duration_ms")
        reference_segments = [_normalize_segment(segment) for segment in sample["reference_segments"]]
        _validate_timeline(reference_segments, int(sample["duration_ms"]))
        seen_ids.add(sample_id)
        categories.add(category)
        sample["audio_path"] = manifest_path.parent / audio
        normalized.append(sample)
    missing = sorted(scorer.REQUIRED_CATEGORIES - categories)
    if missing:
        raise ValueError(f"ASR Benchmark 缺少场景：{'、'.join(missing)}")
    if len(normalized) < MIN_REVIEWED_SAMPLES:
        raise ValueError(f"ASR Benchmark 至少需要 {MIN_REVIEWED_SAMPLES} 个已人工核对 clip")
    if not any(
        sample["category"] == "LONG_FORM"
        and int(sample["duration_ms"]) >= MIN_LONG_FORM_DURATION_MS
        for sample in normalized
    ):
        raise ValueError("LONG_FORM 至少需要一个 15 分钟已人工核对样本")
    replays = manifest.get("full_video_replays")
    if not isinstance(replays, list) or len({str(row.get("id") or "") for row in replays if isinstance(row, dict)}) < 2:
        raise ValueError("manifest 必须记录至少两个完整真实视频回放的独立证据")
    for replay in replays:
        if not isinstance(replay, dict) or not all(str(replay.get(key) or "").strip() for key in ("id", "reviewed_by", "replayed_at")):
            raise ValueError("每个完整视频回放必须含 id、reviewed_by 与 replayed_at")
    return normalized


def run_benchmark(
    samples: list[dict[str, Any]],
    providers: list[str],
    adapters: dict[str, BenchmarkAdapter],
    output_dir: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for provider_id in providers:
        adapter = adapters[provider_id]
        provider_rows: list[dict[str, Any]] = []
        first_measurement = True
        modes = ("DEFAULT", "WITH_CONTEXT") if provider_id == "QWEN3_ASR_MLX_0_6B" else ("DEFAULT",)
        for mode in modes:
            for sample in samples:
                hints = list(sample.get("context_hints") or []) if mode == "WITH_CONTEXT" else []
                started = time.perf_counter()
                try:
                    text, segments, adapter_metrics = adapter.transcribe(sample["audio_path"], hints)
                    runtime_ms = round((time.perf_counter() - started) * 1000)
                    row = _result_row(provider_id, mode, sample, text, segments, runtime_ms, adapter_metrics)
                    if first_measurement:
                        row["first_run_ms"] = runtime_ms
                        first_measurement = False
                    else:
                        row["warm_run_ms"] = runtime_ms
                except (RuntimeError, ValueError, subprocess.TimeoutExpired, OSError) as exc:
                    row = _failed_row(provider_id, mode, sample, str(exc))
                provider_rows.append(row)
        run_dir = output_dir / "runs" / RUN_DIRECTORY_NAMES[provider_id]
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "results.json").write_text(json.dumps(provider_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows.extend(provider_rows)
    return rows


def _result_row(
    provider_id: str,
    mode: str,
    sample: dict[str, Any],
    text: str,
    segments: list[dict[str, Any]],
    runtime_ms: int,
    adapter_metrics: dict[str, Any],
) -> dict[str, Any]:
    _validate_timeline(segments, int(sample["duration_ms"]))
    timeline = _timeline_metrics(sample, segments)
    expected_entities = [str(value) for value in sample.get("expected_entities", [])]
    expected_numbers = [str(value) for value in sample.get("expected_numbers", [])]
    false_hotwords = [
        hint
        for hint in sample.get("context_hints", [])
        if _normalized(hint) not in _normalized(sample["reference_text"]) and _normalized(hint) in _normalized(text)
    ]
    forbidden = [phrase for phrase in sample.get("forbidden_phrases", []) if _normalized(phrase) in _normalized(text)]
    peak_memory = adapter_metrics.get("peak_memory_bytes") or _process_peak_memory_bytes()
    row: dict[str, Any] = {
        "provider": provider_id,
        "benchmark_mode": mode,
        "sample_id": sample["id"],
        "category": sample["category"],
        "expected_entities": expected_entities,
        "actual_entities": [entity for entity in expected_entities if _normalized(entity) in _normalized(text)],
        "expected_numbers": expected_numbers,
        "actual_numbers": [number for number in expected_numbers if _normalized(number) in _normalized(text)],
        "false_hotword_insertions": false_hotwords,
        "text": text,
        "segments": segments,
        "runtime_ms": runtime_ms,
        "peak_memory_bytes": peak_memory,
        "model_load_ms": adapter_metrics.get("model_load_ms"),
        "model_id": adapter_metrics.get("model_id"),
        "backend_id": adapter_metrics.get("backend_id"),
        "runtime_version": adapter_metrics.get("runtime_version"),
        "alignment_runtime_ms": adapter_metrics.get("alignment_runtime_ms"),
        "alignment_peak_memory_bytes": adapter_metrics.get("alignment_peak_memory_bytes"),
        "cer": _cer(sample["reference_text"], text),
        "hallucination_rate": round(len(forbidden) / len(sample.get("forbidden_phrases") or [None]), 4),
        "rtf": round(runtime_ms / sample["duration_ms"], 4),
        "failed": False,
        **timeline,
    }
    return row


def _failed_row(provider_id: str, mode: str, sample: dict[str, Any], error: str) -> dict[str, Any]:
    return {
        "provider": provider_id,
        "benchmark_mode": mode,
        "sample_id": sample["id"],
        "category": sample["category"],
        "expected_entities": sample.get("expected_entities", []),
        "actual_entities": [],
        "expected_numbers": sample.get("expected_numbers", []),
        "actual_numbers": [],
        "runtime_ms": 0,
        "peak_memory_bytes": None,
        "cer": 1.0,
        "segment_coverage": 0.0,
        "timestamp_alignment": 0.0,
        "long_form_drift_ms": None,
        "hallucination_rate": 1.0,
        "rtf": None,
        "failed": True,
        "error": error[-500:],
    }


def _timeline_metrics(sample: dict[str, Any], actual_segments: list[dict[str, Any]]) -> dict[str, Any]:
    reference_segments = [_normalize_segment(segment) for segment in sample["reference_segments"]]
    actual = [_normalize_segment(segment) for segment in actual_segments]
    covered = sum(
        1
        for reference in reference_segments
        if any(_text_similarity(reference["text"], candidate["text"]) >= 0.6 for candidate in actual)
    )
    pairs = zip(reference_segments, actual)
    errors = [
        (abs(reference["start_ms"] - candidate["start_ms"]) + abs(reference["end_ms"] - candidate["end_ms"])) / 2
        for reference, candidate in pairs
    ]
    tolerance = int(sample.get("timestamp_tolerance_ms") or 2000)
    mean_error = sum(errors) / len(errors) if errors else float(tolerance)
    last_end = max((segment["end_ms"] for segment in actual), default=0)
    return {
        "segment_coverage": round(covered / len(reference_segments), 4),
        "timestamp_alignment": round(max(0.0, 1 - mean_error / tolerance), 4),
        "long_form_drift_ms": abs(last_end - sample["duration_ms"])
        if sample["category"] == "LONG_FORM"
        else None,
    }


def _normalize_segment(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("segment 必须是对象")
    text = str(value.get("text") or "").strip()
    start_ms = int(value.get("start_ms") or 0)
    end_ms = int(value.get("end_ms") or 0)
    if not text or start_ms < 0 or end_ms < start_ms:
        raise ValueError("segment 必须有 text、合法 start_ms 与 end_ms")
    return {"text": text, "start_ms": start_ms, "end_ms": end_ms, "locator": dict(value.get("locator") or {})}


def _validate_timeline(segments: list[dict[str, Any]], duration_ms: int) -> None:
    if not segments:
        raise ValueError("ASR 必须返回至少一个带时间码 Segment")
    previous_start = previous_end = -1
    for segment in segments:
        if segment["start_ms"] < previous_start or segment["end_ms"] < previous_end:
            raise ValueError("ASR Segment 时间码不得逆序")
        if segment["end_ms"] > duration_ms + 2000:
            raise ValueError("ASR Segment 时间码异常超出音频时长")
        previous_start, previous_end = segment["start_ms"], segment["end_ms"]


def _cer(reference: str, actual: str) -> float:
    source, target = _normalized(reference), _normalized(actual)
    if not source:
        return 0.0 if not target else 1.0
    previous = list(range(len(target) + 1))
    for index, character in enumerate(source, start=1):
        current = [index]
        for target_index, target_character in enumerate(target, start=1):
            current.append(min(current[-1] + 1, previous[target_index] + 1, previous[target_index - 1] + (character != target_character)))
        previous = current
    return round(previous[-1] / len(source), 4)


def _text_similarity(reference: str, actual: str) -> float:
    source, target = _normalized(reference), _normalized(actual)
    if not source:
        return 1.0 if not target else 0.0
    return 1 - _cer(source, target)


def _normalized(value: object) -> str:
    return "".join(character for character in str(value).lower() if not character.isspace() and not re.match(r"[^\w\u4e00-\u9fff]", character))


def _process_peak_memory_bytes() -> int:
    peak = max(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    )
    return int(peak if sys.platform == "darwin" else peak * 1024)


def _adapter_commands(values: list[str]) -> dict[str, str]:
    commands: dict[str, str] = {}
    for value in values:
        provider, separator, command = value.partition("=")
        if separator != "=" or provider not in PROVIDERS or not command.strip():
            raise ValueError("--adapter-command 需为 PROVIDER=命令，且命令 stdout 必须为 transcript JSON")
        commands[provider] = command
    return commands


def _build_adapters(args: argparse.Namespace, providers: list[str]) -> dict[str, BenchmarkAdapter]:
    commands = _adapter_commands(args.adapter_command)
    adapters: dict[str, BenchmarkAdapter] = {}
    for provider in providers:
        if provider == "WHISPER_CPP_BASE":
            adapters[provider] = WhisperBenchmarkAdapter(args.whisper_binary, args.whisper_base_model)
        elif provider == "WHISPER_CPP_LARGE_V3_TURBO_Q5":
            adapters[provider] = WhisperBenchmarkAdapter(args.whisper_binary, args.whisper_turbo_model)
        elif provider in commands:
            adapters[provider] = CommandBenchmarkAdapter(commands[provider])
        elif provider == "QWEN3_ASR_MLX_0_6B":
            adapters[provider] = CommandBenchmarkAdapter(
                shlex.join(
                    [
                        str(args.qwen_python),
                        str(SCRIPT_DIR / "qwen_asr_runner.py"),
                        "{input}",
                        "--context",
                        "{context}",
                    ]
                )
            )
        else:
            raise ValueError(f"{provider} 需要显式 --adapter-command；实验 Runtime 不写入生产 Registry")
    return adapters


def _render_report(result: dict[str, Any], manifest: dict[str, Any]) -> str:
    lines = [
        "# ASR Benchmark Report",
        "",
        "| Provider | Place Recall | Proper Noun | CER | Coverage | Timestamp | RTF | Peak RAM | Failures |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for provider, values in result["providers"].items():
        lines.append(
            "| {provider} | {place_entity_recall:.4f} | {proper_noun_accuracy:.4f} | {cer} | {segment_coverage} | {timestamp_alignment} | {rtf} | {peak_memory_bytes} | {failure_count} |".format(
                provider=provider,
                place_entity_recall=values["place_entity_recall"],
                proper_noun_accuracy=values["proper_noun_accuracy"],
                cer=_display(values["cer"]),
                segment_coverage=_display(values["segment_coverage"]),
                timestamp_alignment=_display(values["timestamp_alignment"]),
                rtf=_display(values["rtf"]),
                peak_memory_bytes=_display(values["peak_memory_bytes"]),
                failure_count=values["failure_count"],
            )
        )
    lines.extend(["", "## Qwen Context 对照", ""])
    qwen_context = result["qwen_context"]
    if qwen_context:
        without_context = qwen_context["without_context"]
        with_context = qwen_context["with_context"]
        lines.extend(
            [
                "| Mode | Place Recall | Proper Noun | Hallucination |",
                "| --- | ---: | ---: | ---: |",
                "| 无 Context | {place:.4f} | {proper:.4f} | {hallucination} |".format(
                    place=without_context["place_entity_recall"],
                    proper=without_context["proper_noun_accuracy"],
                    hallucination=_display(without_context["hallucination_rate"]),
                ),
                "| 有 Context | {place:.4f} | {proper:.4f} | {hallucination} |".format(
                    place=with_context["place_entity_recall"],
                    proper=with_context["proper_noun_accuracy"],
                    hallucination=_display(with_context["hallucination_rate"]),
                ),
                f"\ncontext_gain: {qwen_context['context_gain']:.4f}",
            ]
        )
    else:
        lines.append("Qwen 无 Context / 有 Context 成对数据尚不完整。")
    recommendation = result["recommendation"]
    lines.extend(
        [
            "",
            "## 决策",
            "",
            f"- 状态：{recommendation['status']}",
            f"- 建议：{recommendation.get('decision') or '待补齐数据'}",
            f"- 原因：{recommendation['reason']}",
            f"- Ground Truth：{manifest['ground_truth_reviewed_by']}，{manifest['ground_truth_reviewed_at']}",
            "- 该结果不改变生产默认 ASR；仍须人工确认、完整真实视频回放和生产接入后的回归。",
            "",
        ]
    )
    return "\n".join(lines)


def _display(value: Any) -> str:
    return "—" if value is None else str(value)


def _example_manifest() -> dict[str, Any]:
    categories = sorted(scorer.REQUIRED_CATEGORIES)
    return {
        "ground_truth_reviewed_by": "填写人工核对人",
        "ground_truth_reviewed_at": "2026-09-16T00:00:00+08:00",
        "samples": [
            {
                "id": f"{categories[index % len(categories)].lower()}_{index + 1:03d}",
                "category": categories[index % len(categories)],
                "audio": (
                    f"clips/{categories[index % len(categories)].lower()}_{index + 1:03d}.wav"
                ),
                "duration_ms": (
                    MIN_LONG_FORM_DURATION_MS
                    if categories[index % len(categories)] == "LONG_FORM"
                    else 30_000
                ),
                "reference_text": "填写人工核对文本",
                "reference_segments": [
                    {
                        "text": "填写人工核对文本",
                        "start_ms": 0,
                        "end_ms": (
                            MIN_LONG_FORM_DURATION_MS
                            if categories[index % len(categories)] == "LONG_FORM"
                            else 30_000
                        ),
                    }
                ],
                "expected_entities": [],
                "expected_numbers": [],
                "context_hints": [],
                "forbidden_phrases": [],
            }
            for index in range(MIN_REVIEWED_SAMPLES)
        ],
        "full_video_replays": [
            {"id": "填写完整视频一", "reviewed_by": "填写人工核对人", "replayed_at": "2026-09-16T00:00:00+08:00"},
            {"id": "填写完整视频二", "reviewed_by": "填写人工核对人", "replayed_at": "2026-09-16T00:00:00+08:00"},
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行与生产 ASR Registry 隔离的本地 Benchmark")
    parser.add_argument("manifest", type=Path, nargs="?", default=Path("data/benchmarks/asr/manifest.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmarks/asr"))
    parser.add_argument("--provider", choices=PROVIDERS, action="append", default=[])
    parser.add_argument("--whisper-binary", default="whisper-cli")
    parser.add_argument("--whisper-base-model", type=Path, default=Path("data/models/whisper/ggml-base.bin"))
    parser.add_argument("--whisper-turbo-model", type=Path, default=Path("data/models/whisper/ggml-large-v3-turbo-q5_0.bin"))
    parser.add_argument(
        "--qwen-python",
        type=Path,
        default=Path("data/runtime/qwen-asr/venv/bin/python"),
        help="隔离 Qwen Runtime 的 Python；Qwen provider 未指定 adapter-command 时使用",
    )
    parser.add_argument("--adapter-command", action="append", default=[], metavar="PROVIDER=COMMAND")
    parser.add_argument("--write-example", type=Path, metavar="PATH")
    args = parser.parse_args()
    if args.write_example:
        args.write_example.parent.mkdir(parents=True, exist_ok=True)
        args.write_example.write_text(json.dumps(_example_manifest(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    providers = args.provider or list(PROVIDERS)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise SystemExit("manifest 必须是 JSON 对象")
    try:
        samples = validate_manifest(manifest, args.manifest)
        rows = run_benchmark(samples, providers, _build_adapters(args, providers), args.output_dir)
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "raw-results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = scorer.evaluate(rows)
    reports = args.output_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "asr_benchmark_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (reports / "ASR_BENCHMARK_REPORT.md").write_text(_render_report(result, manifest), encoding="utf-8")


if __name__ == "__main__":
    main()
