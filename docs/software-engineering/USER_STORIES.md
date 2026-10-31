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
- If the team approves the D-015 privacy baseline, the interface explains that submitted skills are used only for the current request and are not saved in the initial release.
- The user can remove or edit selected skills before requesting matches.

### US-009 — Review role matches
**As a** job seeker, **I want** to see roles and advertisements ranked against my skills, **so that** I can explore relevant options.

**Acceptance criteria**
- Results are ranked using a documented method.
- Each result explains matched skills and the basis of its score.
- The score is described as skill coverage, not a hiring probability.

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
