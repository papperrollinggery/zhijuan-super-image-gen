# zhijuan-super-image-gen 深度研究与 v2 可执行改造方案

这次仓库审阅和外部研究之后，我的核心判断很明确：你现在这套 skill 的主要问题，不是“提示词还不够长”，也不是“字段还不够全”，而是**把视觉导演这件事做成了模板填表**。这样会提升稳定性，却会同时损失 ChatGPT 生图里最值钱的东西：**对简短需求的语义展开、对世界与材质的隐式补全、对画面完成度的默认审美、以及对多轮上下文的连续建模**。OpenAI 官方已经公开说明，ChatGPT Images 2.0 的优势不只在底层图像模型本身，还在于更强的世界知识、指令遵循、细节生成，以及“thinking mode”把简单 prompt 变成“经过研究与思考的最终图像”的过程；而 OpenAI 的 hosted image generation tool 也会自动优化文本输入，并暴露 `revised_prompt`。这正是“同一句话，ChatGPT 常常比裸 image_gen / API 更会出图”的工程性原因。citeturn25view0turn22view0turn28view1

## 外部研究结论和来源

OpenAI 官方对 GPT Image 系列的定位非常接近“生产级视觉工作流引擎”，而不是单纯的 text-to-image 玩具。官方 prompting guide 把它定义为适合专业视觉任务、迭代式内容生产、可控编辑与高保真输出的模型；同一份 guide 还明确把“高保真写实、自然光照、准确材质、文本渲染、身份保持、可控编辑”列为关键能力。citeturn21view0turn24view2

ChatGPT Images 2.0 的官方 system card 进一步解释了为什么 ChatGPT 端看起来更“聪明”：它强调了**显著增强的世界知识、指令遵循、复杂细节与密集文字生成能力**，并且说新的 thinking mode 会把 live web search、推理栈和工具使用接到图像生成过程中，把一个基础 prompt 变成“更充分研究、想清楚之后的最终图像”。这不是“prompt 写得更花”，而是**生成前就做了更强的任务建模**。citeturn25view0turn25view6

OpenAI 还公开写明，Responses API 里的 image generation tool 会**自动优化文本输入**，而且主模型会为图像生成生成一个 `revised_prompt`。这意味着如果你的 Codex skill 只是把用户句子原样转成 image_gen prompt，你实际上是在和一个会“自动改写 prompt”的系统竞争。社区里关于“ChatGPT web 结果比 API 更锐、更会用参考图、更会排字”的讨论，基本也都围绕这个“隐藏 scaffolding / hidden system prompt / prompt tweaking”展开；这些讨论不是官方结论，但和官方文档揭示的 tool-side prompt revision 是一致的。citeturn22view0turn40view0turn40view1turn40view2

ChatGPT 生图相比普通 image_gen prompt 的真正优势，可以拆成六层。第一层是**语言理解**：ChatGPT 本身就是对话模型，能从简短自然语言里抽出目标、用途、风格、限制与省略条件；官方 Academy 甚至明确说，好 prompt 往往不需要很长，通常 1–3 句清楚的话就够，关键是说明图片做什么、主体是什么、发生什么、场景在哪里、风格如何，以及必要的 framing / lighting / constraints。第二层是**隐式视觉补全**：system card 直接说它会把 basic prompt 变成“well-researched and thought-through final image”，这就是把用户没说全的空间关系、材质行为、画面秩序补进去。第三层是**世界知识与上下文**：官方博客说明 4o / ChatGPT image gen 会利用 inherent knowledge base、chat context 和上传图像进行 in-context learning。第四层是**审美默认值**：ChatGPT Images 2.0 官方展示样张覆盖电影感人像、杂志书页、旅行 brochure、学术海报、漫画分页、现代主义海报、多语种排版、信息图等，说明它不是单一“会出图”，而是有较强的默认 art direction 先验。第五层是**多轮编辑与一致性**：OpenAI 明写 multi-turn generation / editing 能沿着 chat context 维护一致性。第六层是**对短需求的自动扩写方式**：官方建议短句、明确、可维护的 skimmable template，而 hosted tool 又能自动 revise prompt；这使 ChatGPT 的短输入体验天然优于“用户自己写完所有字段”。citeturn29view0turn29view1turn25view0turn28view1turn28view4turn28view5turn21view4

