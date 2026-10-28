# Requirements Traceability Matrix

This matrix connects requirements to stories, project tasks, and planned verification. Test identifiers are placeholders for the eventual test suite; they do not imply that tests have been implemented.

| Requirement | User story | Project task(s) | Planned verification |
|---|---|---|---|
| FR-001 Market overview | US-001 | T06, T07, T08, T16 | TC-001: Reconcile overview metrics and sample sizes |
| FR-002 Search advertisements | US-002 | T14, T15 | TC-002: Search by supported fields |
| FR-003 Filter advertisements | US-002 | T01, T02, T14, T15 | TC-003: Validate each filter against the data dictionary |
| FR-004 View advertisement details | US-003 | T14, T15 | TC-004: Render available and missing detail fields |
| FR-005 Link to original source | US-003 | T01, T03, T15 | TC-005: Validate source URL handling |
| FR-006 Explore skill demand | US-004 | T03, T06, T07, T09, T16 | TC-006: Reconcile normalized skill counts |
| FR-007 Compare markets | US-005 | T06, T08, T16 | TC-007: Verify units, filters, and sample-size context |
| FR-008 Show time trends conditionally | US-006 | T01, T06, T07, T16 | TC-008: Confirm date-quality gate and period labels |
| FR-009 Accept skill input | US-008 | T10, T17 | TC-009: Validate valid, empty, unknown, and oversized input |
| FR-010 Rank and explain matches | US-009 | T10, T17 | TC-010: Review ranking and explanation against test cases |
| FR-011 Identify skill gaps | US-010 | T09, T10, T17 | TC-011: Verify evidence and gap ordering |
| FR-012 Provide reviewed resources | US-011 | T09, T17 | TC-012: Audit links and free-access verification dates |
| FR-013 Support English and Arabic | US-012 | T17, T18 | TC-013: Review translated critical flows and RTL behavior |
| FR-014 Explain methodology and limitations | US-013 | T08, T19 | TC-014: Documentation completeness review |
| FR-015 Distinguish advertised and estimated salary | US-003 | T13, T15 | TC-015: Verify salary source labels and estimate gate |
| FR-016 Do not persist skill input | US-008 | T14, T17, T18 | TC-016: Inspect storage, logs, and network behavior |
| FR-017 Provide loading, empty, unavailable, and error states | US-002, US-003, US-009 | T15, T16, T17, T18 | TC-017: Exercise each interface state |
| FR-018 Show skill co-occurrence conditionally | US-007 | T06, T07, T11, T16 | TC-018: Verify evidence counts and quality gate |
| NFR-001 Performance | All relevant stories | T14–T18 | NTC-001: Load test against the agreed target |
| NFR-002 Reliability | US-001–US-013 | T18, T19 | NTC-002: Exercise database and model failures |
| NFR-003 Data integrity | US-001–US-013 | T03–T08, T18 | NTC-003: Reconcile data and displayed metrics |
| NFR-004 Security | All API-facing stories | T14, T18 | NTC-004: Security and configuration review |
| NFR-005 Privacy | US-008–US-010 | T17, T18 | NTC-005: Confirm skill input is not retained |
| NFR-006 Accessibility | US-001–US-013 | T17, T18 | NTC-006: Accessibility checks on critical flows |
| NFR-008 Localization | US-012 | T17, T18 | NTC-007: English/Arabic localization review |
| NFR-012 Data provenance | US-001, US-003, US-005, US-013 | T01, T08, T15, T16 | NTC-008: Verify source and sample-size context |

## Maintenance Rule

When a requirement changes, update its linked story, task, verification, and status. Remove or revise placeholder test identifiers when the actual test suite is designed. No requirement should be marked complete solely because a page or model exists.
