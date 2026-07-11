# Data Steward Skills

11 skills packaging the operational workflows of a Data Owner on top of the MCP tools in `../mcp_server`.

Each skill is a folder containing a `SKILL.md` (YAML frontmatter + Markdown body) following the Anthropic Skills spec. Drop this `skills/` folder into your Claude Code project, publish individual skills to Claude for Work via the admin console, or upload as agent skills to Claude.ai.

## Skill map

| Skill | When to trigger | Chains into |
| --- | --- | --- |
| `document-asset` | Document one specific asset | `link-assets-to-glossary`, `propose-data-quality-rules` |
| `review-undocumented-backlog` | Batch-review documentation debt | `document-asset` |
| `trace-data-origin` | Explain where data comes from | — |
| `impact-analysis` | Assess blast radius of a change | — |
| `arbitrate-golden-source` | Pick a golden source among candidates | `certify-golden-source`, `impact-analysis` |
| `align-referentials` | Reconcile glossary overlaps | — |
| `onboard-data-owner` | First-week brief for a new owner | most of the others |
| `monthly-stewardship-report` | Periodic health check | `align-referentials`, `review-undocumented-backlog` |
| `propose-data-quality-rules` | Define QA controls for an asset | — |
| `link-assets-to-glossary` | Enrich assets with business semantics | — |
| `certify-golden-source` | Promote an asset to golden | `impact-analysis` |

## Design principles

- **No writes without confirmation.** Every skill that touches the catalog uses dry-run tools first, then requires explicit "yes / apply" from the user.
- **Metadata only.** These skills never inspect business rows, only catalog metadata.
- **Human-in-the-loop.** The agent proposes, the Data Owner decides. Skills that could auto-mutate the catalog are explicitly gated.
- **Chainable.** Skills reference each other. The onboarding skill delegates to the others; certification blocks on prerequisite skills.
