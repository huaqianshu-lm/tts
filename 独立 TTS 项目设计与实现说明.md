# 九、第七步：TTS Script

## 目的

Narration Script 还是面向内容和口播的文档。

真正进入 TTS 前，再加工成：

> **TTS Script**

主要解决两件事：

### 1. 拆 Narration Segment

一个 Scene 可以拆成多个 Narration Segment。

例如：

```text
Scene 06

06-01
这里其实还涉及一个现在非常重要的概念：Agent。

06-02
过去我们用 AI 写代码时，人的角色其实非常重。

06-03
Agent 的变化就在这里。

06-04
人开始从管理每一步操作，转向管理最终目标。
```

### 2. 清理 TTS 文本

包括：

- 去掉 Markdown
- 去掉标题
- 调整标点
- 控制停顿
- 统一数字读法
- 统一英文产品名
- 处理技术词发音

## 推荐结构

```json
{
  "videoId": "what-is-claude-code",
  "scenes": [
    {
      "sceneId": "06",
      "segments": [
        {
          "id": "06-01",
          "text": "这里其实还涉及一个现在非常重要的概念：Agent。"
        }
      ]
    }
  ]
}
```

## 核心原则

> **Segment ID 全流程保持一致。**

例如：

```text
03-02
```

后续同时用于：

```text
TTS Script
Audio Manifest
Subtitle Data
Remotion Timeline
```

---

# 十、第八步：edge-tts Audio

## 工具选择

当前确定使用：

> **edge-tts**

原因：

- 接入简单
- 可脚本化
- 不需要单独购买 TTS API
- 适合批量生成
- 可以获取语音边界信息
- 非常适合后续字幕同步

## 生成方式

不要整篇一次生成。

按 Scene / Narration Segment 生成。

例如：

```text
audio/
└── scene-06/
    ├── 06-01.mp3
    ├── 06-02.mp3
    ├── 06-03.mp3
    └── 06-04.mp3
```

## 为什么按 Segment 生成

好处：

- 单段不满意可以单独重生成
- 单段语速可以单独调整
- 更方便控制动画节奏
- 更方便生成字幕
- 更容易排查问题

---

# 十一、第九步：Audio Manifest

## 目的

TTS 完成以后，不只是输出一堆音频文件。

还要生成：

`audio-manifest.json`

## 示例

```json
{
  "scenes": [
    {
      "sceneId": "03",
      "segments": [
        {
          "id": "03-01",
          "file": "audio/scene-03/03-01.mp3",
          "text": "如果换成 Claude Code，同一个问题，工作方式会完全不一样。",
          "duration": 4.82
        }
      ],
      "narrationDuration": 4.82
    }
  ]
}
```

## 核心作用

Audio Manifest 告诉后续系统：

- 每段音频是什么
- 属于哪个 Scene
- 对应什么文本
- 实际时长是多少

## Scene 时长原则

Scene 不要提前人工写死。

应该：

```text
Segment 实际音频时长
+
场景必要缓冲
=
Scene 基础时长
```

也就是说：

> **真实语音时长决定 Scene 的时间基础。**

---

# 十二、第十步：Subtitle System

## 目标

字幕不直接来自文章。

字幕应该来自：

```text
TTS Script
↓
edge-tts
↓
音频 + WordBoundary
↓
Subtitle Cue
```

## 字幕层级

```text
Scene
  ↓
Narration Segment
  ↓
Subtitle Cue
```

例如：

```text
03-02
├── 03-02-a
├── 03-02-b
└── 03-02-c
```

## 为什么这样设计

一眼可以知道：

- 属于哪个 Scene
- 属于哪段音频
- 当前是哪一个字幕块

---

# 十三、字幕时间来源

不要根据文字长度猜时间。

优先使用 edge-tts 返回的真实边界信息。

流程：

```text
edge-tts
↓
WordBoundary
↓
结合语义切分
↓
字幕时间
```

## 字幕时间建议

字幕 Cue 主要控制在：

```text
约 1.2 ～ 4 秒
```

避免大量：

```text
0.4 秒
0.6 秒
0.8 秒
```

快速闪烁。

---

# 十四、中文字幕切分规则

字幕切分同时考虑：

```text
语义完整
+
阅读长度
+
真实语音停顿
```

推荐：

```text
单行约 10～16 个中文字符
最多两行
一个 Cue 约 15～26 个中文字符
```

但优先级是：

```text
语义完整
>
阅读舒适
>
字数限制
```

---

# 十五、Subtitle Manifest

建议首先生成：

`subtitle-manifest.json`

而不是直接只生成 SRT。

## 示例

```json
{
  "sceneId": "03",
  "segmentId": "03-02",
  "audioFile": "audio/scene-03/03-02.mp3",
  "cues": [
    {
      "id": "03-02-a",
      "text": "接下来，它可以自己去查看相关文件，",
      "start": 0.0,
      "end": 2.46
    },
    {
      "id": "03-02-b",
      "text": "搜索代码之间的调用关系，",
      "start": 2.46,
      "end": 4.38
    }
  ]
}
```

时间建议保存为：

> **相对于当前 Segment 的时间。**

后续 Remotion 再结合 Scene 和 Segment Offset 计算绝对时间。

---

# 十六、字幕与视觉重点文字必须分开

字幕负责：

> 观众听到什么。

Visual Script 中的重点文字负责：

> 这一幕希望观众记住什么。

例如：

```text
字幕：
人开始从管理每一步操作，转向管理最终目标。

视觉重点：
管理步骤
↓
管理目标
```

两套文字不要合并。

---

# 十七、字幕样式建议

字幕保持克制。

建议：

```text
位置：底部居中
最大宽度：画面 70%～75%
最多两行
半透明深色背景
浅色高对比文字
轻微圆角
淡入 / 淡出
```

避免：

- 卡拉 OK 式逐字跳色
- 大幅缩放
- 每个字弹跳
- 复杂描边
- 过强装饰

---

# 十八、音频与字幕输出目录

建议：

```text
projects/<video-id>/video-assets/
├── tts-script.json
│
├── audio/
│   ├── scene-01/
│   ├── scene-02/
│   └── ...
│
├── audio-manifest.json
│
├── subtitles/
│   ├── scene-01.json
│   ├── scene-02.json
│   └── ...
│
└── subtitle-manifest.json
```

可选再导出：

```text
captions.srt
captions.vtt
```



---
