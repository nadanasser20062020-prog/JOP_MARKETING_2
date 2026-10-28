# Use Cases and User Flows

## Actors

- **Visitor:** Uses the public website without an account.
- **Project team member:** Maintains data, resources, definitions, analyses, and application releases through the repository and database tools.
- **External provider:** Hosts an original job advertisement or learning resource linked from the application.

No authenticated user or administration role is required for the initial release.

## UC-01 — Explore the Market Overview

**Primary actor:** Visitor
**Preconditions:** The application is available and summary data has been loaded.

**Main flow**
1. The visitor opens the home page.
2. The system displays supported sample-level indicators and the available market/date coverage.
3. The visitor selects a route to job search, market comparison, skill exploration, or matching.

**Alternate flows**
- If summary data is unavailable, the system explains that the analysis is temporarily unavailable.
- If a field has no coverage, the system marks it unavailable rather than displaying zero.

**Postcondition:** The visitor can navigate to a relevant exploration flow.

## UC-02 — Search and Filter Job Advertisements

**Primary actor:** Visitor
**Preconditions:** Job advertisements are available in the database.

**Main flow**
1. The visitor opens the job explorer.
2. The visitor enters a search term and selects supported filters.
3. The system validates the request and returns a paginated result list.
4. The visitor opens an advertisement.

**Alternate flows**
- Invalid or unsupported filter values produce a clear validation message.
- No matching advertisements produce an empty state and an option to revise filters.
- A database failure produces a recoverable error and does not expose internal details.

**Postcondition:** The visitor sees a result list or a clear reason why no results are available.

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
3. The matching service ranks relevant roles or advertisements.
4. The system shows the score definition, matched skills, missing skills, and supporting evidence.
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
