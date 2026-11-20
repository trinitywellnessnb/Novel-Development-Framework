# Agent-pattern provenance and scope

This upgrade adapts workflow ideas after inspecting the fork at `trinitywellnessnb/500-AI-Agents-Projects`: source retrieval from `agents/03-pdf-qa-agent`, opposed analysis from `agents/20-multi-agent-debate`, and testing from `agents/15-unit-test-generator`. Its catalog also points to CrewAI book-flow and self-evaluation examples. Examples were treated as reference patterns, not installed runtime dependencies or adequate source-verification solutions.

Original implementations rely on external packages, model APIs, or toy data, and do not enforce this framework's source hierarchy, private-manuscript boundaries, cross-book narrative knowledge, or separate author approvals. We implement original, standard-library offline checks and author-controlled Markdown procedures instead. No upstream agent source code or third-party model prompts are copied.

Upstream reference: https://github.com/trinitywellnessnb/500-AI-Agents-Projects
Fork license: MIT; see the source repository's license for its exact attribution requirements should future code actually be copied. Linked third-party project licenses must be checked separately.

These procedures do not install autonomous background workers, automatically write prose, index inboxes, approve canon, merge PRs, or publish manuscripts. Versioned references to research examples are explanatory rather than a claim that they are production dependencies.