OpenAI 自己对 prompt 形式的建议，其实已经给了你答案：复杂任务建议按**scene / subject / key details / constraints** 的稳定顺序写；可以用短标签和换行；“极简 prompt、描述段落、JSON-like 结构、instruction-style prompt、tag-based prompt”都能工作，但生产环境应优先追求**易维护、易浏览、意图清晰**，而不是花哨的语法。同时，OpenAI Academy 又强调“清晰比 clever phrasing 更重要”，尤其是灯光、材质、纹理、版式这种容易被写虚的东西。citeturn27view3turn27view4turn29view0

GitHub 上比较成熟、值得借鉴的，不是“再造一个更长的 prompt”，而是三类基础设施。第一类是**受控但可关闭的 prompt expansion**：Fooocus 的更新日志里长期在调 prompt expansion 的权重、位置和副作用，甚至专门加入 raw mode 用于关闭 expansion；它还明确提到要降低 semantic corruption，这和你现在遇到的“越补越像模板，不像真实画面”高度同构。第二类是**风格/镜头/灯光/材质的可视化库**：PromptForge 把样式、镜头、灯光、材质、主题拆成独立 JSON 页面，并配可视化预览，而不是把它们全部连成一个固定海报模板。第三类是**结果与元数据沉淀**：Image Prompt Library 的重点不是再写一层 prompt，而是把成功图像、原 prompt、来源和 metadata 都存成本地可检索知识库。citeturn32view0turn34view2turn35search0

开源图像工作流社区对“参考图如何处理”的经验也很一致：ComfyUI 相关 workflow 文档把 image conditioning、text conditioning、style model、reference closeness、multiple reference images 明确拆开，并把强度做成单独可调的控制项。这说明你的 skill 不应该把“参考一致性、风格、构图、主体、文字限制”一股脑塞进一个最终 prompt，而应该先在前置 planning 阶段拆维度。citeturn33view0

Reddit 和社区反馈也和这个判断一致。关于 ChatGPT web 与 API，同一句 prompt 结果差异很大的帖里，用户最常见的观察就是“web 版文字更准、参考图更稳、结果更像被额外指挥过”；而在 Stable Diffusion / Midjourney / Fooocus 社区里，又经常能看到“过长 prompt 会让模型变笨”“太多 style/negative 会吃掉画面活力”“巨大 negative prompt 会破坏风格细节”的经验反馈。它们不是可直接外推到 OpenAI 图像模型的定律，但足以说明：**结构化并不天然等于更好，尤其是当结构化变成模板化和过度约束时**。citeturn40view0turn40view1turn32view2turn39search13turn39search10turn38search17

最后，和你目标最可迁移的并不是“prompt engineering 博客套路”，而是商业视觉的基础规则：产品摄影里，柔和的大面积漫射主光、稳定的轮廓边缘、可感知的接触阴影与可解释的反射，是“高级质感”的底层；平面设计里，visual hierarchy 与 negative space 决定了主体是否立得住；SaaS hero / hero shot 的目标是**即时解释产品价值与视觉主语**，而不是做一张看似昂贵、实则没有信息焦点的炫技图。citeturn41search0turn41search2turn41search3turn41search12turn41search4turn41search16

## 当前仓库诊断

仓库里最正确的方向，是主会话与图像子流程的分离。`AGENTS.md` 明确要求主 Codex 会话做干净 orchestrator，把图像需求委托给 `subagents/image_director.md`，子流程负责 feasibility、抽取视觉上下文、生成结构化 brief、负面约束、Codex draft prompt、ChatGPT handoff prompt，并且不要把长 prompt 直接污染主会话。这条思路本身是对的，我建议保留。问题不在“要不要子智能体”，而在**子智能体内部的导演逻辑还太像表单编译器**。citeturn43view4

真正的 load-bearing runtime 逻辑目前集中在 `scripts/imageops_core.py`。我在代码里直接看到了内联的 `TASTE_PRESETS`、trigger scoring、preset 选择与 `craft_expansion` 返回值；同时我没有在可见代码片段里看到一个把 `references/presets/*` 作为运行时唯一来源的 loader。也就是说，当前运行时的“味道”主要由 `imageops_core.py` 里的硬编码 preset 与 trigger 分数决定，而不是一个易维护、可替换的外部方向系统。citeturn15view0turn16view1turn14view1

