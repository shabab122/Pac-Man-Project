# Verified Results

Verification was completed against the upgraded project on 17 September 2026.

## Environment

- Python 3.12.14
- pygame-ce 2.5.6
- ReportLab 4.4.9
- pytest 8.4.2

## Automated checks

| Check | Command | Result |
|---|---|---|
| Standard-library suite | `python run_tests.py` | 19/19 passed |
| Independent pytest run | `python -m pytest -q` | 19/19 passed |
| Bytecode compilation | `python -m compileall -q pacman_ai tests main.py run_tests.py tools` | Passed |
| Headless startup/render | `python main.py --smoke-test` | Passed |
| Full interface gallery | `python main.py --qa-gallery qa_gallery` | 10 screens rendered |

The upgrade tests cover heuristic variants, deterministic AUTO selection,
advanced ghost behavior, explicit-map round trips, safe Map Studio saving,
experiments, CSV/PDF output, replay JSON, and preference-preserving resets.

## Reproducible five-scenario experiment

The included sample was generated on packaged map **Cyber Citadel**. Every
algorithm received the same five targets and the same static snapshot for each
target.

| Algorithm | Success | Average steps | Average cost | Average expanded |
|---|---:|---:|---:|---:|
| BFS | 5/5 | 41.8 | 58.2 | 195.8 |
| DFS | 5/5 | 64.6 | 90.2 | 165.8 |
| UCS | 5/5 | 41.8 | 54.8 | 194.0 |
| Dijkstra | 5/5 | 41.8 | 54.8 | 194.0 |
| A* with Manhattan | 5/5 | 41.8 | 54.8 | 151.2 |

Interpretation:

- BFS matched the weighted algorithms' average step count but paid a larger
  weighted cost.
- DFS found every target but used more steps and higher cost in this sample.
- UCS and Dijkstra matched, as expected for this non-negative single-target
  grid model.
- Manhattan A* matched the minimum weighted cost while expanding fewer nodes
  than UCS and Dijkstra in these controlled scenarios.

## A* heuristic comparison

| Heuristic | Success | Average cost | Average expanded | Guarantee |
|---|---:|---:|---:|---|
| Manhattan | 5/5 | 54.8 | 151.2 | Optimal in this four-direction grid |
| Euclidean | 5/5 | 54.8 | 157.4 | Optimal but less grid-specific |
| Weighted A* | 5/5 | 54.8 | 132.6 | No general optimality guarantee |

Weighted A* explored the fewest nodes in this sample. That result is evidence
for these five scenarios, not a claim that it always wins or always preserves
optimal cost.

## Artifact checks

- The sample CSV was parsed successfully and contains algorithm and heuristic
  rows for all five scenarios.
- The sample replay JSON uses format `pacman-ai-replay-v1` and contains 13
  logical frames.
- The experiment PDF is a valid, unencrypted, single-page landscape A4 report
  with extractable text.
- The neutral project presentation contains 11 slides, speaker notes, three
  editable tables, and one editable chart. Package, layout, font, chart, table,
  and re-import validation all passed with zero findings and zero warnings.
- Every presentation slide and every game QA screen was visually reviewed for
  clipping, overlap, and readability.

## Controlled full-mission regression

The original complete-run benchmark remains useful as a regression result. On
Cyber Citadel with ghosts removed, all five original solvers completed the same
mission:

| Algorithm | Complete | Travelled steps | Terrain cost | Expanded nodes |
|---|---:|---:|---:|---:|
| BFS | Yes | 250 | 272 | 1,168 |
| DFS | Yes | 664 | 706 | 4,137 |
| UCS | Yes | 252 | 260 | 1,093 |
| Dijkstra | Yes | 252 | 260 | 1,093 |
| A* | Yes | 252 | 260 | 624 |

Runtime measurements are intentionally not treated as universal results because
small-map timing depends on the computer, Python build, and current system load.
