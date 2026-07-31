# Humanizer 模式清单

## 动刀前先排除

下列内容即使像 AI 腔也**不要**当文风问题清理：

- 命令、CLI 标志、脚本入口、workflow 子命令
- 策略键与合法取值（如 `humanizer_policy: confirm`）
- Ticket / Spec 的 frontmatter、字段名、枚举、`blocked_by`、验收复选框原文
- 硬性「必须 / 不得」及同等约束句
- 代码块、标识符、API 名、错误码
- 链接目标、仓库相对路径、机器可读 ID
- `/my-*` 调用名与 Skill 内已约定的主导词
- 引号内被讨论的术语、专名、标题（讨论对象本身）

扫描可改区时找**成簇**痕迹。单一破折号、单一 however、完美语法本身都不是证据。

## 内容

1. **意义膨胀**：pivotal / testament / broader movement / setting the stage → 删掉「代表更大趋势」的空话，留事实。
2. **知名度堆砌**：罗列媒体与粉丝数却无语境 → 留有语境的一条，或删。
3. **-ing 假深度**：highlighting / ensuring / reflecting / showcasing 挂句尾 → 改成直接陈述。
4. **宣传腔**：vibrant / nestled / stunning / rich heritage → 中性具体说法。
5. **模糊归因**：experts argue / observers say（无来源）→ 删或点名真实来源；不捏造来源。
6. **挑战与展望套话**：Despite challenges… continues to thrive → 只写具体问题，删励志收尾。

## 用词与句法

7. **AI 高频词**：delve / pivotal / landscape / tapestry / underscore / foster / crucial / vibrant 等扎堆 → 换成平常词。
8. **回避是/有**：serves as / boasts / features → 用「是」「有」。
9. **否定排比**：not only… but… / it's not just… it's…；句尾「no guessing」碎片 → 写成正常从句。
10. **三件套强迫症**：创新、灵感、洞见 → 只留实际有的项。
11. **同义轮换**：protagonist / main character / hero 轮着叫 → 固定一个称呼。
12. **假范围**：from X to Y 而 X、Y 不在同一尺度 → 改枚举。
13. **无主语被动**：No config needed → 说出谁做什么。

## 版式

14. **破折号**：终稿可改区不含 `—` / `–` 或 ` -- `（写作样本常用时除外）。用句号、逗号、冒号或括号替代。
15. **机械加粗**：去掉装饰性 bold（契约里要求加粗的标记不动）。
16. **粗标题列表**：`- **性能：** …` → 改成连贯句子或普通列表。
17. **标题 Title Case**：英文标题改句式大小写；中文标题不大写堆砌。
18. **Emoji 装饰**：删掉标题与列表上的 emoji。
19. **弯引号**：`“”` → `""`（仅在与其他痕迹成簇时优先处理；编辑器自动弯引号可保留）。

## 腔调

20. **客服尾巴**：I hope this helps / let me know / 希望这对你有帮助 → 删。
21. **知识截止与脑补**：as of my training / maintains a low profile / likely grew up → 不知就写不知或删，不编。
22. **奉承**：Great question! You're absolutely right! → 删，直接说事。
23. **填充**：in order to / due to the fact that / it is important to note → 缩短。
24. **过度对冲**：could potentially possibly → 一次限定即可。
25. **空洞展望**：future looks bright / exciting times → 删；有具体计划才写计划。
26. **连字符形容词**：定语位置可保留 high-quality；谓语后改 high quality。
27. **伪深刻**：the real question is / at its core / what really matters → 直接说判断。
28. **预告式开场**：Let's dive in / here's what you need to know → 删，直接写内容。
29. **标题后热身句**：标题下第一句只是复述标题 → 删。
30. **diff 叙事**：this was added to replace… → 按事物现状描述（changelog 类文档除外）。
31. **短句鼓点**：连续碎句制造戏剧 → 收成正常节奏。
32. **箴言公式**：X is the Y of Z / X is not a tool but a mirror → 改回具体主张。
33. **假坦诚开场**：Honestly? / Look, / Here's the thing → 删，直接说。

## 勿误伤

不要只因「写得干净」「偏正式」「偶尔用 however」就大改。保留难编造的细节、未决态度、年代感梗、作者辩得清的用词选择，以及长短句交错。

博客、随笔、立场文可以保留观点、犹豫与旁白；技术与参考文保持平实即是人声。
