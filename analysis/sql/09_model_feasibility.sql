SELECT
    source_dataset,
    COUNT(*) AS job_record_count,
    SUM(CASE WHEN category_raw IS NOT NULL AND trim(category_raw) <> '' THEN 1 ELSE 0 END) AS category_label_count,
    COUNT(DISTINCT CASE WHEN category_raw IS NOT NULL AND trim(category_raw) <> '' THEN lower(trim(category_raw)) END) AS distinct_category_label_count,
    SUM(CASE WHEN title IS NOT NULL AND trim(title) <> '' THEN 1 ELSE 0 END) AS title_count,
    SUM(CASE WHEN description IS NOT NULL AND trim(description) <> '' THEN 1 ELSE 0 END) AS description_count,
    SUM(CASE WHEN salary_year_avg IS NOT NULL AND trim(salary_year_avg) <> '' THEN 1 ELSE 0 END) AS annual_salary_field_count,
    SUM(CASE WHEN salary_hour_avg IS NOT NULL AND trim(salary_hour_avg) <> '' THEN 1 ELSE 0 END) AS hourly_salary_field_count,
    SUM(CASE WHEN salary_currency IS NOT NULL AND trim(salary_currency) <> '' THEN 1 ELSE 0 END) AS currency_count,
    SUM(CASE WHEN salary_basis IS NOT NULL AND trim(salary_basis) <> '' THEN 1 ELSE 0 END) AS pay_basis_count
FROM jobs
GROUP BY source_dataset
ORDER BY job_record_count DESC;
