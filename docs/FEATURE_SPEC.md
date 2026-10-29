# Feature Specification

This document defines the user-facing product scope. A feature that depends on a missing or unreliable field must be implemented only after the data audit confirms that the requirement is supported.

## Target Users

- Engineers exploring opportunities in a specific job market.
- People who know some of their skills and want to discover relevant roles and development areas.
- The project team presenting documented analysis to reviewers.

## 1. Home Page and Market Dashboard

- Summarize the available advertisement sample: record count, covered markets, most common roles and skills, and work-arrangement distribution where available.
- Show the latest collection or update date when documented.
- Display the number of records behind each metric; distinguish advertisement counts from unique employers or roles.
- Every chart must state its unit, time period, and source of calculation. Results must not be presented as complete facts about a market beyond the collected sample.

## 2. Job Explorer

- Search and filter advertisements using verified fields, such as title, skills, country/city, company, work arrangement, experience, and salary.
- Sort results using understandable criteria such as recency or skill relevance.
- Show unavailable values as unavailable; do not display zero or an invented value.
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
- Rank relevant jobs or role profiles and explain matched and missing skills.
- Explain how the match score is calculated; it represents skill coverage, not the probability of being hired.
- Rank missing skills using evidence from the relevant advertisements. Do not call a skill required unless the sample supports that claim.
- Allow users to open the recommended job detail page and original advertisement.

## 7. Free Learning Resources

- Link each resource to a specific skill and display its title, provider, language, level, and URL.
- Record when the free-access status was last checked. If only part of a resource is free, state that clearly.
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
