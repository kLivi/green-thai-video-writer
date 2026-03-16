#!/bin/bash
# Install green-thai-video-writer skill to Claude Code

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills/get-video"

mkdir -p "$SKILLS_DIR"

# Copy skill file
cp "$PROJECT_DIR/SKILL.md" "$SKILLS_DIR/SKILL.md"

# Copy prompt references (SKILL.md reads these relative to project root, but keep a copy)
cp -r "$PROJECT_DIR/prompts" "$SKILLS_DIR/"

# Copy config (categories.json)
mkdir -p "$SKILLS_DIR/src/config"
cp "$PROJECT_DIR/src/config/categories.json" "$SKILLS_DIR/src/config/"

echo "Installed get-video skill to $SKILLS_DIR/"
echo ""
echo "Contents:"
find "$SKILLS_DIR" -type f | sort | sed "s|$SKILLS_DIR/|  |"
echo ""
echo "Restart Claude Code to pick up changes."
