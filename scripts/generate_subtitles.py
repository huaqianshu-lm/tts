#!/usr/bin/env python3
"""Build segment-relative subtitle cues from TTS text and WordBoundary data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MIN_CUE_DURATION = 1.2
MAX_CUE_DURATION = 4.0
MAX_CUE_LENGTH = 26
BREAK_CHARACTERS = set("，。！？；：、,.!?;:")


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_project_dir() -> Path:
    return workspace_root() / "projects" / "what-is-claude-code"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def display_length(text: str) -> float:
    """Estimate visual width, treating ASCII characters as half-width."""
    return sum(0.5 if ord(character) < 128 else 1 for character in text if not character.isspace())


def boundary_spans(
    text: str, boundaries: list[dict[str, Any]]
) -> list[dict[str, Any]] | None:
    spans: list[dict[str, Any]] = []
    cursor = 0
    for boundary in boundaries:
        token = boundary.get("text", "")
        if not token:
            continue
        start = text.find(token, cursor)
        if start < 0:
            return None
        end = start + len(token)
        spans.append(
            {
                "sourceStart": start,
                "sourceEnd": end,
                "start": float(boundary.get("start", 0)),
                "end": float(boundary.get("start", 0))
                + float(boundary.get("duration", 0)),
            }
        )
        cursor = end
    return spans or None


def build_cues(
    text: str,
    boundaries: list[dict[str, Any]],
    audio_duration: float,
    segment_id: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    spans = boundary_spans(text, boundaries)
    if spans is None:
        return (
            [
                {
                    "id": f"{segment_id}-a",
                    "text": text,
                    "start": 0.0,
                    "end": round(audio_duration, 3),
                }
            ],
            [f"{segment_id} 的 WordBoundary 无法与原文对齐，已退化为整段字幕"],
        )

    cues: list[dict[str, Any]] = []
    start_index = 0

    def source_end(index: int) -> int:
        if index + 1 < len(spans):
            return spans[index + 1]["sourceStart"]
        return len(text)

    def finish(end_index: int) -> None:
        nonlocal start_index
        start_span = spans[start_index]
        end_span = spans[end_index]
        cue_start = round(start_span["start"], 3)
        cue_end = round(
            audio_duration if end_index == len(spans) - 1 else spans[end_index + 1]["start"],
            3,
        )
        cue_text = text[start_span["sourceStart"] : source_end(end_index)]
        if cue_text and cue_end > cue_start:
            cues.append(
                {
                    "id": f"{segment_id}-{chr(ord('a') + len(cues))}",
                    "text": cue_text,
                    "start": cue_start,
                    "end": cue_end,
                }
            )
        start_index = end_index + 1

    while start_index < len(spans):
        end_index = start_index
        for index in range(start_index, len(spans)):
            end_time = audio_duration if index == len(spans) - 1 else spans[index + 1]["start"]
            candidate_text = text[spans[start_index]["sourceStart"] : source_end(index)].strip()
            candidate_duration = end_time - spans[start_index]["start"]
            candidate_length = display_length(candidate_text)

            if index > start_index and (
                candidate_duration > MAX_CUE_DURATION
                or candidate_length > MAX_CUE_LENGTH
            ):
                break

            end_index = index
            ends_with_break = candidate_text[-1:] in BREAK_CHARACTERS
            remaining_duration = (
                0
                if index == len(spans) - 1
                else audio_duration - spans[index + 1]["start"]
            )
            if candidate_duration >= MAX_CUE_DURATION:
                break
            if (
                candidate_duration >= MIN_CUE_DURATION
                and (ends_with_break or candidate_length >= MAX_CUE_LENGTH * 0.85)
                and remaining_duration >= MIN_CUE_DURATION
            ):
                break

        while (
            end_index > start_index
            and end_index < len(spans) - 1
            and audio_duration - spans[end_index + 1]["start"] < MIN_CUE_DURATION
        ):
            end_index -= 1
        finish(end_index)

    return cues, []


def create_outputs(
    tts_script: dict[str, Any],
    audio_manifest: dict[str, Any],
    timing_root: Path,
    subtitle_root: Path,
) -> dict[str, Any]:
    manifest_scenes: list[dict[str, Any]] = []
    for scene, audio_scene in zip(tts_script["scenes"], audio_manifest["scenes"]):
        scene_segments: list[dict[str, Any]] = []
        warnings: list[str] = []
        for segment, audio_segment in zip(scene["segments"], audio_scene["segments"]):
            timing_path = timing_root / f"scene-{scene['sceneId']}" / f"{segment['id']}.json"
            timing = load_json(timing_path)
            cues, segment_warnings = build_cues(
                segment["text"],
                timing["wordBoundaries"],
                audio_segment["duration"],
                segment["id"],
            )
            warnings.extend(segment_warnings)
            scene_segments.append(
                {
                    "segmentId": segment["id"],
                    "audioFile": audio_segment["file"],
                    "cues": cues,
                }
            )

        scene_output = {
            "schemaVersion": "1.0",
            "videoId": tts_script["videoId"],
            "sceneId": scene["sceneId"],
            "segments": scene_segments,
        }
        scene_root = subtitle_root / f"scene-{scene['sceneId']}.json"
        scene_root.parent.mkdir(parents=True, exist_ok=True)
        scene_root.write_text(
            json.dumps(scene_output, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest_scenes.append(
            {
                "sceneId": scene["sceneId"],
                "file": scene_root.relative_to(subtitle_root.parent).as_posix(),
                "segments": scene_segments,
            }
        )
        if warnings:
            print("警告：" + "；".join(warnings))

    return {
        "schemaVersion": "1.0",
        "videoId": tts_script["videoId"],
        "scenes": manifest_scenes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=default_project_dir(),
        help="Video project directory",
    )
    parser.add_argument("--tts-script", type=Path, default=None)
    parser.add_argument("--audio-manifest", type=Path, default=None)
    parser.add_argument("--timing-root", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()
    args.project_dir = args.project_dir.resolve()
    video_assets = args.project_dir / "video-assets"
    if args.tts_script is None:
        args.tts_script = video_assets / "tts-script.json"
    if args.audio_manifest is None:
        args.audio_manifest = video_assets / "audio-manifest.json"
    if args.timing_root is None:
        args.timing_root = video_assets / "timing"
    if args.output_root is None:
        args.output_root = video_assets / "subtitles"
    if args.manifest is None:
        args.manifest = video_assets / "subtitle-manifest.json"
    return args


def main() -> None:
    args = parse_args()
    tts_script = load_json(args.tts_script)
    audio_manifest = load_json(args.audio_manifest)
    manifest = create_outputs(
        tts_script,
        audio_manifest,
        args.timing_root,
        args.output_root,
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    cue_count = sum(
        len(segment["cues"])
        for scene in manifest["scenes"]
        for segment in scene["segments"]
    )
    print(f"已生成 {args.manifest}：{len(manifest['scenes'])} 个 Scene，{cue_count} 个 Subtitle Cue")


if __name__ == "__main__":
    main()
