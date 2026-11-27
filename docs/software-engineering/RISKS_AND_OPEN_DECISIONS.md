# Risks and Open Decisions

This register captures risks and decisions that affect the software design. Review it after the dataset audit and at each major project milestone.

## Risk Register

| ID | Risk | Impact | Mitigation or response | Status |
|---|---|---|---|---|
| R-001 | New or changed source files may have columns or quality issues not covered by the current audit | Imports, features, schema, and models may not be feasible for a new refresh | Re-audit each changed source, compare its data dictionary, and update migrations only for reviewed schema changes | Open for future refreshes |
| R-002 | Salary data may be sparse or incomparable across currencies and pay periods | Salary comparisons or regression may be misleading | Measure coverage, define a normalization policy, and use a no-go gate for unreliable estimates | Open |
| R-003 | Job advertisements may be duplicated, expired, or reposted | Counts and trends may be inflated | Define a documented deduplication policy and distinguish posting from collection dates | Open |
| R-004 | Collected markets may be biased or unrepresentative | Users may interpret a partial sample as a complete labor market | Show sample sizes, source coverage, dates, and limitations on relevant views | Open |
| R-005 | Source terms may restrict reuse or redistribution | Public deployment may violate source requirements | Review source terms and permitted use before publication | Open |
| R-006 | Skill extraction and normalization may be noisy | Skill counts and recommendations may be inaccurate | Audit a representative sample, retain original text, and review the skill taxonomy | Open |
| R-007 | Classification labels may be absent or inconsistent | Classification metrics may not be meaningful | Create a reviewed labelled sample or document that the model is not feasible | Open |
| R-008 | Language variants and spelling differences may fragment skills and titles | Search, comparisons, and matching may miss relevant records | Maintain reviewed aliases and test English/Arabic normalization where applicable | Open |
| R-009 | Learning-resource access status can change | Users may follow resources that are no longer free or available | Record verification dates and establish a periodic review owner | Open |
| R-010 | External job links may expire | Users may not be able to verify an advertisement | Show collection dates and avoid promising external-link availability | Open |
| R-011 | Frontend framework/chart library are unselected; full-data Vercel packaging is not verified | Frontend and public hosting scope may change; Vercel cannot read a developer's local file | Keep local full-data mode as the supported demonstration; measure a packaged database before promising Vercel full-data deployment | Open |
| R-012 | User-entered skills could be exposed in logs or storage | User privacy could be compromised | Do not persist skill inputs; exclude request bodies from logs; verify with tests | Open |
| R-013 | Data volume and query patterns are not measured | Common queries may be slow at demonstration time | Profile data size, benchmark queries, and add indexes only when measured | Open |
| R-014 | Model results may perform unevenly across markets | Recommendations may be less useful for underrepresented countries | Report market coverage and evaluate errors by market where sample sizes allow | Open |

## Open Decisions

| ID | Decision | Options or decision criteria | Required before |
|---|---|---|---|
| D-001 | Frontend framework and chart library | Frontend team familiarity, integration needs, accessibility, and RTL support; backend is implemented in Node.js 22 | Frontend implementation |
| D-002 | Full-data application hosting | Local SQLite remains the supported full-data mode; Vercel handler exists, but Vercel cannot access a developer's local file and full-database packaging/limits must be verified | Before public full-data deployment |
| D-003 | Database engine and storage location | Resolved: local SQLite only; default file `data/processed/job_market.sqlite3`; no external database service or connection URL | Complete; keep local-file behavior in future changes |
| D-004 | Initial market and role coverage | Select based on actual records and project objectives | Final feature scope |
| D-005 | Supported search filters | Include only reliable audited fields | API and UI implementation |
| D-006 | Salary normalization and exchange-rate policy | Decide whether conversion is needed and how historical rates are handled | Salary analysis and regression |
| D-007 | Job-family taxonomy and labelling method | Existing field, reviewed manual labels, or no classifier | Classification experiment |
| D-008 | Skill matching score and evidence threshold | Resolved for current API: deterministic Jaccard overlap ranks aggregate exact-title role profiles and returns matched/missing skills plus record evidence; it is not a hiring probability or per-ad ranking | Fixture and selected full-database smoke checks pass; direct individual-ad scoring and broader relevance evaluation remain unimplemented |
| D-009 | Online ML runtime | Resolved: Node.js-only online API; a separate positive-evidence Naive Bayes model ranks exact observed titles for limited-scope review. Python trains/evaluates offline; no Python subprocess or separate ML server. The model is not production-approved. | Implemented for limited-scope review; any new task or broader/production use needs renewed approval and evaluation |
| D-010 | Data refresh and advertisement-retention policy | One-time snapshot or periodic manual refresh; source terms apply | Operations and methodology |
| D-011 | Resource-review owner and review frequency | Team owner and feasible cadence | Resource catalogue release |
| D-012 | Local performance and availability targets | Agree after measuring normalized data size and demonstration-machine capacity | Test and release plan |
| D-013 | Exact locale and translation policy | English/Arabic labels, original title treatment, date/currency formats | UX implementation |
| D-014 | Public-data licensing and attribution | Review source terms and redistribution requirements | Public deployment |
| D-015 | Retention of user-entered skills | Current API implements the privacy-preserving baseline: process in memory and do not persist/log. Any future retention requires explicit review and a scope change. | Resolved for the current API |

## Decision Record Rule

Once the team resolves an open decision that materially affects architecture or scope, create an Architecture Decision Record in `adr/`, link it here, and update affected requirements and plans.
