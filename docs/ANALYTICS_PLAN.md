# SQL and Python Analytics Plan

The analysis answers specific questions about the **collected job-ad records**, not the labor market as a whole. In the last full-data run, the checksum-verified archive was loaded into the local ignored SQLite file and a reproducible driver executed 19 SQL analyses, including role-by-country counts, eligible skills by exact role and role-country, and a role-country salary-comparability audit. The generated report and CSV tables are in [`analysis/reports/pre_backend/`](../analysis/reports/pre_backend/PRE_BACKEND_ANALYSIS.md). The archive and SQLite file are absent from the current snapshot, so rerunning the analysis requires restoring them. The Node API exposes the supported role/country/skill aggregates; there is no frontend application in this checkout. Use the International 2023 sample for historical aggregates, keep the latest exports as a separate unverified snapshot, and do not use mixed `updated` fields as a time series until their semantics are confirmed. See [`docs/data/DATA_AUDIT.md`](data/DATA_AUDIT.md).

## Analysis Questions

### Data Coverage and Quality

- How many advertisements are available by source, country, and period?
- What proportion of records is missing title, employer, location, date, skills, work arrangement, or salary?
- How many duplicate records exist, and what rule was used to detect them?
- Which languages and time periods are represented, and which markets are underrepresented?

### Roles and Skills

- Which roles or job families appear most frequently in the sample?
- Which skills are most frequent overall and by role or country?
- Which skills commonly appear together?
- Which employers appear most often, distinguishing advertisement counts from unique employers?
- What is the distribution of remote, hybrid, and onsite roles if the field can be normalized reliably?

### Salaries and Time

- How are disclosed salaries distributed by role, country, and experience level?
- What are the median and range, and how many advertisements support each figure?
- How do advertisement counts or skill demand change over time if posting dates are reliable?
- Are there differences in currency or monthly, annual, and hourly pay periods?

## Overview and Role-Analysis Metrics

- The Overview landing page should report Total Jobs as job-ad records, Total Skills as distinct normalized skill concepts in the analytical scope, and Total Countries as distinct normalized country values represented in the selected data.
- The world-map marker size is the number of job-ad records for that country. Country shares use records with a known country as the denominator; expose the count and denominator in chart details.
- The Top 10 skills chart counts job records associated with each normalized skill rather than repeated raw tokens. Show both count and share of records with usable skill data.
- Compare Arab and global skill demand using within-group shares as well as counts. Define the Arab-country list and explicitly state whether “global” includes the Arab group.
- For a selected normalized role, calculate country counts and shares among records for that role with a known country. Show the denominator and make country selections filter the role's skills and salary charts.
- Show the requested arithmetic mean salary per country only for comparable disclosed salary records. Include the median, salary-bearing record count, currency, and pay period; do not combine incompatible currencies or periods, include research-derived estimates as employer offers, or fill missing values.
- Interactive visualizations should expose details on hover, tap, and keyboard focus; selecting a country or chart segment may cross-filter related panels. The Overview should remain sparse, with detailed breakdowns available on the role-analysis page.

**Current salary gate result:** the role-country audit has 58,267 salary-field records across 25,956 exact-title/country pairs; 52 records supply a currency, but zero annual or hourly values have both an explicit currency and matching pay-period fields. The API therefore returns salary-field coverage by country, but no mean or median. Missing salary information is not represented as a zero amount.

## SQL Approach

- Perform database aggregations for counts, groupings by country/role/skill, summary statistics, and date filters.
- Keep analytical queries separate from schema definitions. Document the question and metric definition for each query.
- Validate queries against manually checked samples and compare totals with the database.
- When SQL is executed from Python, keep each query readable and reviewable; open only the configured local SQLite path and keep the database file itself out of source control.

## Python Approach

- **Pandas:** Inspect and transform query results or samples; clean and combine analysis-ready data when needed.
- **NumPy:** Perform numerical calculations and suitable transformations.
- **Matplotlib and Seaborn:** Create descriptive, comparative, and distribution charts.
- Query the local SQLite file from Python through `sqlite3`. Prefer aggregated results or suitable batches over loading a large raw file into memory without need; do not fall back to a remote database.
- Give each notebook a clear question, ordered steps, reproducible results, and stated limitations. Do not use notebooks as the only record of data-cleaning rules.

## Suggested Visualizations

- Bar charts for the most frequent skills and roles, overall or by selected market.
- Comparative charts for roles and skills across countries, with sample sizes.
- Box plots or salary distributions only after standardizing currency and pay period; show the number of salary-bearing advertisements.
- Work-arrangement comparisons by country or role when coverage is sufficient.
- Time-series charts for advertisement counts and skill demand only when dates are reliable and cover a meaningful period.
- Heatmaps or networks for skill co-occurrence when repeated advertisements do not distort the result.

## Interpretation Rules

- Prefer the median for salaries, which may be skewed and contain outliers. Do not present an average without context, distribution, and sample count.
- Do not directly compare different currencies or pay periods. Document any exchange-rate policy used.
- Distinguish advertised salaries from model estimates.
- Treat missing values as missing coverage, not zero.
- Review repeated or expired postings; a high number of advertisements from an employer does not necessarily mean more accessible opportunities.
- Every chart should identify its source, sample limitations, filters, units, and time period where relevant.

## Required Deliverables

- Documented analytical SQL queries.
- Reproducible Python notebooks for exploratory analysis and validation.
- Charts suitable for the website and final presentation.
- A findings report covering the question, method, sample size, result, limitations, and decisions informed by the result.