这也是为什么你的“Codex 介绍电商海报”很容易被拉向一种固定画面。`premium_saas_poster` preset 的触发词里同时包含 `codex`、`ai agent`、`电商`、`海报`、`软件`、`工具` 等关键词；而一旦命中，它的 visual thesis、composition、lighting、materials 和 craft 会把图像拉向“抽象 AI 指挥中心作为英雄物体、黑色缎面底座、三枚 floating feature chips、底部 trust strip、熏黑玻璃、阳极氧化铝、OLED glow”的高端 SaaS 海报模板。这个 preset 本身并不差，但它实际上在**替用户决定画面隐喻**，而不是帮用户把“AI coding agent”做得更有生命力。citeturn15view0turn16view1turn16view2

另一个大问题是输入理解太粗。`infer_subject` 的默认策略几乎等于“把整个用户任务字符串直接塞给 subject”；`infer_lighting`、`infer_style`、`infer_composition`、`infer_camera` 又是比较粗的关键词分支，所以最后生成出来的 `subject` 往往是“原始需求 + 抽象修饰词”的混合体，而不是清晰的视觉主语。这样 renderer 再把它写成 `Subject:`、`Composition:`、`Light and texture:` 等字段时，看上去更整齐，实际上对模型来说更像“半自然语言、半 schema 的压缩记录”，不够像一个真正的导演 brief。citeturn11view7turn16view4turn16view5

防御逻辑也偏重。`build_negative` 会按 person / product / UI / scene / fake claims 词表拼出一串通用 negative；更关键的是，`IDENTITY_TERMS` 里把 `product` 也算进去了，所以很多商业图、产品图即使没有参考图，也会被判成“需要 preservation / identity-style lock”的任务；`use_chatgpt_images_for_final` 又会在 `identity_needed` 为真或 task 很长时转向 ChatGPT final。结果就是：**你还没开始做导演，系统就先把任务定义成一个需要强 preservation、强避险、强 handoff 的工程题**。citeturn18view0turn12view5turn12view6turn17view1turn13view3

最后是 prompt render 形式本身。`make_codex_prompt` 现在输出的是一串字段：`Subject / Visual direction / Aspect ratio / Composition / Light and texture / Camera / Positive constraints / Text handling / Preserve / Avoid`，然后再走 `compress_prompt` 去重与限长。这个做法有两个副作用：第一，它把画面的主次顺序抹平了，因为所有字段看起来都像同级要求；第二，`compress_prompt` 是按逗号和分号做 phrase 去重，再按词数裁掉尾巴，它适合去重，不适合保留“导演语义的节奏”。与此同时，`make_chatgpt_prompt` 又把 handoff prompt 扩到 700 词上限，等于另一端又可能过长。于是你两头都中招：Codex prompt 太 schema，ChatGPT handoff 又容易太 verbose。citeturn11view1turn17view0turn13view1turn13view2

## 要保留的部分

第一，**主会话不污染、子会话做图像导演** 这个架构要保留，而且应该强化。现在 `AGENTS.md` 已经要求主会话只接收状态、路径和建议，不要把长 prompt body 回灌到主上下文，这跟你想要的“子子子智能体做图，但不把主会话搞脏”是同方向的。citeturn43view4

第二，**feasibility analysis** 和 **human checklist** 要保留，但要更聚焦。当前代码里已经把图像是否有用、目标是否具体、是否需要 references、是否有 fake claims 风险、是否有 layout precision 风险等拆出来，同时 human checklist 也覆盖了主体是否清晰、是否有触感、光向是否一致、文字是否可读、是否避免了虚构数字等。这些都很有价值，只是要从“默认防御”改成“关键风险提示”。citeturn12view5turn12view6turn16view3

第三，**Codex draft prompt 与 ChatGPT handoff prompt 双产物** 也值得保留，但它们应该都从同一个 visual plan 生成，而且 ChatGPT handoff 必须是**可选 artifact**，不是系统默认站队“Codex 只能打草稿、ChatGPT 才能出最终图”。当前 `AGENTS.md` 的“quality matters 就 handoff ChatGPT Images 2.0”表述太绝对，需要降级成 optional。citeturn43view4

## 要删除或弱化的部分

