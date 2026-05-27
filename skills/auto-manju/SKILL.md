# Auto Manju（自动化AI漫剧全流程）Skill

## 目标
输入：用户上传的小说文本（txt/md/docx抽取后文本）。  
输出：完成审核的成片视频（含分镜、画面、配音、配乐、剪辑、质检报告）。

该 skill 默认追求**高质量优先**，通过“生成-评估-修正”闭环提升人物一致性、剧情一致性和视听表现。

---

## 1. 能力范围
- 自动提炼小说核心爽点、节奏线、冲突线。
- 自动生成角色设定卡 + 形象提示词（可直接喂给图像/视频模型）。
- 自动改编为可拍摄剧本（幕-场-镜头级）。
- 自动生成高质量镜头语言（景别、机位、运动、时长、情绪、转场）。
- 自动调用模型 API：文案、图像、视频、TTS、音乐、剪辑。
- 自动审核：人物一致性、剧情一致性、视听质量、违禁风险。
- 自动迭代：失败镜头重绘/重配/重剪。
- 自动导出成片 + 全链路报告 + 可学习数据。

---

## 2. 目录结构
- `scripts/pipeline.py`：主流程编排器（含平台路由器与阶段调用决策）。
- `templates/prompts.yaml`：各阶段提示词模板。
- `templates/config.example.yaml`：API、模型、阈值、风格参数与阶段平台策略。

---

## 3. 快速开始
1) 准备配置：
```bash
cp skills/auto-manju/templates/config.example.yaml config.yaml
```
2) 填写各平台 API Key 环境变量（如 `OPENAI_API_KEY`、`RUNWAY_API_KEY`）。
3) 执行：
```bash
python3 skills/auto-manju/scripts/pipeline.py \
  --input novel.txt \
  --config config.yaml \
  --outdir outputs/run_001
```

---

## 4. 什么时候调用哪个平台（核心）
Skill 在每个阶段先读取 `stage_plan`，再通过 `platforms` 能力表进行匹配，输出 `00_routing_plan.json`，明确：
- primary（主平台）
- fallback（备用平台）
- capability（当前阶段所需能力）
- call_guide（API base/key、输入输出协议、重试策略）

### 阶段调用顺序与平台能力映射
1. `story_insight`：调用文本LLM（如 OpenAI）提炼爽点/冲突/节奏。  
2. `character_bible`：调用文本LLM生成人物设定和形象锚点。  
3. `script_generation`：调用文本LLM生成剧情与分镜脚本。  
4. `storyboard_generation`：调用视频/分镜平台生成镜头级计划。  
5. `video_generation`：调用视频平台逐镜生成（主平台失败自动切 fallback）。  
6. `tts_generation`：调用TTS平台按角色音色生成对白。  
7. `music_generation`：调用音乐平台按情绪与节奏生成BGM。  
8. `editing`：调用剪辑引擎完成拼接、字幕、混音。  
9. `qc`：调用审核引擎（规则+LLM）计算一致性与质量分。  

### 调用触发条件
- 仅在“前一阶段产物存在 + 安全审核通过 + 当前阶段阈值满足”时触发下一平台。
- 若阶段失败：优先同平台重试；超重试次数后切换 fallback。

---

## 5. 质量红线与审核机制
- 人物一致性 < `0.82`：打回重生镜头。
- 剧情一致性 < `0.85`：打回重写台词/镜头。
- 技术质量 < `0.80`：重编码或替换素材。
- 任一违禁审核不通过：直接中断并输出风险报告。

每轮最多迭代 `max_regen_rounds` 次，超过次数则保底降级策略：
- 保留最优版本 + 标记“人工复核建议位”。

---

## 6. 输出产物
在 `outdir` 生成：
- `00_routing_plan.json`（每阶段调用哪个平台、为何调用、失败切换策略）
- `01_story_insight.json`
- `02_character_bible.json`
- `03_script.json`
- `04_storyboard.json`
- `05_assets/`（图/视频/音频）
- `06_edit/final.mp4`
- `07_qc_report.json`
- `08_learning_log.json`

---

## 7. 提示
- 若追求“绝对高质量”，建议提高：分镜细度、角色锚点一致性约束、双路审核（规则+模型）。
- 首次运行推荐先做 30~60 秒短片试生产，再全片。
