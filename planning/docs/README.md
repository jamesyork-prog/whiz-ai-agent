# Documentation

This directory contains architectural documentation and clarifications created during development.

## Documents

### GEMINI_INTEGRATION_CLARIFICATION.md
**Purpose:** Clarifies the actual implementation architecture vs. what was tested.

**Key Points:**
- Explains that `process_ticket_end_to_end` tool is the actual implementation (not journey-based)
- Documents why the journey approach was abandoned (freezing issues)
- Clarifies that Task 5.3 verified tool calling, not the full workflow architecture
- Separates Gemini integration issues from booking extraction issues

**Audience:** Developers working on the codebase

**Status:** Reference document for understanding current architecture

### GEMINI.md
**Purpose:** Original Gemini integration documentation or notes.

**Note:** Review this file to determine if it's still relevant or if it can be merged with other documentation.

## Related Documentation

- `.kiro/specs/gemini-llm-integration/` - Formal spec for Gemini integration
- `.kiro/specs/policy-based-decisions/` - Formal spec for policy-based decisions
- `planning/testing/` - Test results and verification documentation

## Maintenance

These documents should be reviewed periodically to ensure they remain accurate as the codebase evolves.
