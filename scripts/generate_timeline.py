#!/usr/bin/env python3
"""Build absolute Scene/Segment offsets and export SRT/VTT captions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_project_dir() -> Path:
    return workspace_root() / "projects" / "what-is-claude-code"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def round_time(value: float) -> float:
    return round(value, 3)


def timestamp(value: float, separator: str) -> str:
    """Format seconds as an SRT/VTT timestamp with millisecond precision."""
    milliseconds = max(0, round(value * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{milliseconds:03d}"


def index_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items}


def build_timeline(
    tts_script: dict[str, Any],
    audio_manifest: dict[str, Any],
    subtitle_manifest: dict[str, Any],
    scene_buffer: float,
) -> dict[str, Any]:
    audio_scenes = index_by(audio_manifest["scenes"], "sceneId")
    subtitle_scenes = index_by(subtitle_manifest["scenes"], "sceneId")
    scenes: list[dict[str, Any]] = []
    scene_cursor = 0.0

    for script_scene in tts_script["scenes"]:
        scene_id = script_scene["sceneId"]
        audio_scene = audio_scenes.get(scene_id)
        subtitle_scene = subtitle_scenes.get(scene_id)
        if audio_scene is None or subtitle_scene is None:
            raise ValueError(f"Scene {scene_id} 缺少音频或字幕数据")

        audio_segments = index_by(audio_scene["segments"], "id")
        subtitle_segments = index_by(subtitle_scene["segments"], "segmentId")
        segment_cursor = 0.0
        segments: list[dict[str, Any]] = []

        for script_segment in script_scene["segments"]:
            segment_id = script_segment["id"]
            audio_segment = audio_segments.get(segment_id)
            subtitle_segment = subtitle_segments.get(segment_id)
            if audio_segment is None or subtitle_segment is None:
                raise ValueError(f"Segment {segment_id} 缺少音频或字幕数据")

            duration = float(audio_segment["duration"])
            segments.append(
                {
                    "segmentId": segment_id,
                    "offset": round_time(segment_cursor),
                    "duration": round_time(duration),
                    "end": round_time(segment_cursor + duration),
                    "audioFile": audio_segment["file"],
                    "subtitleFile": subtitle_scene["file"],
                }
            )
            segment_cursor += duration

        narration_duration = round_time(segment_cursor)
        duration = round_time(narration_duration + scene_buffer)
        scenes.append(
            {
                "sceneId": scene_id,
                "offset": round_time(scene_cursor),
                "narrationDuration": narration_duration,
                "buffer": round_time(scene_buffer),
                "duration": duration,
                "end": round_time(scene_cursor + duration),
                "segments": segments,
            }
        )
        scene_cursor += duration

    return {
        "schemaVersion": "1.0",
        "videoId": tts_script["videoId"],
        "sceneBuffer": round_time(scene_buffer),
        "duration": round_time(scene_cursor),
        "scenes": scenes,
    }


def absolute_cues(
    timeline: dict[str, Any], subtitle_manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    subtitle_scenes = index_by(subtitle_manifest["scenes"], "sceneId")
    cues: list[dict[str, Any]] = []
    for timeline_scene in timeline["scenes"]:
        subtitle_scene = subtitle_scenes[timeline_scene["sceneId"]]
        subtitle_segments = index_by(subtitle_scene["segments"], "segmentId")
        for timeline_segment in timeline_scene["segments"]:
            subtitle_segment = subtitle_segments[timeline_segment["segmentId"]]
            for cue in subtitle_segment["cues"]:
                start = timeline_scene["offset"] + timeline_segment["offset"] + cue["start"]
                end = timeline_scene["offset"] + timeline_segment["offset"] + cue["end"]
                cues.append(
                    {
                        "id": cue["id"],
                        "text": cue["text"],
                        "start": round_time(start),
                        "end": round_time(end),
                    }
                )
    return cues


def render_srt(cues: list[dict[str, Any]]) -> str:
    blocks = []
    for index, cue in enumerate(cues, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{timestamp(cue['start'], ',')} --> {timestamp(cue['end'], ',')}",
                    cue["text"],
                ]
            )
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def render_vtt(cues: list[dict[str, Any]]) -> str:
    blocks = ["WEBVTT", ""]
    for cue in cues:
        blocks.extend(
            [
                cue["id"],
                f"{timestamp(cue['start'], '.')} --> {timestamp(cue['end'], '.')}",
                cue["text"],
                "",
            ]
        )
    return "\n".join(blocks)


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
    parser.add_argument("--subtitle-manifest", type=Path, default=None)
    parser.add_argument("--timeline", type=Path, default=None)
    parser.add_argument("--srt", type=Path, default=None)
    parser.add_argument("--vtt", type=Path, default=None)
    parser.add_argument(
        "--scene-buffer",
        type=float,
        default=0.0,
        help="每个 Scene 末尾增加的缓冲秒数，默认 0",
    )
    args = parser.parse_args()
    args.project_dir = args.project_dir.resolve()
    video_assets = args.project_dir / "video-assets"
    if args.tts_script is None:
        args.tts_script = video_assets / "tts-script.json"
    if args.audio_manifest is None:
        args.audio_manifest = video_assets / "audio-manifest.json"
    if args.subtitle_manifest is None:
        args.subtitle_manifest = video_assets / "subtitle-manifest.json"
    if args.timeline is None:
        args.timeline = video_assets / "timeline-manifest.json"
    if args.srt is None:
        args.srt = video_assets / "subtitles/captions.srt"
    if args.vtt is None:
        args.vtt = video_assets / "subtitles/captions.vtt"
    return args


def main() -> None:
    args = parse_args()
    if args.scene_buffer < 0:
        raise SystemExit("错误：--scene-buffer 不能为负数")

    tts_script = load_json(args.tts_script)
    audio_manifest = load_json(args.audio_manifest)
    subtitle_manifest = load_json(args.subtitle_manifest)
    timeline = build_timeline(
        tts_script,
        audio_manifest,
        subtitle_manifest,
        args.scene_buffer,
    )
    cues = absolute_cues(timeline, subtitle_manifest)

    args.timeline.parent.mkdir(parents=True, exist_ok=True)
    args.srt.parent.mkdir(parents=True, exist_ok=True)
    args.vtt.parent.mkdir(parents=True, exist_ok=True)
    args.timeline.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.srt.write_text(render_srt(cues), encoding="utf-8")
    args.vtt.write_text(render_vtt(cues), encoding="utf-8")
    print(f"已生成时间轴：{args.timeline}")
    print(f"已生成 SRT：{args.srt}")
    print(f"已生成 VTT：{args.vtt}")
    print(f"总时长：{timeline['duration']} 秒，{len(cues)} 个绝对时间字幕 Cue")


if __name__ == "__main__":
    main()
