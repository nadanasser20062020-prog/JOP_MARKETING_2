SELECT
    source_dataset,
    COALESCE(NULLIF(trim(salary_provenance_status), ''), 'not_available') AS salary_provenance_status,
    COALESCE(NULLIF(trim(salary_currency), ''), 'not_supplied') AS salary_currency,
    COALESCE(NULLIF(trim(salary_basis), ''), 'not_supplied') AS salary_basis,
    COALESCE(NULLIF(trim(salary_rate), ''), 'not_supplied') AS salary_rate,
    COUNT(*) AS records_with_any_salary_field,
    SUM(CASE WHEN salary_raw IS NOT NULL AND trim(salary_raw) <> '' THEN 1 ELSE 0 END) AS salary_text_records,
    SUM(CASE WHEN salary_year_avg IS NOT NULL AND trim(salary_year_avg) <> '' THEN 1 ELSE 0 END) AS annual_value_records,
    SUM(CASE WHEN salary_hour_avg IS NOT NULL AND trim(salary_hour_avg) <> '' THEN 1 ELSE 0 END) AS hourly_value_records,
    SUM(CASE WHEN salary_currency IS NOT NULL AND trim(salary_currency) <> '' THEN 1 ELSE 0 END) AS currency_present_records,
    SUM(CASE WHEN salary_basis IS NOT NULL AND trim(salary_basis) <> '' THEN 1 ELSE 0 END) AS basis_present_records
FROM jobs
WHERE (salary_raw IS NOT NULL AND trim(salary_raw) <> '')
   OR (salary_year_avg IS NOT NULL AND trim(salary_year_avg) <> '')
   OR (salary_hour_avg IS NOT NULL AND trim(salary_hour_avg) <> '')
GROUP BY
    source_dataset,
    salary_provenance_status,
    salary_currency,
    salary_basis,
    salary_rate
ORDER BY records_with_any_salary_field DESC, source_dataset;
