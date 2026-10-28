# Machine Learning Plan

Models must address a clear project question; they should not be added as decoration. Every model depends on the dataset audit. If the required data is unavailable or unreliable, document why the model is unsuitable rather than presenting misleading results.

## 1. Skill-to-Job Matching — Explainable Baseline

- **Question:** Which job advertisements or role profiles cover the largest share of a user's skills, and which common skills are missing?
- **Potential inputs:** Normalized user skills, skills extracted or normalized for each advertisement, and market or work-arrangement preferences if available.
- **Approach:** Start with a transparent skill-coverage measure, rank relevant jobs, and explain matched and missing skills. Compare with text-similarity methods only if they improve ranking quality.
- **Evaluation:** Create team-reviewed test cases, inspect ranking logic, and assess the quality of missing-skill recommendations. Use ranking metrics such as Precision@K only when reviewed relevance judgments are available.
- **Usage limit:** A coverage score is not a hiring probability and does not establish a candidate's suitability in every respect.

## 2. Clustering — Discovering Job Groups

- **Question:** Are there groups of advertisements with similar skill combinations or descriptions?
- **Potential inputs:** A normalized skill set for each advertisement, or text representations of titles and descriptions if the text is usable.
- **Approach:** Build an appropriate representation, test a small number of clustering methods, and review metrics, examples, and the most frequent skills in each group. Assign descriptive names only after manual interpretation.
- **Evaluation:** Review silhouette or another suitable metric for the representation, cluster stability, and representative examples.
- **Output:** Patterns that support market exploration, not authoritative employer or occupation labels.

## 3. Classification — Job-Family Classification

- **Question:** Can an advertisement be classified into useful categories such as Data, Backend, or Frontend?
- **Required inputs:** An analyzable title and description, defined categories, and a reviewed labelled sample or a reliable existing category field.
- **Approach:** Define category rules, prepare and review labels, split data without leakage, and establish a simple text-classification baseline such as TF-IDF with a suitable classifier. Manually review errors.
- **Evaluation:** Report per-class precision, recall, and F1, as well as Macro-F1 and a confusion matrix. Do not rely on accuracy alone when class sizes differ.
- **Go/no-go condition:** Do not expose the model if there are too few reliable labels or its errors are unacceptable. A report explaining insufficient labels is a valid outcome.

## 4. Regression — Salary Estimation

- **Question:** Can an approximate salary level or range be estimated from job-advertisement attributes?
- **Required inputs:** A sufficient number of advertisements with disclosed salaries, comparable currency and pay-period data, and explanatory attributes such as country, role, experience, or skills.
- **Approach:** Standardize units and currencies under a documented policy; do not encode undisclosed salaries as zero. Build a simple baseline and compare it with suitable additional models.
- **Evaluation:** Use an appropriate train/test split, compare against the baseline, and report MAE, RMSE, and R² with clear interpretation in understandable units. Review errors by country and category.
- **Go/no-go condition:** If salary coverage is sparse or inconsistent, keep the experiment in the report and do not show estimates to users.

## Reliable Experiment Practices

- Separate training and test data before fitting data-dependent transformations; prevent duplicate advertisements from leaking across the split.
- Use a time-based split when dates support the intended use of predicting future advertisements.
- Compare every model with a simple baseline and record data definitions, features, metrics, and experiment settings.
- Check performance differences across countries or categories; they may reveal collection bias or weak market coverage.
- Do not display a recommendation or salary figure without explaining its evidence and limitations.

## Integration with the Website

- Matching returns relevant jobs with shared skills, missing skills, and ranking explanations.
- Clustering may support exploration of skill groups.
- Classification may support browsing or normalization of job families.
- Regression estimates must remain distinct from advertised salaries and include clear limitations.
- Document experiment results and metrics; do not conceal weak model performance just to claim that every algorithm was used.
