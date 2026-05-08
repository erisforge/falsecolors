#!/usr/bin/env bash
#
# preserve.sh — Eris FALSECOLORS prior-art preservation
#
# Establishes a cryptographic prior-art record for the current repo state
# by combining two independent witnesses:
#
#   1. Software Heritage    (archival + content-addressable identifier)
#   2. OpenTimestamps       (Bitcoin block attestation, ~24h to upgrade)
#
# Pipeline:
#   - push current main to origin
#   - submit SWH Save Code Now (round 1: bare code state)
#   - poll until snapshot SWHID is available
#   - generate MANIFEST.sha256 (file hashes + git HEAD + SWH SWHID)
#   - ots stamp manifest + each Eris_FALSECOLORS_*.md + falsecolors.py
#   - commit and push the manifest + .ots proofs
#   - submit SWH Save Code Now (round 2: archive includes the proofs)
#   - print summary and the ots upgrade reminder for ~25h later
#
# Run at meaningful checkpoints: paper revisions, code milestones,
# pre-disclosure events. Not for WIP commits.
#
# Requires: git, curl, python3, ots (brew install opentimestamps-client).
# Assumes: working tree clean, on main, origin is a public GitHub HTTPS URL.
#
# Usage: ./preserve.sh

set -euo pipefail

# ---------------------------------------------------------------- preflight

cd "$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: not inside a git repository" >&2
    exit 1
}

for cmd in git curl python3 ots shasum; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "ERROR: required command not found: $cmd" >&2
        [[ "$cmd" == "ots" ]] && echo "  install: brew install opentimestamps-client" >&2
        exit 1
    }
done

if [[ -n "$(git status --porcelain)" ]]; then
    echo "ERROR: working tree is dirty. Commit or stash first." >&2
    git status --short >&2
    exit 1
fi

branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$branch" != "main" ]]; then
    echo "ERROR: not on main (currently on $branch)" >&2
    exit 1
fi

origin_url=$(git config --get remote.origin.url || true)
if [[ ! "$origin_url" =~ ^https://github\.com/ ]]; then
    echo "ERROR: origin is not a GitHub HTTPS URL: $origin_url" >&2
    exit 1
fi
# Strip trailing .git for SWH browse URLs and ensure it has it for the API
swh_origin="$origin_url"
[[ "$swh_origin" =~ \.git$ ]] || swh_origin="${swh_origin}.git"

# --------------------------------------------------------------- helpers

swh_save() {
    # POST a Save Code Now request, echo the request id
    curl -sS -X POST -H "Accept: application/json" \
        "https://archive.softwareheritage.org/api/1/origin/save/git/url/${swh_origin}/" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
}

swh_poll() {
    # Poll a save request until succeeded/failed, echo the snapshot SWHID
    local req_id="$1"
    local label="$2"
    for i in $(seq 1 60); do
        local poll status swhid
        poll=$(curl -sS "https://archive.softwareheritage.org/api/1/origin/save/${req_id}/")
        status=$(echo "$poll" | python3 -c 'import json,sys; print(json.load(sys.stdin)["save_task_status"])')
        case "$status" in
            succeeded)
                swhid=$(echo "$poll" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("snapshot_swhid",""))')
                echo "$swhid"
                return 0
                ;;
            failed)
                echo "ERROR: SWH save $label failed: $poll" >&2
                return 1
                ;;
        esac
        echo "    [$label $i/60] status=$status; sleep 5s..." >&2
        sleep 5
    done
    echo "ERROR: SWH save $label timed out after 5min" >&2
    return 1
}

# ---------------------------------------------------------- 1. push main

echo "==> push origin main"
git push origin main

# ----------------------------------------- 2. SWH round 1 (pre-manifest)

echo "==> SWH submission 1/2 (bare code state)"
req1=$(swh_save)
echo "    request id: $req1"
swhid1=$(swh_poll "$req1" "1/2")
echo "    snapshot:   $swhid1"

# ---------------------------------------------- 3. generate MANIFEST.sha256

echo "==> generating MANIFEST.sha256"
{
    echo "# Eris FALSECOLORS — Cryptographic Manifest"
    echo "# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "# Git HEAD: $(git rev-parse HEAD)"
    echo "# Git HEAD tree: $(git rev-parse HEAD^{tree})"
    echo "# Origin: $origin_url"
    echo "# SWH snapshot (pre-manifest): $swhid1"
    echo "# SWH browse: https://archive.softwareheritage.org/browse/origin/?origin_url=${origin_url}"
    echo ""
    echo "# SHA-256 of every git-tracked file:"
    git ls-files | sort | xargs shasum -a 256
} > MANIFEST.sha256
echo "    $(wc -l < MANIFEST.sha256 | tr -d ' ') lines"

# -------------------------------------------- 4. identify + stamp artifacts

artifacts=("MANIFEST.sha256")
[[ -f falsecolors.py ]] && artifacts+=("falsecolors.py")
while IFS= read -r -d '' paper; do
    artifacts+=("$paper")
done < <(find . -maxdepth 1 -name 'Eris_FALSECOLORS_*.md' -print0 | sort -z)

echo "==> ots stamp ${#artifacts[@]} artifact(s):"
for a in "${artifacts[@]}"; do echo "    $a"; done
ots stamp "${artifacts[@]}"

# -------------------------------------------------------- 5. commit + push

echo "==> commit + push proofs"
git add MANIFEST.sha256
for a in "${artifacts[@]}"; do git add "${a}.ots"; done

if git diff --cached --quiet; then
    echo "    nothing to commit (manifest and .ots files unchanged)"
else
    git commit -m "preserve: $(date -u +%Y-%m-%d) prior-art checkpoint"
    git push origin main
fi

# ---------------------------------------- 6. SWH round 2 (with proofs)

echo "==> SWH submission 2/2 (archive includes proofs)"
req2=$(swh_save)
echo "    request id: $req2"
swhid2=$(swh_poll "$req2" "2/2")
echo "    snapshot:   $swhid2"

# --------------------------------------------------------- 7. summary

# +25h reminder, BSD date (macOS) or GNU date (Linux)
if upgrade_at=$(date -u -v+25H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null); then :
else upgrade_at=$(date -u -d '+25 hours' +%Y-%m-%dT%H:%M:%SZ); fi

ots_files=()
for a in "${artifacts[@]}"; do ots_files+=("${a}.ots"); done

cat <<EOF

==================================================================
Preservation complete.

  Git HEAD:           $(git rev-parse HEAD)
  SWH (pre):          $swhid1
  SWH (with proofs):  $swhid2
  SWH browse:         https://archive.softwareheritage.org/browse/origin/?origin_url=${origin_url}
  OTS proofs:         ${#ots_files[@]} (Bitcoin attestation pending)

For citation, use SWH (with proofs): $swhid2

NEXT STEP — run after $upgrade_at to embed the Bitcoin attestation:

  ots upgrade ${ots_files[*]}
  git add ${ots_files[*]}
  git commit -m "ots upgrade: attach Bitcoin block attestations to prior-art proofs"
  git push origin main

==================================================================
EOF
