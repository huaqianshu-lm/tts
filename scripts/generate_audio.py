#!/usr/bin/env python3
"""Generate one MP3 and WordBoundary sidecar per TTS segment."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
TICKS_PER_SECOND = 10_000_000


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_project_dir() -> Path:
    return workspace_root() / "projects" / "what-is-claude-code"


def load_script(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def selected_segments(
    tts_script: dict[str, Any],
    scene_id: str | None,
    segment_id: str | None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for scene in tts_script["scenes"]:
        if scene_id and scene["sceneId"] != scene_id:
            continue
        for segment in scene["segments"]:
            if segment_id and segment["id"] != segment_id:
                continue
            selected.append((scene, segment))
    if not selected:
        scope = segment_id or scene_id or "全部内容"
        raise ValueError(f"没有找到匹配的 Segment：{scope}")
    return selected


def seconds(value: int | float) -> float:
    return round(float(value) / TICKS_PER_SECOND, 6)


async def synthesize_segment(
    text: str,
    audio_path: Path,
    timing_path: Path,
    voice: str,
    rate: str,
    pitch: str,
    volume: str,
) -> None:
    try:
        import edge_tts
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "未安装 edge-tts，请先执行：python3 -m pip install -r requirements.txt"
        ) from error

    audio_path.parent.mkdir(parents=True, exist_ok=True)
    timing_path.parent.mkdir(parents=True, exist_ok=True)
    boundaries: list[dict[str, Any]] = []
    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
        boundary="WordBoundary",
    )

    with audio_path.open("wb") as audio_file:
        async for chunk in communicate.stream():
            chunk_type = chunk.get("type")
            if chunk_type == "audio":
                audio_file.write(chunk["data"])
            elif chunk_type and chunk_type.lower() == "wordboundary":
                boundaries.append(
                    {
                        "text": chunk.get("text", ""),
                        "start": seconds(chunk.get("offset", 0)),
                        "duration": seconds(chunk.get("duration", 0)),
                    }
                )

    timing_path.write_text(
        json.dumps(
            {"wordBoundaries": boundaries},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return round(float(result.stdout.strip()), 3)


def build_manifest(
    tts_script: dict[str, Any],
    project_dir: Path,
    voice: str,
    rate: str,
    pitch: str,
    volume: str,
) -> dict[str, Any]:
    scenes: list[dict[str, Any]] = []
    video_assets = project_dir / "video-assets"
    for scene in tts_script["scenes"]:
        manifest_segments: list[dict[str, Any]] = []
        for segment in scene["segments"]:
            audio_path = video_assets / "audio" / f"scene-{scene['sceneId']}" / f"{segment['id']}.mp3"
            if not audio_path.is_file():
                raise FileNotFoundError(f"缺少音频文件：{audio_path}")
            relative_path = audio_path.relative_to(video_assets).as_posix()
            manifest_segments.append(
                {
                    "id": segment["id"],
                    "file": relative_path,
                    "text": segment["text"],
                    "duration": audio_duration(audio_path),
                }
            )
        scenes.append(
            {
                "sceneId": scene["sceneId"],
                "segments": manifest_segments,
                "narrationDuration": round(
                    sum(segment["duration"] for segment in manifest_segments), 3
                ),
            }
        )
    return {
        "schemaVersion": "1.0",
        "videoId": tts_script["videoId"],
        "voice": {
            "name": voice,
            "rate": rate,
            "pitch": pitch,
            "volume": volume,
        },
        "scenes": scenes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=default_project_dir(),
        help="Video project directory",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
    )
    parser.add_argument("--scene", help="只生成指定 Scene，例如 06")
    parser.add_argument("--segment", help="只生成指定 Segment，例如 06-01")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--pitch", default="+0Hz")
    parser.add_argument("--volume", default="+0%")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-manifest", action="store_true")
    args = parser.parse_args()
    args.project_dir = args.project_dir.resolve()
    if args.input is None:
        args.input = args.project_dir / "video-assets/tts-script.json"
    return args


async def run(args: argparse.Namespace) -> None:
    project_dir = args.project_dir
    video_assets = project_dir / "video-assets"
    tts_script = load_script(args.input)
    segments = selected_segments(tts_script, args.scene, args.segment)

    for scene, segment in segments:
        audio_path = video_assets / "audio" / f"scene-{scene['sceneId']}" / f"{segment['id']}.mp3"
        timing_path = video_assets / "timing" / f"scene-{scene['sceneId']}" / f"{segment['id']}.json"
        if audio_path.exists() and timing_path.exists() and not args.force:
            print(f"跳过已存在：{segment['id']}")
            continue
        print(f"生成音频：{segment['id']}")
        await synthesize_segment(
            segment["text"],
            audio_path,
            timing_path,
            args.voice,
            args.rate,
            args.pitch,
            args.volume,
        )

    if not args.no_manifest:
        manifest = build_manifest(
            tts_script,
            project_dir,
            args.voice,
            args.rate,
            args.pitch,
            args.volume,
        )
        manifest_path = video_assets / "audio-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"已生成：{manifest_path}")


def main() -> None:
    try:
        asyncio.run(run(parse_args()))
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise SystemExit(f"错误：{error}") from error


if __name__ == "__main__":
    main()
