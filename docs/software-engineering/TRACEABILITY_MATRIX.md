# Requirements Traceability Matrix

This matrix connects SRS requirements to user stories, project tasks, and planned verification. Test identifiers are placeholders; they do not imply that implementation tests already exist. Requirements marked Proposed or Conditional remain subject to their approval or data-quality gate.

## Functional Requirements

| Requirement | User story or process | Project task(s) | Planned verification |
|---|---|---|---|
| FR-001 Market overview | US-001 | T06, T07, T08, T16 | TC-001: Reconcile overview metrics and sample sizes |
| FR-002 Search advertisements | US-002 | T14, T15 | TC-002: Search by supported fields |
| FR-003 Filter advertisements | US-002 | T01, T02, T14, T15 | TC-003: Validate filters against the data dictionary |
| FR-004 View advertisement details | US-003 | T14, T15 | TC-004: Render available and missing fields |
| FR-005 Link to original source | US-003 | T01, T03, T15 | TC-005: Validate source-link behavior |
| FR-006 Explore skill demand | US-004 | T03, T06, T07, T09, T16 | TC-006: Reconcile normalized skill counts |
| FR-007 Compare markets | US-005 | T06, T08, T16 | TC-007: Verify units, filters, and sample-size context |
| FR-008 Show time trends conditionally | US-006 | T01, T06, T07, T16 | TC-008: Confirm date-quality gate and period labels |
| FR-009 Accept skill input | US-008 | T10, T17 | TC-009: Validate valid, empty, unknown, and oversized inputs |
| FR-010 Rank and explain matches | US-009 | T10, T17 | TC-010: Review ranking and explanations against test cases |
| FR-011 Identify skill gaps | US-010 | T09, T10, T17 | TC-011: Verify evidence and gap ordering |
| FR-012 Provide reviewed resources | US-011 | T09, T17 | TC-012: Audit links and free-access verification dates |
| FR-013 Support English and Arabic | US-012 | T17, T18 | TC-013: Review translations and RTL behavior |
| FR-014 Explain methodology and limitations | US-013 | T08, T19 | TC-014: Review documentation completeness |
| FR-015 Distinguish advertised and estimated salary | US-003 | T13, T15 | TC-015: Verify salary labels and estimate gate |
| FR-016 Process skill input transiently | US-008 | T14, T17, T18 | TC-016: Confirm D-015 decision and review storage/log behavior |
| FR-017 Provide loading, empty, unavailable, and error states | US-002, US-003, US-009 | T15–T18 | TC-017: Exercise each interface state |
| FR-018 Show skill co-occurrence conditionally | US-007 | T06, T07, T11, T16 | TC-018: Verify evidence counts and quality gate |
| FR-019 Preserve raw sources and provenance | Data pipeline process | T01, T03, T05 | TC-019: Verify source files remain unchanged and transformations are traceable |
| FR-020 Clean to separate outputs without silent data loss | Data pipeline process | T03 | TC-020: Reconcile before/after counts and rejected records |
| FR-021 Validate database loads | Data-loading process | T04, T05 | TC-021: Check schema, counts, keys, and relationships |
| FR-022 Reproduce SQL and Python analysis | US-013 / analysis process | T06–T08 | TC-022: Re-run analysis and verify documented outputs |
| FR-023 Evaluate job-ad clustering conditionally | ML process | T11 | TC-023: Review metrics, stability, and representative clusters |
| FR-024 Evaluate job-family classification conditionally | ML process | T12 | TC-024: Verify labels, per-class metrics, and error analysis |
| FR-025 Evaluate salary regression conditionally | ML process | T13 | TC-025: Verify salary comparability, baseline, and held-out metrics |
| FR-026 Block models that fail quality gates | US-009, US-013 | T11–T13, T18 | TC-026: Confirm rejected models are not exposed through API/UI |
| FR-027 Show unsupported data as unavailable | US-001, US-002, US-005 | T02, T15, T16, T18 | TC-027: Test missing and unsupported fields |
| FR-028 Provide documented backend operations | US-001–US-013 | T14 | TC-028: Verify API contract and integration behavior |

## Non-Functional Requirements

| Requirement | Related task(s) | Planned verification |
|---|---|---|
| NFR-001 Performance | T14–T18 | NTC-001: Load test against the approved target |
| NFR-002 Reliability | T18, T19 | NTC-002: Exercise database and model failures |
| NFR-003 Data integrity | T03–T08, T18 | NTC-003: Reconcile stored data, queries, and displayed metrics |
| NFR-004 Security | T14, T18, T19 | NTC-004: Security and configuration review |
| NFR-005 Privacy | T14, T17, T18 | NTC-005: Confirm the approved D-015 behavior and log handling |
| NFR-006 Accessibility | T17, T18 | NTC-006: Review critical flows against the agreed WCAG target |
| NFR-007 Usability | T15–T18 | NTC-007: User walkthrough and acceptance review |
| NFR-008 Localization | T17, T18 | NTC-008: English/Arabic and RTL/LTR review |
| NFR-009 Maintainability | T03–T14, T18 | NTC-009: Review reproducibility and documentation consistency |
| NFR-010 Compatibility | T18, T19 | NTC-010: Smoke test supported desktop/mobile browsers |
| NFR-011 Observability | T14, T18, T19 | NTC-011: Verify service health and safe diagnostic logs |
| NFR-012 Data provenance | T01, T08, T15, T16 | NTC-012: Verify source, sample-size, and date context |
| NFR-013 Recoverability | T18, T19 | NTC-013: Review and exercise rollback/recovery steps |
| NFR-014 Portability and reproducibility | T03, T05, T07, T19 | NTC-014: Re-run workflows in a clean environment |
| NFR-015 Legal and ethical use | T01, T19 | NTC-015: Review attribution, source terms, and data-use approval |

## Maintenance Rule

When a requirement changes, update its linked story or process, project task, verification, and status. Replace placeholder test IDs when the actual test suite is designed. No requirement should be marked complete solely because a page or model exists.
