WITH reviewed_skill_links AS (
    SELECT
        job_skills.record_id,
        job_skills.skill_id
    FROM job_skills
    JOIN skills ON skills.skill_id = job_skills.skill_id
    WHERE job_skills.skill_match_policy = skills.match_policy
      AND job_skills.skill_review_status = skills.review_status
      AND (
          (job_skills.skill_match_policy = 'approved_aliases' AND job_skills.skill_review_status = 'curated')
          OR (job_skills.skill_match_policy = 'exact_only' AND job_skills.skill_review_status = 'curated_exact_only')
      )
), eligible_skill_summary AS (
    SELECT
        COUNT(*) AS eligible_job_skill_links,
        COUNT(DISTINCT skill_id) AS eligible_distinct_skills,
        COUNT(DISTINCT record_id) AS jobs_with_eligible_skills
    FROM reviewed_skill_links
), country_summary AS (
    SELECT
        COUNT(DISTINCT lower(trim(country))) AS distinct_country_territory_labels
    FROM jobs
    WHERE country IS NOT NULL
      AND trim(country) <> ''
      AND lower(trim(country)) NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
)
SELECT
    COUNT(*) AS total_job_records,
    COUNT(DISTINCT source_dataset) AS source_dataset_count,
    COUNT(DISTINCT lower(trim(title))) AS exact_normalized_title_count,
    SUM(CASE WHEN exact_duplicate_within_source = 'yes' THEN 1 ELSE 0 END) AS exact_duplicate_rows_retained,
    SUM(CASE WHEN listing_status = 'unknown_not_verified' THEN 1 ELSE 0 END) AS listing_status_unknown_rows,
    eligible_skill_summary.eligible_job_skill_links,
    eligible_skill_summary.eligible_distinct_skills,
    eligible_skill_summary.jobs_with_eligible_skills,
    country_summary.distinct_country_territory_labels
FROM jobs
CROSS JOIN eligible_skill_summary
CROSS JOIN country_summary;
