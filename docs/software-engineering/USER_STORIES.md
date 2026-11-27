# User Stories and Acceptance Criteria

Stories are grouped by product capability. Market fields and filters remain conditional on the dataset audit. Each story should be linked to one or more tasks in `docs/PROJECT_PLAN.md` when converted into GitHub Issues.

## Epic E1 — Explore Job Markets

### US-001 — View the market overview
**As a** job seeker, **I want** to see a summary of the collected job-market sample, **so that** I can understand what the platform covers.

**Acceptance criteria**
- The overview shows the number of advertisements and covered markets when known.
- Every displayed metric identifies its sample size or provides a clear route to that information.
- Missing market or date coverage is not presented as zero.

### US-002 — Search and filter job advertisements
**As a** job seeker, **I want** to search and filter advertisements using supported criteria, **so that** I can find relevant opportunities.

**Acceptance criteria**
- Search returns results that match the selected query fields.
- Filters are limited to audited, usable data fields.
- Users can clear filters and see an explicit no-results state.
- Missing values do not cause unrelated records to be misrepresented.

### US-003 — Inspect a job advertisement
**As a** job seeker, **I want** to view the details and source of an advertisement, **so that** I can verify the opportunity independently.

**Acceptance criteria**
- The detail page shows available fields and clearly marks unavailable information.
- Advertised salary is distinguished from any model estimate.
- A valid original-source link is available when it exists in the data.

## Epic E2 — Understand Market Patterns

### US-004 — Explore skill demand
**As a** job seeker, **I want** to see which skills appear frequently by role or market, **so that** I can prioritize learning.

**Acceptance criteria**
- Skill aliases are normalized before aggregation where feasible.
- The view identifies the number of advertisements behind the result.
- The user can distinguish a skill mention from an explicitly required skill when the source permits that distinction.

### US-005 — Compare markets
**As a** job seeker, **I want** to compare selected markets, **so that** I can understand differences in the collected opportunities.

**Acceptance criteria**
- Each side of a comparison uses the same metric definition and compatible units.
- Sample sizes and date coverage are visible.
- Unsupported comparisons are disabled or clearly qualified.

### US-006 — Review trends over time
**As a** job seeker, **I want** to see how advertisement counts or skill demand change over time, **so that** I can explore patterns across the available period.

**Acceptance criteria**
- The trend view is enabled only after date quality and coverage pass the data gate.
- The selected period and date definition are shown.
- Gaps in the source data are not presented as a continuous market trend.

### US-007 — Explore related skills
**As a** job seeker, **I want** to see skills that commonly appear together, **so that** I can understand role profiles and adjacent skills.

**Acceptance criteria**
- The view is based on normalized skill associations.
- It shows the evidence or sample count behind relationships.
- It avoids implying causation or a formal qualification standard.

## Epic E3 — Match Skills and Find Learning Resources

### US-008 — Enter my current skills
**As a** job seeker, **I want** to enter or select skills, **so that** the platform can identify relevant roles.

**Acceptance criteria**
- Inputs are validated and normalized to the skill catalogue where possible.
- The interface explains that submitted skills are used only for the current request and are not saved or logged by the API, consistent with the resolved D-015 privacy baseline.
- The user can remove or edit selected skills before requesting matches.

### US-009 — Review role matches
**As a** job seeker, **I want** to see relevant role profiles and, eventually, individual advertisements ranked against my skills, **so that** I can explore relevant options.

**Acceptance criteria**
- Results are ranked using a documented method.
- Each result explains matched skills and the basis of its score.
- The score is described as skill overlap, not a hiring probability.

**Current implementation status:** `/api/v1/matches` ranks aggregate exact-title role profiles with Jaccard; it does not score individual advertisements. Individual-ad ranking and the user interface remain unimplemented.

### US-010 — Identify skill gaps
**As a** job seeker, **I want** to see skills that are common in relevant advertisements but absent from my input, **so that** I can plan what to learn.

**Acceptance criteria**
- Missing skills are linked to evidence from the relevant role or advertisement sample.
- The interface does not claim that every missing skill is mandatory.
- Users can navigate from a gap to learning resources when available.

### US-011 — Open a free learning resource
**As a** job seeker, **I want** to find learning resources for a skill gap, **so that** I can take a practical next step.

**Acceptance criteria**
- Each resource identifies its skill, provider, language, and access status.
- Free status has a recorded verification date, and only `cost_status=free_verified` is labelled free.
- `some_free_options`, `conditional_or_mixed`, and `cost_unverified` are not presented as verified-free recommendations; their access caveats remain visible.

## Epic E4 — Use the Product in My Language

### US-012 — Switch between English and Arabic
**As a** user, **I want** to use the interface in English or Arabic, **so that** I can understand the product comfortably.

**Acceptance criteria**
- All key navigation, form labels, errors, and empty states are translated.
- Arabic uses correct right-to-left layout; English uses left-to-right layout.
- Numbers, URLs, and original job titles remain readable in both languages.

## Epic E5 — Verify the Evidence

### US-013 — Understand a result's source and limitations
**As a** user or reviewer, **I want** to understand how a result was produced, **so that** I can judge its relevance and limitations.

**Acceptance criteria**
- A methodology page describes sources, cleaning, metric definitions, and model methods.
- Market results identify available sample size, date coverage, and missing fields.
- The product distinguishes observed advertisement information from model output.

## Epic E6 — Analyze Roles and Explore Interactive Markets

### US-014 — Analyze a role across countries
**As a** job seeker, **I want** to search for a job title and see its country distribution, skills, and comparable salaries, **so that** I can understand the role before opening individual advertisements.

**Acceptance criteria**
- Selecting a normalized role opens its analysis view first, not an advertisement list.
- The country view shows record counts and shares with the denominator defined.
- Skills are shown for the role overall and by country where data supports the comparison.
- Average salary appears only for comparable disclosed values and is accompanied by median, sample count, currency, and pay period.
- Related advertisements are available through a secondary link or tab.

### US-015 — Explore the interactive market Overview
**As a** job seeker, **I want** a simple visual overview of countries, jobs, and skills, **so that** I can understand the collected market at a glance.

**Acceptance criteria**
- The intended Overview contains archive-scope KPI cards, a Top 10 reviewed-skill chart, and an Arab-versus-other-represented-markets comparison restricted to `merged_tech_jobs`.
- Show represented country labels and counts in an accessible table; a map is conditional on a reviewed country-to-geometry mapping and must not imply global coverage.
- The current backend supports the underlying aggregates; the frontend and chart interactions are not implemented.
- Hover/tap exposes chart details; selecting a country or chart value filters related visualizations where appropriate.
- Important chart details are also available by keyboard and in an accessible text/table form.
- The page uses progressive disclosure and does not become crowded with repeated numbers or text.
