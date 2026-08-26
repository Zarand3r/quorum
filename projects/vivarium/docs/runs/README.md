# Raw run logs, preserved

`/tmp` is volatile and `AUTONOMOUS_LOG.md` records only the analysis. These are the raw checkpoint logs
behind the claims in `PAPER.md`, so any number in it can be re-derived rather than taken on trust.

| prefix | what it is | paper section |
|---|---|---|
| `deno_sd450*` | 18 fresh dispersed-start seeds; the 2/18 formation rate | 4 |
| `emerge3T_sd*` / `emerge3_sd*` | transformer engine against its matched integrator control, 6 seeds each at 1.6M | 12.4 |
| `pocket_ns81*` | 5 noise-only replicas from sd45004's pocket state | 4.4 |
| `fis_f*` / `fis2_f*` | osmotic deflation, 4 fills x 5 seeds then 15+15 at fill 1.0 and 0.50 | 13 |
| `multi_sd9100*` | N=320 in L=92, the two-vesicle attempt | 12.3 |
| `noise_ns*` / `place_bs*` / `varA_*` / `varB_*` | separating placement from thermal noise | 17 |

**Column map:** 1 step, 2 E/lip, 3 largest, 4 R_mid, 5 shellCV, 6 hollow, 7 mix, 8 seg, 9 burial,
10 core, 11 lumen_c, 12 nenc, 13 perc, 14 lumen, 15 lumenW, 16 shortOUT, 17 shortIN, 18 enrichment,
19 nves, 20 lumH2O.

Filter numeric rows before parsing: `awk '$1 ~ /^[0-9]+$/ && NF>15'`. The header line contains words in
the numeric columns and will silently corrupt a naive tally, which it did once here, turning 2/18 into
an apparent 5/18.
