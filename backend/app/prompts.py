"""
Prompt templates and construction utilities for novel generation.
Implements the 3-layer knowledge injection strategy.
"""

import json
from dataclasses import dataclass, field

# ─── Prompt Templates ───────────────────────────────────

OUTLINE_SYSTEM = """你是一位资深网文大纲策划师。根据用户的设定，生成完整的小说大纲。"""

OUTLINE_USER = """请为以下小说生成完整大纲：

小说名：《{title}》
类型：{genre}
目标平台：{platform}
目标字数：约{word_count}万字

{world_setting}

请生成：
1. 故事主线概要（200字内）
2. 主要人物设定（每人100字内）
3. 分卷/分段落结构
4. 每章简要章纲（标题 + 50字概要）

输出格式要求：
- 使用纯文本
- 章节格式：第X章 章标题：概要内容
- 人物格式：【人物名】：设定描述"""

OPENING_SYSTEM = """你是一位经验丰富的网文作家。请根据大纲和设定创作高质量的小说章节。
要求：
1. 文笔流畅，代入感强
2. 人物形象鲜明
3. 场景描写生动
4. 章末设置悬念或转折"""

CHAPTER_GENERATION = """你正在创作一部{genre}小说《{title}》。

=== 本章信息 ===
章节：第{chapter_no}章 {chapter_title}
章纲：{chapter_outline}

=== 前文摘要 ===
{previous_summary}

=== 关键人物状态 ===
{core_characters}

=== 相关上下文 ===
{related_context}

{background_section}

=== 写作要求 ===
1. 保持人物性格和说话风格一致
2. 人物等级、物品归属必须与上文一致
3. 功法威力符合设定，不可随意更改
4. 情节推进符合章纲
5. 字数约{word_count}字
6. 章末设置悬念

请生成本章内容："""

SUMMARY_SYSTEM = "你是一位小说内容分析师。请用简洁的语言概括章节核心内容。"

SUMMARY_USER = """请概括以下章节的核心内容（150字以内）：

小说：《{title}》
第{chapter_no}章 {chapter_title}

内容：
{content}

要求：
1. 包含本章关键情节
2. 提到出场的重要人物
3. 标注重要的状态变化（等级提升、物品获得等）
4. 不超过150字"""

KNOWLEDGE_EXTRACT_SYSTEM = "你是一位小说知识库管理员。分析章节内容，提取知识变更。"

KNOWLEDGE_EXTRACT_USER = """分析以下章节，提取所有知识变更：

小说：《{title}》
第{chapter_no}章 {chapter_title}

当前知识库摘要：
{current_knowledge}

章节内容：
{content}

请以 JSON 格式输出变更列表，每项包含：
- entity_type: character/item/skill/faction/location
- name: 实体名称
- field: 变化的属性
- old_value: 旧值（如果已知）
- new_value: 新值
- reason: 变更原因

仅输出 JSON 数组，不要其他文字：
[{{"entity_type": "...", "name": "...", "field": "...", "old_value": "...", "new_value": "...", "reason": "..."}}]"""

CONSISTENCY_CHECK_SYSTEM = "你是一位小说一致性审查员。检查章节中是否有与已知设定矛盾的内容。"

CONSISTENCY_CHECK_USER = """检查以下章节是否有一致性问题：

小说：《{title}》
第{chapter_no}章

已知设定：
{known_facts}

章节内容：
{content}

如果发现矛盾，以 JSON 数组输出：
[{{"issue": "问题描述", "severity": "high/medium/low", "location": "相关文段"}}]

如果没有问题，输出空数组：[]"""

COMPLIANCE_KEYWORDS = [
    # 基础敏感词列表（MVP 阶段，可后续扩展）
    "自杀", "自残", "吸毒", "贩毒",
]


