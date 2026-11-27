DELETE FROM api_scope_skill_rollups;
DELETE FROM api_scope_rollups;
DELETE FROM api_role_skill_rollups;
DELETE FROM api_role_scope_rollups;
DELETE FROM api_source_field_coverage;
DELETE FROM api_historical_month_rollups;

INSERT INTO api_source_field_coverage (
    source_dataset, job_record_count, title_records, company_records, country_records,
    city_records, description_records, source_url_records, salary_raw_records,
    posted_at_records, work_mode_raw_records
)
SELECT source_dataset,
       COUNT(*),
       COUNT(CASE WHEN title IS NOT NULL AND trim(title) <> '' THEN 1 END),
       COUNT(CASE WHEN company IS NOT NULL AND trim(company) <> '' THEN 1 END),
       COUNT(CASE WHEN country IS NOT NULL AND trim(country) <> '' THEN 1 END),
       COUNT(CASE WHEN city IS NOT NULL AND trim(city) <> '' THEN 1 END),
       COUNT(CASE WHEN description IS NOT NULL AND trim(description) <> '' THEN 1 END),
       COUNT(CASE WHEN source_url IS NOT NULL AND trim(source_url) <> '' THEN 1 END),
       COUNT(CASE WHEN salary_raw IS NOT NULL AND trim(salary_raw) <> '' THEN 1 END),
       COUNT(CASE WHEN posted_at IS NOT NULL AND trim(posted_at) <> '' THEN 1 END),
       COUNT(CASE WHEN work_mode_raw IS NOT NULL AND trim(work_mode_raw) <> '' THEN 1 END)
FROM jobs
GROUP BY source_dataset;

INSERT INTO api_role_scope_rollups (
    source_dataset, country_key, country_label, work_mode_key, work_mode_label,
    experience_key, experience_label, role_id, role_display_title,
    job_record_count, eligible_job_record_count, records_with_salary_text,
    records_with_explicit_currency, records_with_unverified_salary
)
SELECT j.source_dataset,
       COALESCE(lower(trim(j.country)), ''),
       COALESCE(MIN(NULLIF(trim(j.country), '')), ''),
       COALESCE(lower(trim(j.work_mode_raw)), ''),
       COALESCE(MIN(NULLIF(trim(j.work_mode_raw), '')), ''),
       COALESCE(lower(trim(j.experience_raw)), ''),
       COALESCE(MIN(NULLIF(trim(j.experience_raw), '')), ''),
       COALESCE(lower(trim(j.title)), ''),
       COALESCE(MIN(NULLIF(trim(j.title), '')), ''),
       COUNT(*),
       SUM(CASE WHEN EXISTS (
           SELECT 1
           FROM job_skills AS js
           JOIN skills AS s ON s.skill_id = js.skill_id
             AND js.skill_match_policy = s.match_policy
             AND js.skill_review_status = s.review_status
             AND (
               (js.skill_match_policy = 'approved_aliases' AND js.skill_review_status = 'curated'
                 AND s.match_policy = 'approved_aliases' AND s.review_status = 'curated')
               OR
               (js.skill_match_policy = 'exact_only' AND js.skill_review_status = 'curated_exact_only'
                 AND s.match_policy = 'exact_only' AND s.review_status = 'curated_exact_only')
             )
           WHERE js.record_id = j.record_id
       ) THEN 1 ELSE 0 END),
       SUM(CASE WHEN ((j.salary_raw IS NOT NULL AND trim(j.salary_raw) <> '')
                    OR (j.salary_year_avg IS NOT NULL AND trim(j.salary_year_avg) <> '')
                    OR (j.salary_hour_avg IS NOT NULL AND trim(j.salary_hour_avg) <> ''))
                 THEN 1 ELSE 0 END),
       SUM(CASE WHEN ((j.salary_raw IS NOT NULL AND trim(j.salary_raw) <> '')
                    OR (j.salary_year_avg IS NOT NULL AND trim(j.salary_year_avg) <> '')
                    OR (j.salary_hour_avg IS NOT NULL AND trim(j.salary_hour_avg) <> ''))
                      AND j.salary_currency IS NOT NULL AND trim(j.salary_currency) <> ''
                 THEN 1 ELSE 0 END),
       SUM(CASE WHEN ((j.salary_raw IS NOT NULL AND trim(j.salary_raw) <> '')
                    OR (j.salary_year_avg IS NOT NULL AND trim(j.salary_year_avg) <> '')
                    OR (j.salary_hour_avg IS NOT NULL AND trim(j.salary_hour_avg) <> ''))
                      AND j.salary_provenance_status = 'source_or_origin_unverified'
                 THEN 1 ELSE 0 END)
