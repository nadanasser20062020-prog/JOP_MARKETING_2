# Use Cases and User Flows

These are intended flows, not implemented frontend screens. The current checkout has no frontend entry point; API capabilities and remaining gaps are tracked in the project plan and API specification.

## Actors

- **Visitor:** Uses the public website without an account.
- **Project team member:** Maintains data, resources, definitions, analyses, and application releases through the repository and local SQLite tools.
- **External provider:** Hosts an original job advertisement or learning resource linked from the application.

No authenticated user or administration role is required for the initial release.

## UC-01 — Explore the Interactive Market Overview

**Primary actor:** Visitor
**Preconditions:** The application is available and the local SQLite file contains the selected dataset and supported overview aggregates.

**Main flow**
1. The visitor opens the default Overview page.
2. The system displays archive-scope KPIs, the Top 10 reviewed skills, an accessible country-label/count table, and Arab-versus-other-represented-market skill shares restricted to `merged_tech_jobs`; a map is conditional on reviewed geospatial labels.
3. The visitor hovers, taps, or keyboard-focuses a visual to read its count, share, and definition.
4. The visitor selects a country or chart value; related overview charts update where appropriate.
5. The visitor searches for a role to open its analysis view, or navigates to another product section.

**Alternate flows**
- If a metric or comparison lacks supported data, it is omitted or shown as unavailable rather than fabricated.
- If summary data is unavailable, the system shows a recoverable empty/service state.

**Postcondition:** The visitor has a concise visual overview and can continue to role analysis or another exploration flow.

## UC-02 — Search Related Job Advertisements

**Primary actor:** Visitor
**Preconditions:** Job advertisements are available; the visitor chooses the secondary Related Advertisements view or navigates to it directly.

**Main flow**
1. The visitor opens the related-advertisement explorer, optionally pre-filtered to a role.
2. The visitor enters a search term and selects supported filters.
3. The system validates the request and returns a paginated result list.
4. The visitor opens an advertisement.

A role-title search from the Overview opens role analysis first; it does not default to this advertisement list.

**Alternate flows**
- Invalid or unsupported filter values produce a clear validation message.
- No matching advertisements produce an empty state and an option to revise filters.
- If the local SQLite file is unavailable, the system produces a recoverable error and does not expose internal details or attempt a network fallback.

**Postcondition:** The visitor sees an optional related-ad list or a clear reason why no results are available.

## UC-03 — View an Advertisement

**Primary actor:** Visitor
**Preconditions:** A valid advertisement identifier exists.

**Main flow**
1. The visitor selects an advertisement.
2. The system displays available details, skill information, dates, and source metadata.
3. The visitor follows the original source link when one is available.

**Alternate flows**
- An unknown identifier returns a not-found state.
- Missing company, salary, date, or location fields are shown as unavailable.
- An invalid or expired source link is identified without implying that the listing is still active.

**Postcondition:** The visitor can review the stored advertisement information and, when possible, verify it at the source.

## UC-04 — Compare Markets

**Primary actor:** Visitor
**Preconditions:** Comparable market data is available for the selected countries.

**Main flow**
1. The visitor selects two or more markets and one supported comparison metric.
2. The system applies the same metric definition and compatible units to each market.
3. The system displays results, sample sizes, and available date coverage.

**Alternate flows**
- A selected market lacks sufficient records; the system explains the limitation.
- Salary units or time periods are incompatible; the system prevents the comparison or clearly qualifies it.

**Postcondition:** The visitor can compare evidence from the collected sample without mistaking unequal coverage for a complete market comparison.

## UC-05 — Match User Skills to Roles

**Primary actor:** Visitor
**Preconditions:** A normalized skill catalogue and job-skill associations are available.

**Main flow**
1. The visitor enters or selects skills and optional supported preferences.
2. The system validates and normalizes the input for the current request.
3. The current matching service ranks aggregate exact-title role profiles using deterministic Jaccard overlap; it does not score individual advertisements.
4. The system shows the score definition, matched skills, missing skills, user-only skills, and supporting record evidence. Per-ad ranking remains unimplemented; `/roles/{roleId}/ads` is a separate, unscored list.
5. The visitor opens a result or a related learning resource.

**Alternate flows**
- No valid skills are provided; the system requests input and displays examples.
- Some skills cannot be normalized; the system asks the user to confirm or keeps them as unrecognized input.
- No relevant matches exist; the system explains the result and suggests broadening the input or preferences.
- The matching service is unavailable; the system does not show partial or stale results as current.

**Postcondition:** The user receives an explainable result. Submitted skills are not persisted in the initial release.

## UC-06 — Find a Learning Resource

**Primary actor:** Visitor
**Preconditions:** A relevant resource has been reviewed and linked to a skill.

**Main flow**
1. The visitor opens a skill gap or skill detail.
2. The system lists relevant resources, languages, levels, providers, and verified access status.
3. The visitor opens an external resource.

**Alternate flows**
- No reviewed resource exists; the system states that no resource is currently listed.
- A resource link has failed verification; the team removes or flags it during maintenance.

**Postcondition:** The visitor can access an appropriately described external learning resource.

## UC-07 — Review Methodology and Limitations

**Primary actor:** Visitor or reviewer

**Main flow**
1. The actor opens the methodology page.
2. The system describes data coverage, definitions, cleaning, analytical methods, model evaluation, and limitations.
3. The actor follows references to relevant source or project documentation where available.

**Postcondition:** The actor can interpret results within the evidence and limitations of the dataset.

## UC-08 — Analyze a Selected Job Role

**Primary actor:** Visitor
**Preconditions:** A normalized role can be resolved and the required market aggregates are available.

**Main flow**
1. The visitor searches for and selects a job title from the Overview.
2. The system opens a role-analysis page rather than an advertisement list.
3. The system shows the role's country counts and shares, with the share denominator defined.
4. The visitor explores skills for the role overall or filters them by country.
5. Where salary data is comparable, the system shows the arithmetic average alongside the median, currency, pay period, and supporting record count.
6. The visitor may open a secondary Related Advertisements view filtered to the selected role.

**Alternate flows**
- If no normalized role matches, the system offers available title suggestions or a clear no-results state.
- If a country, skill, or salary metric lacks adequate comparable data, the system omits that comparison or identifies the value as unavailable; it does not infer a value.
- If the related-ad list is empty, the role analysis remains available.

**Postcondition:** The visitor understands the role's observed market distribution and can optionally inspect individual source advertisements.