最该删的是**preset 直接决定场景隐喻**。像 `premium_saas_poster` 这种 preset 不应再直接输出“黑色缎面底座 + floating chips + trust strip + 抽象 AI command center”。你可以保留“商业科技 still life”“冷色高端 tech palette”“克制的 studio light”这类方向偏置，但不要让 preset 直接生成主角是什么、配件怎么飘、版式怎么摆。否则所有海报最后都会像“同一个模板换一个 noun”。citeturn15view0

第二个要删的是 `Subject = 原始任务全文` 这条 fallback。它会把“用途、风格修饰词、禁止项、商业排版要求”一起塞进主语，导致 renderer 里主语不再是视觉对象，而是一个混合意图串。v2 里必须先抽出 immutable core：视觉主语、用途、比例、硬限制、文字需求、事实风险。citeturn11view7

第三个要大幅弱化的是**通用 negative prompt 清单**。OpenAI 官方给 ChatGPT 的图像建议不是“堆大量 negative”，而是“把必须固定的限制说清楚”；社区也长期反馈，巨大 negative prompt 常常会伤风格、伤细节，或者根本不像用户想的那样工作。你这套 skill 现有的 negative builder 更像 Stable Diffusion 时代的保险丝，不像 GPT-Image 时代的导演约束。v2 应该把 negative 改成 `hard_constraints`，数量严格控制在 1–4 条。citeturn29view0turn39search13turn39search10turn38search17

第四个要弱化的是**统一压缩器对最终 prompt 的破坏**。`compress_prompt` 适合做去重，但不应用来砍掉最终导演 brief 的句法层级。v2 应该允许一个短而完整、句法自然、层次清楚的 prompt 存在，而不是先写成表格再把它剪碎。citeturn17view0

第五个要改的是**默认 ChatGPT final bias**。你用户目标已经很清楚：不是假装底层模型等于 ChatGPT Images，也不是默认把最终结果外包给 ChatGPT，而是把 Codex 里的 image director 做到更像 ChatGPT 的“导演层”。所以 `AGENTS.md` 里那条“质量重要就 handoff ChatGPT Images 2.0”必须从默认策略移除，只保留“可按需导出 handoff prompt”。citeturn43view4

## v2 架构与 prompt rendering 规则

v2 的设计目标应该非常克制：**一句话输入，默认只出一张图，不做自动审美代替人，不伪装成 ChatGPT Images 2.0，但尽可能把 Codex image_gen 喂到更像一个被导演过的状态**。这意味着你不需要“更长 prompt”，你需要的是一个前置 visual planning 层。这个判断既符合 OpenAI 官方对 skimmable prompt / short clear prompts 的建议，也符合 Fooocus 那种“持续压低 expansion 侵入性”的经验。citeturn27view3turn27view4turn29view0turn32view0

我建议 v2 用下面这个单通道流程：

1. **Intent understanding**  
   把用户输入解析成一个 `TaskCard`，只保留不可丢的东西：`deliverable`、`use_case`、`hero_subject`、`aspect_ratio`、`must_have`、`must_not_have`、`text_requirement`、`factual_risk`、`reference_mode`。  
   这里不生成任何画面辞藻，不补世界观，只做抽取。

2. **Visual concept generation**  
   在内部静默生成 2–3 个候选概念，但只选 1 个，不默认多图。候选概念不是 prompt，而是“画面解决方案”，例如：  
   - 产品式科技 still life  
   - 现场工作中的 agent 场景  
   - UI + 物理载体的 hybrid poster  
   选择标准只看：主体明确性、商业相关性、空间可信度、缩略图可读性、文字风险。

3. **Art direction selection**  
   这里不再选 `premium_saas_poster` 这种整包模板，而是选一个**方向卡**：  
   - `commercial_tech_still_life`  
   - `editorial_workplace_realism`  
   - `ui_object_hybrid`  
   - `graphic_poster_minimal`  
   每张方向卡只包含 tone、palette family、light family、material family、composition family，不包含具体 hero object。

4. **Scene construction**  
   用一个“非破坏性扩写预算”去补空间。我的建议是：**最多新增 3 个用户没说但画面必须有的承诺**。比如“桌面”“设备屏幕发光”“薄雾空气层”可以；“黑色缎面底座”“三枚 feature chips”“底部 trust strip”这种强模板物件不可以，除非用户真的要。  
   这一步的目标是“让画面可被拍摄”，不是“让 prompt 看起来高级”。

