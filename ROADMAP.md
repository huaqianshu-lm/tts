# ROADMAP

## 当前阶段

- `claude-code-api-config` 已完成 `+25%` 音频、字幕和 Timeline 生成并回传 Video 项目，当前等待人工 TTS 质检。
- `how-to-install` 的 TTS、音频、字幕和时间轴均已生成，准备进入视频剪辑流程。

## 已完成

- 创建第二部视频目录 `projects/how-to-install/`。
- 将生成脚本改为支持 `--project-dir`。
- 复制 `claude-code-install` 的口播源到 `projects/how-to-install/source/narration-script.md`。
- 生成 `how-to-install` 的 TTS Script：12 个 Scene、76 个 Segment。
- 以 `+50%` 语速生成 `how-to-install` 的 76 个音频和时间边界文件。
- 生成 176 条字幕 Cue、SRT、VTT 及时间轴 Manifest。
- 明确跨项目流程以经过 Video 校验的 `tts-script.json` 为唯一生成输入，Narration Script 只作为人工追溯副本。
- 接收 `claude-code-api-config` 的 12 个 Scene、60 个 Segment 冻结输入，并通过哈希、ID、空文本和内部制作文字校验。
- 完成 `claude-code-api-config` 的 60 个音频、60 个 Timing、111 条字幕 Cue、SRT／VTT 和 256.248 秒 Timeline，并以 `+25%` 语速记录在 Audio Manifest。
- 修复字幕 Cue 边界 `.strip()` 删除中英文间空格的问题，全部 60 个 Segment 的 Cue 拼接文本恢复为与 TTS Script 逐字一致。

## 进行中

- `claude-code-api-config` 的完整产物已复制到 Video 项目 `local/claude-code-api-config/`，等待用户抽听和字幕核对。

## 下一步

- 用户完成人工 TTS 质检；若存在发音或停顿问题，只重生成指定 Segment 及其下游 Manifest。
- TTS 质检通过后，由 Video 项目进入 Remotion 音画同步。

## 最近验证

- 四个生成脚本通过 Python 编译检查和 CLI 参数检查。
- `--project-dir projects/how-to-install` 的默认输入输出路径解析正确。
- `what-is-claude-code` 的 14 个 Scene、166 个 Segment 及各类 Manifest 保持有效。
- `how-to-install` 的 12 个 Scene、76 个 Segment、176 条字幕 Cue 和 365.736 秒时间轴校验通过。
- 音频清单确认语速为 `+50%`；76 个 MP3 和 76 个时间边界文件均存在且非空。
- `claude-code-api-config` 的 Video／TTS 两份 Narration Script 与 TTS Script 哈希分别一致；JSON 包含 12 个 Scene、60 个唯一 Segment，无空文本和内部制作文字。
- `+25%` 音频命令完成 3 个 Segment；两次在 `02-01` 连接 `speech.platform.bing.com:443` 时被重置，未继续重试。
- `claude-code-api-config` 最终校验通过：12 个 Scene、60 个 Segment、111 条字幕 Cue、256.248 秒总时长，60 个 MP3 实际时长与 Audio Manifest 完全一致。
- 全部字幕 Cue 按 Segment 拼接后与冻结版 `tts-script.json` 逐字一致，SRT／VTT 均为 111 条，未包含内部制作文字。
- 对三个现有项目回放新旧 Cue 边界算法：没有新增文本回归，并修复 `what-is-claude-code` 3 段、`how-to-install` 1 段和 `claude-code-api-config` 1 段由 `.strip()` 导致的空格丢失；旧项目未重新写入产物。
