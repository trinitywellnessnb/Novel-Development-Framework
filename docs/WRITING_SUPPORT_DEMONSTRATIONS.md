# Observed native literary demonstrations

On 2026-11-23 native Codex subagents actually read the prepared synthetic excerpts, authored assessments/proposals, and submitted them to `accept_result`. These are observed model outputs, not fixture-generated answers, human beta research, accuracy benchmarks, or author decisions. Only the explicitly synthetic corpus under `tests/fixtures/writing_support/` was used. Raw packets/results/reports remain private local derived files under `.writing-support/native-demo/`.

| Task | Observed outcome | Limits |
| --- | --- | --- |
| Continuity | Three findings: sole key used before permitted transfer; changed eye colour; apprentice mind-reading unavailable | Comparison of selected passages only |
| POV | Two findings: inaccessible private intention and childhood memory | Explicitly uncertain inference was allowed |
| Voice | One base narrative-distance conflict; separate craft challenge found an unsupported universal moral | No abstract drift manufactured in the baseline |
| Dialogue | Baseline zero findings; separate craft challenge found identical procedural lines against established speaker direction | Deliberate imitation remains allowed |
| Expansion | 63 to 97 words; all five protected requirements checked; separate patch | Preservation is a reviewer assertion requiring author review |
| Condensation | 63 to 43 words; protected beats retained; separate patch | Same semantic limitation |
| Handoff | Seven cited entries across entry/exit, changes, decisions, knowledge, obligations and carry-forward | Empty categories do not invent facts |
| Simulated reader | Nine passage-backed observations and five questions for human readers | NOT blinded: inherited context and retrieval could not be restricted |

All ten submitted results passed evidence/scope validation as `REVIEWED`. This establishes actual execution and valid quotation boundaries, not correctness or comprehensive literary coverage. Consistent scarf detail, deception, mistaken belief, later development, deliberate mystery, and incomparable clocks were not indiscriminately labeled contradictions.

The original revision fixture's SHA-256 remained `3c581f272c7d7e005705d6b33273902c9d3b0db2bcfc725cfd9e420ecd531373`. No source prose changed. The actual unapproved condensation proposal was:

> Mira waited by the locked courtyard gate, rain dripping from her red wool scarf. The bell had not rung. She rested her palm against the wall. She could call Tovan, but the rule was clear: wait. She took her hand away and stayed.

The actual unapproved expansion proposal was:

> Mira waited by the locked courtyard gate, rain running from the end of her red wool scarf. She put her palm against the wall and looked at the gate. Still locked. She left her hand there a moment longer.
>
> The bell had not rung.
>
> She could call for Tovan. His name would be easy enough to call; waiting gave her nothing to do with it. But the rule was clear. She took her hand from the wall and looked once more at the gate. She would wait for the bell. Until then, she stayed where she was.

Reproduce task inputs with `python scripts/writing_toolkit.py demo` in a fresh checkout/output workspace, then ask native Codex to follow `docs/skills/writing-support/SKILL.md` for each prepared packet. Model answers may vary. Do not substitute stored demonstrations for actually executing a new assessment. The optional shell `native` adapter was exercised here but returned authentication HTTP 401; the successful model executions used current-session native subagents. No new model account or API endpoint was introduced.