5. **Material and lighting enrichment**  
   不要写“高级感、质感强、细节丰富”这种抽象词，要把它翻成可观察现象：  
   - 主光方向  
   - 边缘轮廓光  
   - 接触阴影  
   - 玻璃/金属/磨砂塑料/织物的反射和粗糙度  
   - 灰尘、指纹、磨损、微划痕是否需要  
   这类写法更符合 OpenAI 官方“clarity over cleverness”的建议，也更符合商业产品摄影的基本语言。citeturn29view0turn41search0turn41search2

6. **Composition intelligence**  
   这一层只回答三个问题：  
   - 观众第一眼看哪里  
   - 文案如果需要，放哪块负空间  
   - 怎么保证 4:5 缩略图下仍然成立  
   Visual hierarchy 和 negative space 是必须引入的规则；它们不需要被写成“排版学论文”，但需要体现在 prompt 的构图句子里。citeturn41search3turn41search12turn41search9

7. **Risk guard**  
   把现在的“negative laundry list”改成 `hard_constraints`，上限 4 条。  
   在你的业务场景里，多半就是：  
   - no official logo  
   - no fabricated numbers / ratings / prices  
   - text only if large and legible  
   - no unrelated extra props  
   这和 OpenAI 官方“明确说什么必须固定”是一致的。citeturn29view0

8. **Final prompt rendering**  
   最终给 image_gen 的不是字段表，也不是 700 词大 essay，而是**混合式导演 brief**：  
   - 一句目标  
   - 一句 scene + subject  
   - 一句 composition  
   - 一句 lighting + materials  
   - 一句 text/constraints  
   总字数建议控制在一个短段落或 5 行短句内。

9. **Human review checklist**  
   不做 AI 审美仲裁，只保留人工 rubric。Rubric 可以直接借 OpenAI 图像 eval 的四大维度：  
   - instruction following  
   - text rendering  
   - style control  
   - preference alignment  
   但执行者仍然是人。citeturn21view7

10. **Optional ChatGPT final handoff prompt**  
    基于同一个 visual plan，额外导出一个更像 ChatGPT 对话风格的短 handoff prompt。它是“导出能力”，不是默认执行路径。这样你既保留了 Codex image_gen 的原生创造力，也保留了真正需要 handoff 时的兼容性。citeturn29view0turn25view0

关于**最终传给 image_gen 的 prompt 形式**，我的结论是：

- **字段式 prompt**  
  适合内部中间态和 metadata，不适合作为最终 prompt。它方便调试，但天然容易失去语义节奏，尤其会让模型把每项都当同级 checklist。

- **长 checklist prompt**  
  适合精修编辑和“只改 X，别动其余”的场景；不适合你这种“一句话输入，默认只出一张”的首帧生成。OpenAI 官方自己也更强调小步迭代和明确约束，而不是永远靠长清单解决。citeturn24view1turn27view5turn27view6

- **一段自然语言导演 brief**  
  更有画面感，也更容易触发模型的自然美学补全；但如果完全不带约束，容易丢掉商业任务里最关键的事实边界。

- **混合式 prompt**  
  最适合 Codex image_gen。官方已经说了任何格式都可以，只要 intent clear 且 skimmable；而你当前的问题恰恰是 schema 太重、语言太弱。因此 v2 应该用“自然语言导演 brief + 少量硬约束”的混合式。citeturn27view3turn27view4turn29view0

我建议 renderer 最终输出形态固定成这样：

```text
Create a [deliverable] for [use case].
Show [hero subject] in [scene], with [one concrete action or state].
Compose it so that [focal order / crop / negative space].
Use [light behavior] and [material behavior] to make the image feel tactile and spatially believable.
If any text appears, [text rule]. Do not [1-4 hard constraints].
```

这个模板的关键不是“格式”，而是**每一句都描述肉眼能看到的东西**。把“高级”“质感强”“商业完成度高”这一类评价词，全部翻译成光、材质、空间、构图、文字规范。citeturn29view0turn29view3

## 具体文件级修改方案

下面这套改法，是能直接指导你改 skill 的。

