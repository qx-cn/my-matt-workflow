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

# Validate the entire recorded deletion list before making any changes.
plan=$(python3 - "$repo" "$HOME/.cursor" "$HOME/.claude" "$codex_home" <<'PY'
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
    local source=$1 target=$2 planned=false old
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
        action "REPLACE $target" rm -rf -- "$target"
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
done
sync_link "$repo/rules/global.md" "$HOME/.claude/CLAUDE.md"
sync_link "$repo/rules/global.md" "$codex_home/AGENTS.md"

if $check && [ -n "$plan" ]; then problem 'legacy installation remains; run --migrate-v1'; fi
exit "$problems"
