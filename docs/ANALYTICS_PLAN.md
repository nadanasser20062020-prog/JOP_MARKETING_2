# SQL and Python Analytics Plan

The analysis should answer specific questions about the **collected job advertisements**, not make unsupported claims about entire labor markets. Begin after T01–T05: audit the dataset, clean it, design the relational model, and load it into the database.

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

## SQL Approach

- Perform database aggregations for counts, groupings by country/role/skill, summary statistics, and date filters.
- Keep analytical queries separate from schema definitions. Document the question and metric definition for each query.
- Validate queries against manually checked samples and compare totals with the database.
- When SQL is executed from Python, keep each query readable and reviewable; never put database credentials in a notebook.

## Python Approach

- **Pandas:** Inspect and transform query results or samples; clean and combine analysis-ready data when needed.
- **NumPy:** Perform numerical calculations and suitable transformations.
- **Matplotlib and Seaborn:** Create descriptive, comparative, and distribution charts.
- Connect to Neon securely. Prefer aggregated results or suitable batches over loading a large raw file into memory without need.
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