FROM jobs AS j
GROUP BY j.source_dataset,
         COALESCE(lower(trim(j.country)), ''),
         COALESCE(lower(trim(j.work_mode_raw)), ''),
         COALESCE(lower(trim(j.experience_raw)), ''),
         COALESCE(lower(trim(j.title)), '');

INSERT INTO api_scope_rollups (
    source_dataset, country_key, country_label, work_mode_key, work_mode_label,
    experience_key, experience_label, job_record_count, eligible_job_record_count
)
SELECT source_dataset, country_key, MIN(country_label), work_mode_key, MIN(work_mode_label),
       experience_key, MIN(experience_label), SUM(job_record_count), SUM(eligible_job_record_count)
FROM api_role_scope_rollups
GROUP BY source_dataset, country_key, work_mode_key, experience_key;

INSERT INTO api_role_skill_rollups (
    source_dataset, country_key, work_mode_key, experience_key, role_id,
    skill_id, canonical_name, category, job_record_count
)
SELECT j.source_dataset,
       COALESCE(lower(trim(j.country)), ''),
       COALESCE(lower(trim(j.work_mode_raw)), ''),
       COALESCE(lower(trim(j.experience_raw)), ''),
       COALESCE(lower(trim(j.title)), ''),
       s.skill_id, s.canonical_name, s.category,
       COUNT(*)
FROM jobs AS j
JOIN job_skills AS js ON js.record_id = j.record_id
JOIN skills AS s ON s.skill_id = js.skill_id
  AND js.skill_match_policy = s.match_policy
  AND js.skill_review_status = s.review_status
  AND (
    (js.skill_match_policy = 'approved_aliases' AND js.skill_review_status = 'curated'
      AND s.match_policy = 'approved_aliases' AND s.review_status = 'curated')
    OR
    (js.skill_match_policy = 'exact_only' AND js.skill_review_status = 'curated_exact_only'
      AND s.match_policy = 'exact_only' AND s.review_status = 'curated_exact_only')
  )
GROUP BY j.source_dataset,
         COALESCE(lower(trim(j.country)), ''),
         COALESCE(lower(trim(j.work_mode_raw)), ''),
         COALESCE(lower(trim(j.experience_raw)), ''),
         COALESCE(lower(trim(j.title)), ''),
         s.skill_id, s.canonical_name, s.category;

INSERT INTO api_scope_skill_rollups (
    source_dataset, country_key, work_mode_key, experience_key,
    skill_id, canonical_name, category, job_record_count
)
SELECT source_dataset, country_key, work_mode_key, experience_key,
       skill_id, MIN(canonical_name), MIN(category), SUM(job_record_count)
FROM api_role_skill_rollups
GROUP BY source_dataset, country_key, work_mode_key, experience_key, skill_id;

INSERT INTO api_historical_month_rollups (
    source_dataset, month, country_key, country_label, job_record_count
)
SELECT source_dataset,
       substr(posted_at, 1, 7),
       COALESCE(lower(trim(country)), ''),
       COALESCE(MIN(NULLIF(trim(country), '')), ''),
       COUNT(*)
FROM jobs
WHERE source_dataset = 'international_jobs'
  AND source_date_field = 'posted_at_or_job_posted_date'
  AND posted_at IS NOT NULL AND trim(posted_at) <> ''
  AND substr(posted_at, 1, 4) = '2023'
GROUP BY source_dataset, substr(posted_at, 1, 7), COALESCE(lower(trim(country)), '');
