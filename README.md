# TTS

面向视频生产流程的轻量 TTS 工具集。它以结构化的 `tts-script.json` 为输入，调用 Microsoft Edge TTS 生成分段 MP3 与 Word Boundary 数据，并继续派生字幕、清单和统一时间轴，供 [Video Harness](https://github.com/huaqianshu-lm/video) 接入 Remotion 制作流程。

## 能力

- 将符合约定的口播 Markdown 转换为 `tts-script.json`。
- 按 Scene／Segment 生成 MP3 和 Word Boundary 数据。
- 根据真实音频时长生成 `audio-manifest.json`。
- 根据口播文本和 Word Boundary 生成逐 Scene 字幕数据。
- 汇总生成 `subtitle-manifest.json`、`timeline-manifest.json`、SRT 和 VTT。
- 支持只重生成指定 Scene 或 Segment，并复用其他已有产物。

## 环境要求

- Python 3.10 或更高版本。
- FFmpeg，且命令行中可以直接执行 `ffprobe`。
- 能访问 Microsoft Edge TTS 服务。

## 安装

```bash
git clone https://github.com/huaqianshu-lm/tts.git
cd tts

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

ffprobe -version
```

Windows PowerShell 激活虚拟环境时使用：

```powershell
.venv\Scripts\Activate.ps1
```

## 输入约定

正式生成链路以经过上游校验并冻结的 `video-assets/tts-script.json` 为唯一输入：

```json
{
  "schemaVersion": "1.0",
  "videoId": "demo-video",
  "scenes": [
    {
      "sceneId": "01",
      "segments": [
        {
          "id": "01-01",
          "text": "这是一段需要实际朗读的口播。"
        }
      ]
    }
  ]
}
```

每个 Segment 只能包含实际朗读文本，不得混入口播作用、视觉说明、制作备注或 Gate 检查内容。音频、字幕和时间轴必须由同一份 `tts-script.json` 派生。

## 完整生成流程

以下示例假设项目目录为 `projects/demo-video`。Video Harness 的 narrated 视频默认使用 `+25%` 语速，因此调用时应显式传入 `--rate +25%`。

### 1．准备 TTS Script

接入 Video Harness 时，直接使用 Harness 已校验并冻结的 `tts-script.json`，不要在 TTS 仓库重新解析 Markdown 覆盖它。

只有独立使用本仓库，并且手上只有符合 Scene 格式的纯口播 Markdown 时，才运行：

```bash
python3 scripts/build_tts_script.py \
  --project-dir projects/demo-video \
  --video-id demo-video
```

Markdown 中的 Scene 标题格式为：

```markdown
## Scene 01｜开场

这是一段需要实际朗读的口播。
```

### 2．生成音频与音频清单

```bash
python3 scripts/generate_audio.py \
  --project-dir projects/demo-video \
  --rate +25%
```

默认语音为 `zh-CN-XiaoxiaoNeural`。可以通过 `--voice`、`--rate`、`--pitch` 和 `--volume` 显式调整。

只生成指定 Scene 或 Segment：

```bash
python3 scripts/generate_audio.py \
  --project-dir projects/demo-video \
  --scene 06 \
  --rate +25%

python3 scripts/generate_audio.py \
  --project-dir projects/demo-video \
  --segment 06-01 \
  --rate +25% \
  --force
```

未使用 `--force` 时，已经同时存在 MP3 和 Timing 文件的 Segment 会被跳过。

### 3．生成字幕数据

```bash
python3 scripts/generate_subtitles.py \
  --project-dir projects/demo-video
```

该命令会读取 TTS Script、Audio Manifest 和 Word Boundary 数据，生成逐 Scene 字幕 JSON 与 `subtitle-manifest.json`。

### 4．生成时间轴、SRT 和 VTT

```bash
python3 scripts/generate_timeline.py \
  --project-dir projects/demo-video
```

如需在每个 Scene 末尾增加停留时间，可以传入非负的 `--scene-buffer`：

```bash
python3 scripts/generate_timeline.py \
  --project-dir projects/demo-video \
  --scene-buffer 0.5
```

## 与 Video Harness 配合

建议将两个仓库放在同一父目录：

```text
video-workspace/
├── video/
└── tts/
```

安装两个仓库的依赖后，Video Harness 默认可以通过相邻的 `../tts` 找到本项目及其 `.venv/bin/python`。具体配置和端到端使用方式见 Video 仓库的 [`docs/TTS-SETUP.md`](https://github.com/huaqianshu-lm/video/blob/main/docs/TTS-SETUP.md)。

## 脚本说明

| 脚本 | 作用 |
| --- | --- |
| `scripts/build_tts_script.py` | 从纯口播 Markdown 构建结构化 TTS Script |
| `scripts/generate_audio.py` | 生成分段 MP3、Word Boundary 和 Audio Manifest |
| `scripts/generate_subtitles.py` | 生成逐 Scene 字幕和 Subtitle Manifest |
| `scripts/generate_timeline.py` | 生成统一 Timeline、SRT 和 VTT |

查看任一脚本的完整参数：

```bash
python3 scripts/generate_audio.py --help
```

## 注意事项

- `generate_audio.py` 会把口播文本发送到 Microsoft Edge TTS 服务，请只处理允许外发的内容。
- 重生成某个 Segment 后，应重新生成 Audio Manifest、字幕和 Timeline，保证下游时间数据一致。
- Video Harness 流程中不要绕过 Gate 2，也不要用未冻结的口播替换正式 `tts-script.json`。