**先改 `AGENTS.md` 和 `SKILL.md`**  
把“Codex 负责草稿，ChatGPT Images 2.0 负责最终高质量图”这种默认策略改掉，替换成：  
- default = Codex image_gen  
- optional = export ChatGPT handoff  
- main session 只拿 status / paths / brief summary  
- 子会话只接收最小必要上下文  
这一改动是为了和你真正目标保持一致，而不是把 skill 做成“自动转单器”。现有 `AGENTS.md` 已经有干净 orchestrator 的壳子，保留壳，换里面的导演策略。citeturn43view4

**重写 `scripts/imageops_core.py` 的核心逻辑**  
这是最大改动点。建议在这个文件里做四件事：  
1. 删除或弱化内联 `TASTE_PRESETS` 的“场景模板字段”，只保留 direction hints。  
2. 用 `parse_task_card()` 取代 `infer_subject()` 这类粗回退。  
3. 用 `build_visual_plan()` 取代 `craft_expansion()`。  
4. 用 `render_codex_prompt_v2()` 取代 `make_codex_prompt()`。  
当前代码里真正把你拖向模板海报的，就是 preset + trigger + field renderer 这条链路。citeturn15view0turn16view1turn11view1

一个可行的内部数据结构可以是这样：

```python
@dataclass
class TaskCard:
    use_case: str
    deliverable: str
    hero_subject: str
    aspect_ratio: str | None
    wants_text: bool
    hard_constraints: list[str]
    factual_risk: list[str]
    references: list[str]

@dataclass
class VisualPlan:
    direction_family: str
    concept: str
    scene: str
    composition: str
    lighting: str
    materials: str
    text_rule: str
    hard_constraints: list[str]
```

**新增一个短导演 renderer，而不是继续修 `compress_prompt`**  
不要再把最终 prompt 当“字段拼接后再裁剪”。直接新增 `render_prompt_v2.py`，内部生成 4–6 行短句，默认不超过 160–220 英文词。`compress_prompt.py` 可以保留给日志与 fallback，但不要再作为最终 prompt 的必经路径。官方 Academy 已经明确说多数情况下 1–3 句清晰描述就够；Cookbook 则建议复杂任务用 short labeled segments 和固定顺序，而不是靠长文堆满。citeturn29view0turn27view3turn27view4

**把 `build_negative.py` 改成 `build_constraints.py`**  
旧逻辑要从“模型不许犯所有常见错误”改成“只拦住本任务最不能犯的错”。  
规则建议：  
- 默认最多 4 条  
- 只有用户明确说过的禁止项，或商业场景的关键合规项，才能进最终 prompt  
- UI/人物/产品通用 defects 不再默认进 prompt，只进 human checklist  
这样既减少模板味，也保住原生创造力。社区里对 giant negative prompt 的副作用抱怨很多，而 OpenAI 官方也更鼓励直接清楚地写 must / must not。citeturn39search13turn39search10turn29view0

**把 preset 从“模板包”改成“方向卡”**  
建议把 `references/presets/*` 重构为 YAML 或 JSON，小而短，只包含：  
- tone  
- palette_family  
- light_family  
- material_family  
- composition_family  
- text_policy  
不要再有 `hero object = X`、`bottom trust strip = Y` 这类会强制模板化的字段。PromptForge 把 camera、lights、materials、styles、themes 分开管理，这个思路更接近你要做的 image director，而不是 single-template poster factory。citeturn34view2

**新增结果元数据与案例库**  
你现在最缺的不是更多 prompt，而是**成功案例沉淀机制**。参考 Image Prompt Library 的思路，在 `imageops/runs/<run_id>/` 下至少保存：  
- `request.json`  
- `task_card.json`  
- `visual_plan.json`  
- `prompt.codex.txt`  
- `prompt.chatgpt.txt`  
- `result.json`  
- `review.md`  
- `thumb.png`  
这样你后面才能做“什么类型的输入 + 什么 visual plan + 什么 prompt 形式，成功率最高”的经验库。citeturn35search0

**新增低成本 A/B，但不要默认多图**  
A/B 不是对每个用户请求都默认两张图，而是做一个**离线 canary benchmark**：  
- 准备 12 个固定场景任务  
- 每个任务只跑 A 和 B 各 1 张  
- 固定质量参数  
- 由人做 pairwise ranking  
- 记录 instruction following / text rendering / style control / preference alignment 四个维度  
OpenAI 的图像 eval cookbook 已经把这四类指标和 pairwise comparison 讲得很清楚，完全可以借来做人评体系。citeturn21view7

