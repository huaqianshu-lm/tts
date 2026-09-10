#!/usr/bin/env python3
"""Convert the narration Markdown source into a structured TTS script."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCENE_PATTERN = re.compile(r"^##\s+Scene\s+(\d+)\s*(?:[｜|].*)?$", re.IGNORECASE)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_project_dir() -> Path:
    return workspace_root() / "projects" / "what-is-claude-code"


def clean_text(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines)
    text = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    text = re.sub(r"(`+|\*\*|__|~~)", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_tts_script(markdown: str, video_id: str) -> dict:
    scenes: list[dict] = []
    current_scene: dict | None = None
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if current_scene is None:
            paragraph.clear()
            return

        text = clean_text(paragraph)
        paragraph.clear()
        if not text:
            return

        segment_number = len(current_scene["segments"]) + 1
        segment_id = f'{current_scene["sceneId"]}-{segment_number:02d}'
        current_scene["segments"].append({"id": segment_id, "text": text})

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        scene_match = SCENE_PATTERN.match(line)

        if scene_match:
            flush_paragraph()
            scene_id = f"{int(scene_match.group(1)):02d}"
            current_scene = {"sceneId": scene_id, "segments": []}
            scenes.append(current_scene)
            continue

        if current_scene is None:
            continue

        if not line or line == "---":
            flush_paragraph()
            continue

        if line.startswith(">"):
            line = line[1:].lstrip()

        if line.startswith("#"):
            flush_paragraph()
            continue

        paragraph.append(line)

    flush_paragraph()

    if not scenes:
        raise ValueError("未找到 Scene 标题，期望格式为：## Scene 01｜标题")

    empty_scenes = [scene["sceneId"] for scene in scenes if not scene["segments"]]
    if empty_scenes:
        ids = ", ".join(empty_scenes)
        raise ValueError(f"以下 Scene 没有正文内容：{ids}")

    return {
        "schemaVersion": "1.0",
        "videoId": video_id,
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
        help="Narration Markdown source file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Generated TTS Script JSON file",
    )
    parser.add_argument(
        "--video-id",
        default="claude-code-video",
        help="Video identifier stored in the generated JSON",
    )
    args = parser.parse_args()
    args.project_dir = args.project_dir.resolve()
    if args.input is None:
        args.input = args.project_dir / "source/narration-script.md"
    if args.output is None:
        args.output = args.project_dir / "video-assets/tts-script.json"
    return args


def main() -> None:
    args = parse_args()
    markdown = args.input.read_text(encoding="utf-8")
    tts_script = build_tts_script(markdown, args.video_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(tts_script, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    segment_count = sum(len(scene["segments"]) for scene in tts_script["scenes"])
    print(
        f"已生成 {args.output}："
        f"{len(tts_script['scenes'])} 个 Scene，{segment_count} 个 Segment"
    )


if __name__ == "__main__":
    main()