@dataclass
class PromptContext:
    """Collects data needed to build a chapter generation prompt."""
    title: str = ""
    genre: str = ""
    chapter_no: int = 0
    chapter_title: str = ""
    chapter_outline: str = ""
    previous_summary: str = ""
    core_characters: str = ""  # Layer 1: ≤1000 tokens
    related_context: str = ""  # Layer 2: ≤1500 tokens
    background_knowledge: str = ""  # Layer 3: ≤1000 tokens (optional)
    word_count: int = 2000


def build_chapter_messages(ctx: PromptContext) -> list[dict]:
    """Build the messages list for chapter generation."""
    bg_section = ""
    if ctx.background_knowledge.strip():
        bg_section = f"=== 背景知识 ===\n{ctx.background_knowledge}"

    user_msg = CHAPTER_GENERATION.format(
        title=ctx.title,
        genre=ctx.genre,
        chapter_no=ctx.chapter_no,
        chapter_title=ctx.chapter_title,
        chapter_outline=ctx.chapter_outline,
        previous_summary=ctx.previous_summary or "（开篇，无前文）",
        core_characters=ctx.core_characters or "（暂无）",
        related_context=ctx.related_context or "（暂无）",
        background_section=bg_section,
        word_count=ctx.word_count,
    )

    return [
        {"role": "system", "content": OPENING_SYSTEM},
        {"role": "user", "content": user_msg},
    ]


def build_outline_messages(
    title: str, genre: str, platform: str,
    word_count: int, world_setting: str = "",
) -> list[dict]:
    """Build messages for outline generation."""
    ws = f"世界观设定：\n{world_setting}" if world_setting.strip() else ""
    wc = word_count // 10000 if word_count >= 10000 else word_count / 10000

    return [
        {"role": "system", "content": OUTLINE_SYSTEM},
        {"role": "user", "content": OUTLINE_USER.format(
            title=title, genre=genre, platform=platform or "通用",
            word_count=wc, world_setting=ws,
        )},
    ]


def build_summary_messages(
    title: str, chapter_no: int, chapter_title: str, content: str,
) -> list[dict]:
    """Build messages for chapter summary generation."""
    # Truncate content to ~3000 chars to avoid huge prompts
    truncated = content[:3000] + "..." if len(content) > 3000 else content
    return [
        {"role": "system", "content": SUMMARY_SYSTEM},
        {"role": "user", "content": SUMMARY_USER.format(
            title=title, chapter_no=chapter_no,
            chapter_title=chapter_title, content=truncated,
        )},
    ]


def build_knowledge_extract_messages(
    title: str, chapter_no: int, chapter_title: str,
    content: str, current_knowledge: str,
) -> list[dict]:
    """Build messages for knowledge extraction."""
    truncated = content[:4000] + "..." if len(content) > 4000 else content
    return [
        {"role": "system", "content": KNOWLEDGE_EXTRACT_SYSTEM},
        {"role": "user", "content": KNOWLEDGE_EXTRACT_USER.format(
            title=title, chapter_no=chapter_no,
            chapter_title=chapter_title, content=truncated,
            current_knowledge=current_knowledge or "（空）",
        )},
    ]


def build_consistency_check_messages(
    title: str, chapter_no: int,
    content: str, known_facts: str,
) -> list[dict]:
    """Build messages for consistency checking."""
    truncated = content[:4000] + "..." if len(content) > 4000 else content
    return [
        {"role": "system", "content": CONSISTENCY_CHECK_SYSTEM},
        {"role": "user", "content": CONSISTENCY_CHECK_USER.format(
            title=title, chapter_no=chapter_no,
            content=truncated, known_facts=known_facts or "（暂无）",
        )},
    ]


def check_compliance(content: str) -> list[dict]:
    """Basic keyword compliance check. Returns list of issues."""
    issues = []
    for keyword in COMPLIANCE_KEYWORDS:
        if keyword in content:
            issues.append({
                "keyword": keyword,
                "severity": "high",
                "message": f"包含敏感词：{keyword}",
            })
    return issues


def parse_json_response(text: str) -> list:
    """Try to parse a JSON array from AI response text."""
    text = text.strip()
    # Find JSON array in the response
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
