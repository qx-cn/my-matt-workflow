---
name: my-edit-article
description: 按读者用途重组并润色文章，默认保留原稿
disable-model-invocation: true
---

# 编辑文章

先按[面向读者写作](references/shared/reader-first-writing.md)确认文章的目标读者、载体、用途、前置知识和作者希望读者采取的动作；这些信息会改变结构且无法推断时再询问。

1. 先按标题划分文章章节，梳理每章的核心论点与信息依赖，确保章节顺序尊重前置知识；把结构方案作为可审阅的新稿依据，不为普通、可逆的重排单独等待确认。若重排必须改变未经确认的立场、范围或事实含义，按[指令权威与决策 Gate](references/shared/instruction-authority.md)分类为 `consequential` 后执行唯一 gate 动作。
2. 逐节改写以改善清晰度、连贯性与节奏；段落长度服从载体和论证需要，不改变未经确认的事实立场。
3. 默认生成新稿，按[工作产物存储](references/shared/adapters/artifact-storage.md)保存到 `.agent/work/<topic>/articles/articles-<topic>-<time-or-sequence>.md`，并报告与原稿的关系。
4. 用户明确要求原地修改即构成该目标文件的授权，说明影响范围后直接执行，不重复确认。只有目标文件、编辑范围或事实立场发生实质变化，或 profile gate 明确要求时才暂停确认。

完成时简述结构变化、保留的原稿路径与仍需作者核实的事实或引文。
