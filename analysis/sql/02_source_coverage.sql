SELECT
    source_dataset,
    snapshot_type,
    COUNT(*) AS job_records,
    SUM(CASE WHEN title IS NOT NULL AND trim(title) <> '' THEN 1 ELSE 0 END) AS title_present,
    SUM(CASE WHEN company IS NOT NULL AND trim(company) <> '' THEN 1 ELSE 0 END) AS company_present,
    SUM(CASE WHEN country IS NOT NULL AND trim(country) <> '' THEN 1 ELSE 0 END) AS country_label_present,
    SUM(CASE WHEN description IS NOT NULL AND trim(description) <> '' THEN 1 ELSE 0 END) AS description_present,
    SUM(CASE WHEN source_url IS NOT NULL AND trim(source_url) <> '' THEN 1 ELSE 0 END) AS source_url_present,
    SUM(CASE WHEN posted_at IS NOT NULL AND trim(posted_at) <> '' THEN 1 ELSE 0 END) AS posted_at_present,
    SUM(CASE WHEN source_updated_at IS NOT NULL AND trim(source_updated_at) <> '' THEN 1 ELSE 0 END) AS source_updated_at_present,
    SUM(CASE WHEN salary_raw IS NOT NULL AND trim(salary_raw) <> '' THEN 1 ELSE 0 END) AS salary_text_present,
    SUM(CASE WHEN salary_year_avg IS NOT NULL AND trim(salary_year_avg) <> '' THEN 1 ELSE 0 END) AS annual_salary_value_present,
    SUM(CASE WHEN salary_hour_avg IS NOT NULL AND trim(salary_hour_avg) <> '' THEN 1 ELSE 0 END) AS hourly_salary_value_present,
    SUM(CASE WHEN skills IS NOT NULL AND trim(skills) <> '' THEN 1 ELSE 0 END) AS source_skills_text_present
FROM jobs
GROUP BY source_dataset, snapshot_type
ORDER BY job_records DESC;
