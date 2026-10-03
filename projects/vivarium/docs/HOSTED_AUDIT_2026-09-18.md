# Hosted vivarium audit and deployment

Updated 2026-09-18. Active URL:
[hosted vivarium](https://workstation.tail16c86d.ts.net/vivarium).
The UI's markup, styles, labels, layout, painter, and controls are unchanged. JavaScript changes are
limited to accepting ordered snapshots, clearing interpolation between different runs, and skipping
redundant settled-frame draws. A fixed-state browser comparison produced pixel-identical canvases.

## Bugs fixed

| Issue | Correction |
|---|---|
| New seed reloaded the same saved seed-509 positions | Restarts construct a dispersed run at the selected seed, regardless of initial saved-state mode |
| Same-seed restart started from an already formed ring | Same seed deterministically reconstructs the dispersed initial configuration and thermostat state |
| Server launch defaulted to saved positions | Default start is now dispersed; saved evidence remains available explicitly with `--vesicle-start formed` |
| Pseudo-slider closures pointed to the previous engine | Restart rebinds getters/setters to the new engine and preserves current parameters |
| Affinity changes silently moved every particle back to its starting position while retaining the old tick | Rebuild the law at current positions; retain velocities, RNG, and tick; recompute the carried force |
| Parameter mutation could race stepping or mix an old snapshot with a new engine's parameters | Reentrant lock covers mutations, pause acknowledgement, restart, and complete snapshot construction |
| Invalid, infinite, or out-of-range parameters could reach physics | Validate the entire request before mutation; reject invalid inputs with HTTP 400 |
| A failed step could leave a dead worker and a falsely running dish | Preserve last finite positions, pause with an API error status, and require restart to recover |
| Cached edges/aliveness could survive restart | Clear cached observation state and reject old-run aliveness work |
| Query strings broke state/stream route recognition; HEAD returned 501 | Parse paths separately and support body-free HEAD requests |
| Saved-state verdict appeared to describe current geometry forever | Separate source evidence from the current `vesicle_gate` verdict, tagged with evaluation tick |
| Saved positions could be loaded into a different box/topology | Check box length, bead count, species, and molecule indexing |
| Restart interpolated unrelated old/new particles across the screen | New run identity resets the interpolation predecessor; older snapshot sequences are ignored |
| Motion arrived in periodic visual bursts | Evaluate the costly vesicle diagnostic from copied geometry off the physics/stream lock and at a 5,000-step observational cadence |
| Restart paused and then visually caught up in bursts | Defer the tick-zero diagnostic, reset the interpolation clock for a new run, and interpolate the tick readout on the same timeline as positions |
| /vivarium/2d and /vivarium/3d proxied dead ports | 2-D aliases the active dish; archived 3-D redirects to /vivarium |
| Hosted process was an unsupervised background process | Enabled user `vivarium.service`, with restart on failure and a repeatable `host.sh` installer |
| Default cold-run pause horizon could miss rings first seen at 850k–950k | Dispersed run horizon is now 1,000,000 steps; manual resume remains available |

Only the control/observation layer changed. The production physical potential, timestep, and
transformer/MLP wiring were not changed. Comparing the original and updated **full production dish**
for 1,000 steps gave bit-identical particle positions and velocities.

## Performance measurements and changes

These are diagnostic measurements on the development host, not pre-registered research results or
portable performance guarantees. Chrome was headless on this machine; phone/GPU behavior may differ.

| Measurement | Value | Interpretation |
|---|---|---|
| Warm production step, 100 steps | 3.08 ms | The old 30 Hz pacing cap left substantial unused simulation throughput |
| First snapshot with classification | 126.99 ms | The gate is expensive; evaluate periodically, not every displayed frame |
| Cached-classification snapshot, 20 samples | 1.22 ms | Moderate per-viewer snapshot construction cost |
| JSON encoding, 20 samples | 1.76 ms | Repeated serialization for multiple viewers is avoidable |
| Sample frame | 165,341 bytes | At 20 Hz, approximately 3.3 MB/s per continuously streaming viewer |
| Browser draw, 40 fixed-fixture samples | median 3.90 ms; p95 4.70 ms | Suitable on this host; repainting a paused dish at 60 Hz is wasteful |
| Original vs optimized rendering, 120 settled-frame requests | 120 vs 1 draws | Same pixels, less idle work |
| Updated stream while paused, 2 seconds | 1 frame; 166,005 bytes | Initial state only; subsequent unchanged frames are suppressed |
| Updated stream while running, 2 seconds | 37 frames; 6,134,152 bytes | Streaming remains close to its 20 Hz limit |
| Old vs updated wall-clock step pacing | 30.0 vs 183.9 steps/s | Host targets 200 Hz; displayed stream remains capped at 20 Hz |

`stream_frame` shares one serialization among viewers requesting the same state. Each connection
sends only changed states and uses a 15-second comment heartbeat while unchanged. Primary SSE
viewers therefore avoid both repeated full paused-state transfer and continuous idle canvas repaint.
The polling fallback still fetches snapshots every 120 ms; it is not the primary transport.

The archived blob aliveness computation no longer consumes CPU for the molecular dish. Its API
value is null because it is not a validated membrane-life measurement; the unchanged viewer's
existing null fallback displays zero. The preserved architecture prose likewise still describes an
older engine. These presentation limitations are recorded rather than redesigned against the
instruction to preserve the UI. The physics review explains the actual model.

The preserved painter also uses the older solvent display radius 0.30, while this field's water
bead radius is 0.50; it does not draw 2-D bond segments. Heads and tails do use radius 0.50. The API
now supplies actual radii, but changing the painter's visible geometry was deliberately left out.
Thus the canvas comparison establishes unchanged rendering, not fully faithful solvent depiction.

The cell-list implementation was also inspected. It avoids dense all-pairs work in the production
box. Its linear-cost description assumes bounded local occupancy; the globally padded cell table
can become costly with extreme crowding. No neighbour-list algorithm or summation order was changed.
One existing 3-D timing gate failed intermittently during the full suite, then all four neighbour
performance tests passed in isolation. Its cause is not isolated; the threshold was not weakened.

Live SSE timing isolated a separate periodic hitch: ordinary frames arrived about 55 ms apart, but
the synchronous vesicle classification produced 290–330 ms gaps near its 1,000-step boundaries.
After moving that observational calculation off the critical path, a live sample spanning two such
boundaries had a 96.7 ms worst gap. Normal display frames still summarize roughly 9–10 physical
steps because dynamics run near 184 steps/s while the stream cap is 20 Hz.

At the later full-speed setting, the diagnostic cadence is 5,000 steps (roughly 10 seconds) so an
observational classifier does not consume a large CPU share; this changes no force or timestep.

The later 2026-09-22 browser audit found a second source of restart bursts. The one-off restart gap was
fed into the frame-gap moving average, stretching interpolation beyond the next SSE arrival. Each new
frame then overtook an unfinished interpolation. Resetting the visual timeline on a new `run_id` and
moving the initial geometry gate off restart reduced measured click-to-first-new-run-paint from 264 ms
to 99 ms. The tick label now follows the same interpolation as positions instead of jumping directly
to the newest snapshot. Static metadata updates once per snapshot rather than once per display frame.
At 2,959 particles, the original harmonic polygon painter measured 3.7--3.9 ms median. Production
beads have exactly flat contour coefficients, so the deployed viewer now uses the browser's native
circle primitive for them and retains the full harmonic painter for non-flat morphing tokens. The
hosted result measures **0.5 ms median and 0.6 ms p95**, while JSON parsing of the 165.7 kB state is
0.4 ms median and 0.5 ms p95.

## Validation and deployment

- Browser tests through the **actual HTTPS hosted address**, using both polling and primary SSE:
  new seed changes, same seed stays selected, both start dispersed, affinity changes hit the active
  engine, reset restores production settings, and no JavaScript exceptions occurred.
- Targeted hosted-control, dish, physical-realism, angle, many-body, slider, and performance checks
  pass. Concurrency tests cover pause during an in-flight step and error/restart recovery.
- Full suite before the final HEAD/horizon refinements: **313 passed, 14 skipped, 2 failed**.
  Failures are the pre-existing disconnected-token-MLP assertion and the intermittent neighbour
  timing assertion. Subsequent targeted checks pass, including the latter; the MLP assertion remains
  unresolved and was not weakened. Do not describe the full suite as green.
- Hosted HTML bytes match the workspace. Static UI markup/styles match HEAD; fixed-state canvas
  output is pixel-identical before/after the scheduling optimization.
- External 2-D route returns the active dish; external archived 3-D route returns HTTP 302 to
  `/vivarium`. Tailscale strips mounted prefixes, so the 3-D proxy explicitly includes the backend
  path needed to issue that redirect.
- Unrelated proxy routes, listeners, and the original Funnel exposure were checked against the
  saved pre-deployment configuration. `host.sh` preserves the existing Serve/Funnel mode rather
  than switching the whole HTTPS listener's exposure.

To update again:

```
bash projects/vivarium/host.sh
systemctl --user status vivarium.service
journalctl --user -u vivarium.service
```

The unit serves `--vesicle --vesicle-start dispersed --hz 1000 --autopause 1000000 --port 8090`.
The target intentionally exceeds the measured compute ceiling, so the simulation advances as fast as
the host permits while yielding between steps; external measurements on 2026-09-22 ranged from about
400 to 493 steps/s as observation work and host load varied.
This is wall-clock pacing, not a changed physical timestep: `dt` remains 0.008. User-service boot
behavior follows this machine's user-manager/login policy; the unit is enabled for its default target.

The independent [physics and architecture review](PHYSICS_REVIEW_2026-09-18.md) is part of this audit.
An MLP is permitted and can model local reactions or an energy-consistent internal shape response;
it is not a prerequisite for molecular membrane assembly. Full strict architecture compliance
remains an open issue, distinct from the repaired hosted controls.