**新增可选的 ChatGPT handoff prompt 生成器**  
保留 `export_chatgpt_prompt.py`，但功能从“把一个更长的 prompt 导出出去”改成“把 VisualPlan 压成 ChatGPT 风格的 1–3 句短 handoff”。  
目的不是让 Codex path 看起来像 ChatGPT，而是在你真要 handoff 时，尽量贴近 OpenAI 官方建议的 plain-language、short clear prompt。citeturn29view0

## 示例新版 prompt

以下例子，用你的输入直接做对照：

> 生成一张 Codex 的介绍电商海报，突出 AI coding agent，光影高级，质感强，细节丰富，适合 4:5 电商主图。不要官方 logo，不要虚构数字。

**按当前版本代码路径，大概率会被渲染成的问题 prompt**  
这不是我随便编的，而是按当前 `premium_saas_poster` preset、`make_codex_prompt()` 与 `build_negative()` 的逻辑做的近似还原。因为 `codex / ai agent / 电商 / 海报` 会强命中 `premium_saas_poster`，而这个 preset 会默认引入“抽象 AI command center、黑色缎面底座、feature chips、trust strip、熏黑玻璃与阳极氧化铝”等一整套海报模板语言。citeturn15view0turn16view1turn11view1turn18view1

```text
Subject: 生成一张 Codex 的介绍电商海报，突出 AI coding agent，光影高级，质感强，细节丰富，适合 4:5 电商主图。不要官方 logo，不要虚构数字。
Visual direction: premium SaaS commerce poster staged like a high-end product photograph: abstract AI command center as the hero object, restrained dark interface surfaces, precise developer-tool credibility
Aspect ratio: 4:5
Composition: vertical 4:5 poster, large headline zone, centered 3D command-center hero on a black satin pedestal, three short floating feature chips, clean bottom trust strip, generous negative space
Light and texture: large softbox key light, cool rim highlights, subtle volumetric screen glow, controlled glass reflections, realistic contact shadows; smoked glass panels, anodized aluminum bevels, frosted acrylic cards, OLED screen glow, satin black pedestal, micro-scratches, fine dust
Camera: natural eye-level framing
Positive constraints: clean readable typography, stable commercial layout, premium developer-tool visual language, photorealistic product staging, short factual copy
Text handling: short readable title and 3-4 short feature labels only; no fabricated metrics, ratings, prices, certifications, awards, or user counts
Avoid: official logo recreation, invented numbers, tiny unreadable text, cluttered dashboard, flat vector look, unreadable text, broken layout
```

这个 prompt 的问题不在细节少，而在于**过早决定了隐喻**。它把“Codex 的介绍电商海报”直接翻译成“一个摆在底座上的抽象 AI 指挥中心”，于是图像虽然整洁、统一、稳定，但很可能没有真实工作状态、没有可信空间、没有真正“AI coding agent 正在工作”的瞬间感。它更像标准 SaaS KV，而不是 ChatGPT 那种“有完整场景想象、光影层次与世界细节”的图。这个副作用和你观察到的现象完全一致。citeturn15view0turn32view0turn32view2

**新版更好的 Codex image_gen prompt**  
我建议 internal renderer 最终给 Codex 的就是这种短导演 brief。它不是超长 prompt，也没有堆满负面词，但每句话都在说肉眼能看到的东西：

```text
Create a premium 4:5 e-commerce hero poster introducing Codex as an AI coding agent. 
Show a believable high-end developer workspace at the moment of active problem solving: a luminous coding interface on screen, terminal output, structured code panels, and subtle signs of reasoning and iteration, with the AI agent feeling present through the workflow rather than as a generic sci-fi object.
Compose the image around one dominant focal subject with strong foreground-background separation and a clean zone for a short headline if needed. Keep the frame elegant, product-like, and immediately readable at thumbnail size.
Use soft directional studio light with a controlled cool edge rim, realistic screen glow, crisp contact shadows, and tactile materials such as brushed aluminum, smoked glass, matte surfaces, fine dust, and slight wear so the scene feels expensive and physically grounded, not like a flat SaaS template.
If any text appears, keep it very short, large, and fully legible, using generic wording only. Do not use any official logo, and do not invent numbers, ratings, prices, or user counts.
```

