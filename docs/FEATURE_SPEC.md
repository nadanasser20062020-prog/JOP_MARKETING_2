# Feature Specification

This document defines intended user-facing scope, not proof that a page is implemented. A feature that depends on a missing or unreliable field must be implemented only after the data audit confirms that the requirement is supported. Current implementation status and remaining frontend work are tracked in [`PROJECT_PLAN.md`](PROJECT_PLAN.md).

## Target Users

- Engineers exploring opportunities in a specific job market.
- People who know some of their skills and want to discover relevant roles and development areas.
- The project team presenting documented analysis to reviewers.

## 1. Overview Dashboard (Default Home Page)

The Overview is the default landing page. Its primary purpose is market and role analysis; individual job advertisements are secondary.

- **Country distribution:** Show represented country labels and job-record counts in an accessible list/table. Add a geographic map only after a reviewed country-name-to-geometry mapping is available; the source has no standard ISO code. Describe the archive sample, not a complete global job market.
- **KPI cards:** Show Total Jobs, Total Skills, and Total Countries. Total Jobs counts included job-ad records; Total Skills counts distinct normalized skills in the analytical scope, not job-skill assignments; Total Countries counts distinct normalized country values represented in the data.
- **Top 10 In-Demand Skills:** Use a horizontal bar chart. Count job records associated with each normalized skill; show the count and within-sample share in the chart details.
- **Arab vs other represented markets:** Compare the most frequent skills with within-group shares and counts, using `merged_tech_jobs` only because it contains both groups. The second cohort is not a global market; list unrepresented Arab-country labels as coverage gaps, not zeros.
- Charts support hover tooltips and click-to-filter, with touch and keyboard alternatives. Selecting a map marker or chart value updates related panels where appropriate.
- Keep the page uncluttered: use a small number of clear sections, consistent labels, and on-demand details rather than repeating the same figures or filling the page with text.
- Define the denominator, sample size, period, and metric for every percentage or chart. Results describe the collected data only.

## 2. Role Search and Role Analysis

- Searching for or selecting a normalized job title opens a role-analysis page, not an advertisement list.
- For the selected role, show the countries where it appears most often and the count and share of role records in each country. State the denominator used for the share.
- Show the skills associated with the role overall and by country, using interactive charts that allow users to filter by market.
- Show the arithmetic average salary by country when disclosed values are sufficiently comparable. Include the median, salary-record count, currency, and pay period alongside the average. Do not mix incompatible currencies or periods, use research-derived amounts as employer offers, or infer missing salaries.
- Individual advertisements are an optional secondary view. A small “Related advertisements” link or tab opens the Job Explorer filtered to the selected role; the advertisement list is not the default result of role search.
- The secondary Job Explorer may search and filter advertisements using audited fields such as title, skills, country/city, company, work arrangement, experience, and comparable salary. Show unavailable values as unavailable; do not display zero or invent values.
- Saving jobs, saving searches, and alerts for new jobs are excluded from the current scope.

## 3. Job Detail Page

- Show only information available in the advertisement: title, description, employer, location, work arrangement, skills, qualifications, salary, and dates where present.
- Provide the original source link and collection date where available.
- Distinguish an advertised salary from a model estimate. A regression estimate may appear only after passing the ML quality gate and must be clearly identified as an estimate, not a guarantee.

## 4. Job and Skill Insights

- Explore frequently occurring skills overall and by role or country.
- Show skills that commonly appear together or are associated with similar role profiles after normalizing aliases and controlling for duplicate advertisements.
- Show salary distributions and work arrangements by role or market only when sample coverage is adequate.
- Use comparable definitions, units, and periods for market comparisons, and show the number of advertisements for each comparison.

## 5. Market Comparison and Time Trends

- Compare two or more countries across available roles, skills, salaries, and work arrangements.
- Show changes over time only when advertisement dates are reliable and cover a meaningful period.
- Treat missing country or date values as missing; do not infer them.

## 6. Skill Matching and Career Exploration

- Let users enter skills or select them from a normalized list. Allow optional country or work-arrangement preferences when the data supports them.
- The current API ranks aggregate exact-title role profiles by deterministic Jaccard and explains matched, missing, and user-only skills. It does not score individual job advertisements; per-ad ranking remains a separate unimplemented requirement.
- Explain how the match score is calculated; it represents observed skill overlap, not the probability of being hired or complete suitability.
- Rank missing skills using evidence from the relevant advertisements. Do not call a skill required unless the sample supports that claim.
- Allow users to open the recommended job detail page and original advertisement.

## 7. Free Learning Resources

- Link each resource to a specific skill and display its title, provider, language, level, and URL.
- Record when the access/cost status was last checked. Only resources marked `free_verified` may be presented as free; `some_free_options`, `conditional_or_mixed`, and `cost_unverified` must be clearly caveated and excluded from free-only recommendations until course-level terms are confirmed.
- Prefer official documentation and verifiable learning resources, and review links periodically.

## 8. Language and Usability

- Support English and Arabic, including correct right-to-left layout for Arabic and correct handling of numbers and links.
- Normalize role and skill names internally while retaining the original wording from advertisements where useful.
- Support mobile and desktop layouts with clear search, filters, and charts.

## 9. Transparency and Data Quality

- Provide a methodology page describing data sources, cleaning, metric definitions, analyses, models, and limitations.
- Show sample size, date coverage, and data coverage for important results.
- Explain that the dataset consists of collected job advertisements that may be duplicated, expired, or missing salary information; results therefore describe the collected sample only.

## Explicitly Out of Scope

- Saving jobs.
- Saving searches.
- Notifications or alerts for newly available jobs.
- Any claim that a skill match guarantees employment.
