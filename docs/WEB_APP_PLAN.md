# Web Application Plan and Data Flow

## Purpose

Turn database records and analytical findings into a simple experience for engineers: explore job markets, understand roles and required skills, and identify relevant learning opportunities.

## Implemented API Flow and Planned Frontend

1. Clean job-advertisement data and load it into the local SQLite file with the documented Python migrations/import scripts.
2. Run the documented 19-query Python/SQL analysis and offline experiments. The current report includes role-country distribution, role skills, role-country skill shares, and salary-comparability counts; unsupported salary averages remain disabled.
3. The Node.js 22 backend opens the local SQLite file read-only and handles search, filtering, analytics, resources, deterministic Jaccard matching, and a separately identified in-process Naive Bayes ranking of exact observed title strings. Python training is offline only; the title model is served for limited-scope review, not production occupational classification.
4. A future frontend will present the versioned JSON API responses, charts, details, and evidence/limitations. No frontend entry point has been found in the current repository; frontend integration is not complete.

The browser must not access SQLite directly or receive the local database path. No external database service or connection URL is used. The backend runtime is selected and implemented; the frontend framework and charting library remain open. Vercel-compatible routing is configured, but a hosted Vercel function cannot access a developer's computer and needs the database included in its deployment bundle.

## Pages and User Flow

### 1. Overview (Default Home Page)

- Open on a clean market overview rather than a list of individual advertisements.
- Show represented country labels and job-record counts in an accessible table; only add a map after a reviewed country-name-to-geometry mapping exists. Selecting a country can filter other overview views where the API supports it.
- Show KPI cards for Total Jobs, distinct normalized Total Skills, and Total Countries.
- Show a Top 10 reviewed-skill horizontal bar chart and an Arab-versus-other-represented-markets comparison using within-group shares, with counts available on hover/tap. The comparison is fixed to `merged_tech_jobs`; it is not a global-market estimate.
- Keep the four requested visual sections distinct and uncluttered. Charts support hover, tap, and keyboard interaction; selecting a value can cross-filter related panels.

### 2. Role Search and Analysis

- Search or select a normalized job title. Selecting a role opens its analysis page, not a list of advertisements.
- Show the role's country distribution as counts and shares with a stated denominator, skills associated with the role overall and by country, and interactive comparisons between supported markets.
- Show average salary by country only when the source values are comparable. Pair the average with median, record count, currency, and pay period; never combine incompatible units or infer missing salaries.
- Provide a small secondary “Related advertisements” link or tab that opens the advertisement explorer filtered to the selected role.

### 3. Related Job Advertisements

- This is an optional supporting view, not the main result of a role search.
- Search and filter using fields supported by the dataset; show concise records with title, employer, location, skills, and salary where available.
- Provide clear loading, no-results, and missing-value states.

### 4. Job Details

- Present collected advertisement details, skills, dates, and source information.
- Distinguish salary stated in the advertisement from any separately evaluated model estimate.
- Link to the original advertisement when the URL is available and permitted for use.

### 5. Market Comparison and Skill Explorer

- Visualize supported role, skill, work-arrangement, and salary indicators and allow comparison of markets using consistent definitions.
- Show time trends only when dates are sufficiently reliable; display the sample size and metric definition for every chart.
- Show in-demand skills by role or market and explore skills that commonly appear together.

### 6. Skill Matching and Learning Resources

- Accept user-entered skills and optional market or work-arrangement preferences.
- The current API resolves reviewed skills and ranks aggregated exact-title role profiles by deterministic Jaccard overlap, returning matched, missing, and user-only skills. It does **not** currently score individual job-ad records; the separate `/roles/{roleId}/ads` route lists ads for a selected role without a per-ad match score. Do not present this as an implemented per-ad ranking feature.
- A separate optional title suggestion endpoint uses a limited-scope, uncalibrated Naive Bayes model; label it as an experimental exact-title ranking, not a probability or occupational classifier.
- Link missing skills to resources; only describe a course as free when that specific course is verified as free.

No frontend entry point exists in this checkout, so these page behaviors are requirements/wireframes rather than a built or browser-verified UI.

### 7. Methodology

- Explain data sources and dates, cleaning, metric definitions, analytical methods, models, and limitations.

## English and Arabic Support

- Provide English and Arabic interface text, including navigation and empty/error states.
- Support correct RTL layout in Arabic and LTR layout in English without reversing links or numbers.
- Preserve the original job title while using normalized titles for comparisons where appropriate.

## Suggested Frontend Completion Sequence

1. Confirm user flows, page wireframes, and exact field labels against the API contract.
2. Select the frontend framework and chart library with accessibility/RTL support.
3. Integrate the existing Node.js API using relative `/api/v1` routes and a development proxy.
4. Build the job explorer and job-detail experience.
5. Build the market dashboard, comparison, and skill explorer.
6. Integrate role analysis, deterministic Jaccard matching, the separately labelled limited-scope Naive Bayes title ranking, and learning resources with their evidence/limitation text.
7. Add localization, missing-data/error states, keyboard/touch interactions, and mobile layouts.
8. Reconcile displayed metrics against the full local SQLite database and test data accuracy, links, privacy, and usability.

## General Acceptance Criteria

- Every displayed metric can be traced to a documented query or analysis result.
- Filters use supported dataset values and handle missing fields safely.
- Each displayed job links to its source when the source is available.
- Missing information is shown clearly and is not replaced with fabricated values.
- Matching results are explainable and do not claim to guarantee employment.
- The application exposes neither direct SQLite access nor the local database path to the browser.
- Saving jobs, saving searches, and new-job alerts remain out of scope.
