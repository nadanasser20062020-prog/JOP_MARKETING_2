# Risks and Open Decisions

This register captures risks and decisions that affect the software design. Review it after the dataset audit and at each major project milestone.

## Risk Register

| ID | Risk | Impact | Mitigation or response | Status |
|---|---|---|---|---|
| R-001 | Actual dataset columns and quality are unknown | Planned features, schema, and models may not be feasible | Complete T01 and map each feature to verified fields before implementation | Open |
| R-002 | Salary data may be sparse or incomparable across currencies and pay periods | Salary comparisons or regression may be misleading | Measure coverage, define a normalization policy, and use a no-go gate for unreliable estimates | Open |
| R-003 | Job advertisements may be duplicated, expired, or reposted | Counts and trends may be inflated | Define a documented deduplication policy and distinguish posting from collection dates | Open |
| R-004 | Collected markets may be biased or unrepresentative | Users may interpret a partial sample as a complete labor market | Show sample sizes, source coverage, dates, and limitations on relevant views | Open |
| R-005 | Source terms may restrict reuse or redistribution | Public deployment may violate source requirements | Review source terms and permitted use before publication | Open |
| R-006 | Skill extraction and normalization may be noisy | Skill counts and recommendations may be inaccurate | Audit a representative sample, retain original text, and review the skill taxonomy | Open |
| R-007 | Classification labels may be absent or inconsistent | Classification metrics may not be meaningful | Create a reviewed labelled sample or document that the model is not feasible | Open |
| R-008 | Language variants and spelling differences may fragment skills and titles | Search, comparisons, and matching may miss relevant records | Maintain reviewed aliases and test English/Arabic normalization where applicable | Open |
| R-009 | Learning-resource access status can change | Users may follow resources that are no longer free or available | Record verification dates and establish a periodic review owner | Open |
| R-010 | External job links may expire | Users may not be able to verify an advertisement | Show collection dates and avoid promising external-link availability | Open |
| R-011 | Technology stack and deployment platform are not selected | Architecture and delivery estimates may change | Review team capabilities and deployment requirements before implementation | Open |
| R-012 | User-entered skills could be exposed in logs or storage | User privacy could be compromised | Do not persist skill inputs; exclude request bodies from logs; verify with tests | Open |
| R-013 | Data volume and query patterns are not measured | Common queries may be slow at demonstration time | Profile data size, benchmark queries, and add indexes only when measured | Open |
| R-014 | Model results may perform unevenly across markets | Recommendations may be less useful for underrepresented countries | Report market coverage and evaluate errors by market where sample sizes allow | Open |

## Open Decisions

| ID | Decision | Options or decision criteria | Required before |
|---|---|---|---|
| D-001 | Frontend and backend frameworks | Team familiarity, integration needs, deployment support | Implementation |
| D-002 | Hosting platform and environment separation | Cost, student-project access, secrets, database connectivity | Deployment design |
| D-003 | Database provider and plan | PostgreSQL/Neon is under consideration; confirm region, limits, and access | Database implementation |
| D-004 | Initial market and role coverage | Select based on actual records and project objectives | Final feature scope |
| D-005 | Supported search filters | Include only reliable audited fields | API and UI implementation |
| D-006 | Salary normalization and exchange-rate policy | Decide whether conversion is needed and how historical rates are handled | Salary analysis and regression |
| D-007 | Job-family taxonomy and labelling method | Existing field, reviewed manual labels, or no classifier | Classification experiment |
| D-008 | Skill matching score and evidence threshold | Transparent coverage method, tested against reviewed cases | Matching implementation |
| D-009 | Model-serving approach | In-process inference, separate service, or analysis-only output | Architecture and deployment |
| D-010 | Data refresh and advertisement-retention policy | One-time snapshot or periodic manual refresh; source terms apply | Operations and methodology |
| D-011 | Resource-review owner and review frequency | Team owner and feasible cadence | Resource catalogue release |
| D-012 | Performance and availability targets | Agree after measuring dataset size and hosting | Test and release plan |
| D-013 | Exact locale and translation policy | English/Arabic labels, original title treatment, date/currency formats | UX implementation |
| D-014 | Public-data licensing and attribution | Review source terms and redistribution requirements | Public deployment |
| D-015 | Retention of user-entered skills | Recommended default: process in memory for the current request and do not persist; confirm with the team | Matching implementation |

## Decision Record Rule

Once the team resolves an open decision that materially affects architecture or scope, create an Architecture Decision Record in `adr/`, link it here, and update affected requirements and plans.
