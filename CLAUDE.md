# TTS 项目规范

## 目录约定

- `scripts/` 保存所有视频项目共享的生成脚本。
- `projects/<video-id>/source/` 保存对应视频人工维护的源内容。
- `projects/<video-id>/video-assets/` 保存对应视频可重新生成的 TTS、音频和字幕产物。
- `projects/<video-id>/source/narration-script.md` 保存已通过人工 Gate 的口播稿副本，用于人工追溯和核对，不直接作为跨项目自动生成音频的输入。
- Video 项目接入的正式流程以经过校验并冻结的 `projects/<video-id>/video-assets/tts-script.json` 为唯一生成输入；音频、字幕和时间轴必须由同一份 JSON 派生。
- `build_tts_script.py` 只用于 TTS 项目独立维护口播源或显式要求从 Markdown 构建的场景；跨项目接入时不得重新解析 Markdown 覆盖上游提供的 `tts-script.json`。
- `tts-script.json` 的每个 Segment 只能包含实际朗读文本，不得包含 Scene 标题、口播作用、视觉说明、制作备注或 Gate 检查内容。

## 实现约定

- 默认使用 Python 标准库，新增依赖前先说明必要性。
- 保持 Scene 和 Segment 的顺序稳定。
- Segment ID 在音频、字幕和后续时间轴中保持一致。
- 生成流程不得修改项目 `source/` 中的人工源文件。
- 正式生成前必须校验 `tts-script.json` 的 Scene／Segment 数量、ID 唯一性、空文本和内部制作文字；校验未通过时不得启动 TTS。
- 修改后必须执行对应的生成或测试验证。

## 沟通与修改

- 默认使用中文说明，代码、命令和变量名使用英文。
- 只修改当前任务涉及的文件，不顺手重构无关内容。
