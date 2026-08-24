#!/bin/bash
# Status of LIVE vivarium runs only.
#
# Twice now a tick has reported progress from a /tmp log that no live process was writing -- once from
# a killed arm's leftovers (half160_*), once nearly from another session's arc200b_sd0..4. Globbing
# /tmp/*.log cannot tell a running experiment from a corpse. The only reliable identity of a run is the
# file its process actually holds open, so this reads /proc/<pid>/fd/1 and nothing else.
#
# Also prints VIVARIUM_* per run: an unset VIVARIUM_CHI_HT silently gives +0.20 instead of -0.25 and
# chi_WW 1.00 instead of 0.50, which invalidated 30 runs before the output filename tag caught it.
printf "%-24s %-8s %-9s %-8s %-6s %s\n" LOG SEED STEP LARGEST NVES ENV
for p in $(pgrep -f "bazel-bin/projects/vivarium"); do
  f=$(readlink /proc/$p/fd/1 2>/dev/null) || continue
  case "$f" in *.log) ;; *) continue ;; esac
  seed=$(tr '\0' ' ' < /proc/$p/cmdline | awk '{print $NF}')
  env=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -E '^VIVARIUM_CHI' | sort | tr '\n' ' ')
  [ -z "$env" ] && env="!! NO CHI OVERRIDES -- ht=+0.20 ww=1.00 !!"
  read step largest nves <<< "$(awk '/^ *[0-9]+ /{s=$1;l=$3;v=$19} END{print s+0, l+0, v+0}' "$f")"
  printf "%-24s %-8s %-9s %-8s %-6s %s\n" "$(basename "$f")" "$seed" "$step" "$largest" "$nves" "$env"
done | sort
