#!/usr/bin/env bash
set -euo pipefail

migrate=false
check=false
dry=false
for arg in "$@"; do
    case "$arg" in
        --migrate-v1) migrate=true ;;
        --check) check=true ;;
        --dry-run) dry=true ;;
        *) printf 'Unknown option: %s\n' "$arg" >&2; exit 2 ;;
    esac
done
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
codex_home=${CODEX_HOME:-"$HOME/.codex"}
workbuddy_home=${WORKBUDDY_CONFIG_DIR:-""}
if [ -n "$workbuddy_home" ] && [[ "$workbuddy_home" != /* ]]; then
    printf 'WORKBUDDY_CONFIG_DIR must be an absolute path: %s\n' "$workbuddy_home" >&2
    exit 2
fi
command -v python3 >/dev/null || { printf 'Python 3 is required.\n' >&2; exit 2; }
problems=0
planned_removals=''

action() {
    local label=$1
    shift
    printf '%s\n' "$label"
    if ! $dry; then "$@"; fi
}

problem() {
    printf 'CHECK FAIL %s\n' "$1"
    problems=1
}

# Check rules/global.md UTF-16 code unit length against WorkBuddy MEMORY.md 4000-unit cap.
global_utf16_len=$(python3 - "$repo/rules/global.md" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
print(len(text.encode("utf-16-le")) // 2)
PY
)
if [ "$global_utf16_len" -gt 4000 ]; then
    problem "rules/global.md length ($global_utf16_len UTF-16 units) exceeds 4000-char MEMORY.md limit"
fi

legacy_roots=("$HOME/.cursor" "$HOME/.claude" "$codex_home")
if [ -n "$workbuddy_home" ]; then
    legacy_roots+=("$workbuddy_home")
fi

# Validate the entire recorded deletion list before making any changes.
plan=$(python3 - "$repo" "${legacy_roots[@]}" <<'PY'
import json, os, sys
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
for raw in dict.fromkeys(sys.argv[2:]):
    state_dir = Path(raw) / 'my-matt-workflow'
    state = state_dir / 'install-state.json'
    if not os.path.lexists(state_dir):
        continue
    targets = []
    if state.exists():
        data = json.loads(state.read_text())
        home = data['skills_home']
        names = data['skills']
        if not isinstance(home, str) or not Path(home).is_absolute() or not isinstance(names, list):
            raise SystemExit(f'Invalid migration record: {state}')
        for name in names:
            if not isinstance(name, str) or not name.startswith('my-') or '/' in name or '\n' in name:
                raise SystemExit(f'Invalid Skill name in {state}: {name!r}')
            targets.append(Path(home) / name)
    targets.append(state_dir)
    for target in targets:
        # Resolve parents, but not a final symlink, since rm removes the link itself.
        effective = target.parent.resolve() / target.name
        if '\n' in str(target) or effective == repo or effective in repo.parents or repo in effective.parents:
            raise SystemExit(f'Unsafe migration target: {target}')
        print(target)
PY
)

if $migrate && ! $check; then
    if $dry; then planned_removals="$plan"$'\n'; fi
    while IFS= read -r target; do
        [ -n "$target" ] || continue
        if [ -e "$target" ] || [ -L "$target" ]; then
            action "REMOVE legacy $target" rm -rf -- "$target"
        fi
    done <<< "$plan"
fi

link_target() {
    python3 - "$1" <<'PY'
import sys
from pathlib import Path
print(Path(sys.argv[1]).resolve())
PY
}

# Include previous host Skill locations when finding stale repository links.
skill_dirs=("$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.cursor/skills"
            "$codex_home/skills")
scan_dirs=("${skill_dirs[@]}" "$HOME/.claude" "$codex_home")
if [ -n "$workbuddy_home" ]; then
    skill_dirs+=("$workbuddy_home/skills")
    scan_dirs+=("$workbuddy_home/skills" "$workbuddy_home")
fi
for dir in "${scan_dirs[@]}"; do
    [ -d "$dir" ] || continue
    for target in "$dir"/*; do
        [ -e "$target" ] || [ -L "$target" ] || continue
        resolved=$target
        if [ -L "$target" ]; then
            resolved=$(link_target "$target")
            case "$resolved" in
                "$repo"/*)
                    if [ ! -e "$target" ]; then
                        if $check; then problem "stale link $target";
                        else
                            action "REMOVE stale $target" rm -- "$target"
                            if $dry; then planned_removals="$planned_removals$target"$'\n'; fi
                        fi
                    fi
                    continue ;;
            esac
        fi
        case "${target##*/}" in
            my-*)
                # A dry-run migration still sees entries scheduled for removal.
                planned=false
                if $migrate && ! $check; then
                    while IFS= read -r old; do
                        if [ "$old" = "$target" ]; then planned=true; break; fi
                    done <<< "$plan"
                fi
                if ! $planned; then
                    printf 'REPORT unmanaged %s\n' "$target"
                    if $check && [ -d "$repo/skills/${target##*/}" ]; then
                        for skill_dir in "${skill_dirs[@]}"; do
                            if [ "$dir" = "$skill_dir" ]; then
                                problem "managed Skill name conflicts with $target"
                                break
                            fi
                        done
                    fi
                fi ;;
        esac
    done
done

sync_link() {
    local source=$1 target=$2 planned=false old backup
    if [ ! -e "$source" ]; then problem "missing source $source"; return; fi
    if $dry && ! $check; then
        while IFS= read -r old; do
            if [ "$old" = "$target" ]; then planned=true; break; fi
        done <<< "$planned_removals"
    fi
    if ! $planned && [ -L "$target" ] && [ "$(link_target "$target")" = "$source" ]; then
        printf 'OK %s -> %s\n' "$target" "$source"
        return
    fi
    if $check; then problem "expected $target -> $source"; return; fi
    if ! $planned && { [ -e "$target" ] || [ -L "$target" ]; }; then
        if [ -f "$target" ] && [ ! -L "$target" ]; then
            backup="${target}.bak.$(date +%Y%m%d%H%M%S)"
            action "BACKUP $target -> $backup" mv -- "$target" "$backup"
        else
            action "REPLACE $target" rm -rf -- "$target"
        fi
    fi
    if [ ! -d "${target%/*}" ]; then
        action "MKDIR ${target%/*}" mkdir -p -- "${target%/*}"
    fi
    action "LINK $target -> $source" ln -s -- "$source" "$target"
}

for source in "$repo"/skills/*; do
    [ -d "$source" ] || continue
    sync_link "$source" "$HOME/.agents/skills/${source##*/}"
    sync_link "$source" "$HOME/.claude/skills/${source##*/}"
    if [ -n "$workbuddy_home" ]; then
        sync_link "$source" "$workbuddy_home/skills/${source##*/}"
    fi
done
sync_link "$repo/rules/global.md" "$HOME/.claude/CLAUDE.md"
sync_link "$repo/rules/global.md" "$codex_home/AGENTS.md"
if [ -n "$workbuddy_home" ]; then
    sync_link "$repo/rules/global.md" "$workbuddy_home/MEMORY.md"
fi

if $check && [ -n "$plan" ]; then problem 'legacy installation remains; run --migrate-v1'; fi
exit "$problems"
