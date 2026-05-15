---
name: brainstorming-detailed-report-generation-prompt
description: Generate detailed brainstorming report from completed brainstorming output using canonical report template.
type: prompt
stage: planning
entry_points:
- brainstorming output already shared and user explicitly asks for detailed report
prerequisites:
- completed brainstorming output in current thread
- explicit user confirmation to generate detailed report
next_steps:
- hand report back to user for validation and decision
related_skills:
- skill-brainstorming
required_reads:
- .agents/skills/skill-brainstorming/brainstorming-detailed-report-template.md
- .agents/skills/skill-brainstorming/SKILL.md
tags:
- prompt
- planning
- brainstorming
distribution_tier: starter_kit
---

# Brainstorming Detailed Report Generation Prompt

## Not For

initial brainstorming, implementation planning, or code execution

```text
Create detailed report from completed brainstorming output in this thread.

Hard requirements:
1. Follow this template exactly:
   .agents/skills/skill-brainstorming/brainstorming-detailed-report-template.md
2. Use only facts, constraints, and options already present in thread context.
3. Do not invent missing details. If critical information is missing, state that in the final section.
4. Keep writing concise, concrete, and decision-oriented.
5. Return only final report content.
```

Expected output:

- completed detailed report that strictly follows template
