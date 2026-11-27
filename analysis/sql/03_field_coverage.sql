WITH total_jobs AS (
    SELECT COUNT(*) AS job_record_count
    FROM jobs
), reviewed_skill_records AS (
    SELECT DISTINCT job_skills.record_id
    FROM job_skills
    JOIN skills ON skills.skill_id = job_skills.skill_id
    WHERE job_skills.skill_match_policy = skills.match_policy
      AND job_skills.skill_review_status = skills.review_status
      AND (
          (job_skills.skill_match_policy = 'approved_aliases' AND job_skills.skill_review_status = 'curated')
          OR (job_skills.skill_match_policy = 'exact_only' AND job_skills.skill_review_status = 'curated_exact_only')
      )
), field_counts AS (
    SELECT 'title' AS field_name, COUNT(*) AS present_count FROM jobs WHERE title IS NOT NULL AND trim(title) <> ''
    UNION ALL
    SELECT 'company', COUNT(*) FROM jobs WHERE company IS NOT NULL AND trim(company) <> ''
    UNION ALL
    SELECT 'country_or_market_label', COUNT(*) FROM jobs WHERE country IS NOT NULL AND trim(country) <> ''
    UNION ALL
    SELECT 'description', COUNT(*) FROM jobs WHERE description IS NOT NULL AND trim(description) <> ''
    UNION ALL
    SELECT 'source_url', COUNT(*) FROM jobs WHERE source_url IS NOT NULL AND trim(source_url) <> ''
    UNION ALL
    SELECT 'posted_at', COUNT(*) FROM jobs WHERE posted_at IS NOT NULL AND trim(posted_at) <> ''
    UNION ALL
    SELECT 'source_updated_at_semantics_unverified', COUNT(*) FROM jobs WHERE source_updated_at IS NOT NULL AND trim(source_updated_at) <> ''
    UNION ALL
    SELECT 'salary_raw_text', COUNT(*) FROM jobs WHERE salary_raw IS NOT NULL AND trim(salary_raw) <> ''
    UNION ALL
    SELECT 'salary_year_avg_field', COUNT(*) FROM jobs WHERE salary_year_avg IS NOT NULL AND trim(salary_year_avg) <> ''
    UNION ALL
    SELECT 'salary_hour_avg_field', COUNT(*) FROM jobs WHERE salary_hour_avg IS NOT NULL AND trim(salary_hour_avg) <> ''
    UNION ALL
    SELECT 'source_skills_text', COUNT(*) FROM jobs WHERE skills IS NOT NULL AND trim(skills) <> ''
    UNION ALL
    SELECT 'usable_skill_associations', COUNT(*) FROM reviewed_skill_records
)
SELECT
    field_counts.field_name,
    field_counts.present_count,
    total_jobs.job_record_count,
    ROUND(100.0 * field_counts.present_count / total_jobs.job_record_count, 2) AS present_percent
FROM field_counts
CROSS JOIN total_jobs
ORDER BY field_counts.field_name;