这版更可能接近 ChatGPT 质感，原因有四个。第一，它把“AI coding agent”落实成了**正在发生的工作状态**，不是抽象奖杯。第二，它把“高级、质感强、细节丰富”翻译成了**光、材质、阴影、磨损、屏幕发光**这些可观察现象，而不是堆形容词。第三，它只保留了对商业图真正关键的硬约束：logo、虚构数字、文字长度。第四，它给模型留了空间去完成自己的世界构建，而不是强迫它复刻某个 SaaS 海报模板。OpenAI 官方对清晰、短句、可维护 prompt 的建议，以及 ChatGPT web / hosted tool 的 prompt revision 机制，都支持这种写法。citeturn29view0turn27view3turn27view4turn22view0

如果你还想保留“ChatGPT final handoff prompt”，那 handoff 版也不要再写成 700 词 essay。它应该只是同一个意思、更口语化一点的版本：

```text
Make a polished 4:5 e-commerce poster that introduces Codex as a premium AI coding agent. The image should feel like a real, expensive technology campaign shot inside a believable developer workspace, with active code, terminal reasoning, subtle interface depth, tactile materials, and refined cinematic lighting. Keep the composition clean and elegant, avoid official branding, and never add fake numbers or badge-style claims.
```

## 风险与优先级实施计划

先说风险。第一，**文字仍然是高风险点**。OpenAI 官方虽然强调了文字渲染能力的提升，但也明确提醒：精确文字位置、长期一致性、跨多次生成的品牌元素保持，仍然可能出现波动。所以你的商业海报里如果要放字，必须坚持“短、少、大、位置明确”的原则。citeturn23view0turn29view0

第二，**独立单张生成下的角色/品牌一致性仍有上限**。官方文档把 character consistency 和 multi-turn 工作流当成强项，但同样承认 recurring characters / brand elements across multiple generations 仍可能偶发不稳。所以 v2 应该优先把“首张图完成度”做好，而不是幻想靠单 prompt 把所有系列一致性问题一次性解决。citeturn24view2turn23view0turn28view5

第三，**API / Codex 与 ChatGPT 的心智差会继续存在**。只要 ChatGPT 端继续拥有 reasoning stack、chat context、tool use、prompt revision、thinking mode，而你的 Codex skill 只是一个薄编译层，就不可能完全复制 ChatGPT 的体验。v2 的目标应该是“更接近 ChatGPT 的导演层”，不是“伪装成同一个产品”。citeturn25view0turn22view0turn40view0turn40view1

优先级上，我建议这样落地：

**第一优先级**  
在一周内完成以下改动：  
- 去掉 preset 的具体场景模板字段  
- 去掉 `Subject = raw task`  
- 把 negative 改成 hard constraints  
- 新增 `render_codex_prompt_v2()`  
- 把默认 handoff ChatGPT 从策略里降为 optional export  
这一步会最快改善“更规整但更没生命力”的主问题。它几乎不依赖新基础设施，只改导演逻辑。这个方向也最符合官方的 skimmable prompt、清晰胜于巧技、少量迭代修正的建议。citeturn27view3turn27view4turn29view0turn32view0

**第二优先级**  
在两周内补齐：  
- VisualPlan 数据结构  
- direction cards  
- run metadata  
- 人工评分 rubric  
- 12 条 canary benchmark  
这一步会让你从“靠感觉调 prompt”升级成“有可验证的导演系统”。OpenAI 的 image eval 维度可以直接拿来做人评维表。citeturn21view7turn35search0

**第三优先级**  
在后续版本中做：  
- 引用图一致性模块  
- 多 reference 的 style / composition / identity 拆维度输入  
- ChatGPT handoff prompt exporter  
- 成功案例检索与推荐  
这里可以借鉴 ComfyUI 的多参考 conditioning 思路，以及 PromptForge / Image Prompt Library 这种“把 prompt 资产化”的做法。citeturn33view0turn34view2turn35search0

最终一句话总结这个 v2：**不要再把 skill 做成“把用户一句话拆成十个字段”，而要把它做成“先想好这张图为什么成立，再用短导演 brief 交给 Codex image_gen”**。这才是最接近 ChatGPT 生图体验、同时又不牺牲 Codex 原生创造力的工程路径。citeturn25view0turn22view0turn27view4turn29view0