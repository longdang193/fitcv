---
name: tag_management
description: "Instruct agent to use available tools from .cursor/tools/ for tag management tasks"
---

# Agent Tools Usage Skill

## When to Apply

**Only apply this rule when working with tag-related operations in markdown files with YAML frontmatter.**

Do not apply for general markdown editing, UI components, or non-tag operations.

## Available Tools

When working with tag-related operations, use the tools in `./tools/` instead of reimplementing functionality.

### Core Tools

1. **normalize-tags**
   - Normalizes tag formats in YAML frontmatter.
   - Example Function: `normalizeTagsInMetadata(content: string): string`
   - Use when: Normalizing tags, standardizing tag formats, batch processing files.

2. **find-files-by-tag**
   - Finds markdown files by tag.
   - Example Function: `findFilesByTag(searchPath: string, tagInput: string): Promise<string[]>`
   - Use when: Searching for files with specific tags, discovering tagged content.

## Guidelines

- **Use tools** when task matches tool functionality (normalizing tags, finding files by tag).
- **Don't reimplement** functionality that tools already provide.
- **Check READMEs** for usage examples, API details, and edge case handling.
- **Extend tools** if behavior is insufficient - consult tool README first, then extend the tool rather than duplicating logic elsewhere.
- **Combine tools** with existing utilities when needed for complex workflows.

## Additional Documentation

Complete documentation, examples, and API details:

- **Main README**: `./tools/README.md`
- **Tool-specific READMEs**: Each tool has its own README in its directory.
