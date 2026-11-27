WITH reviewed_skill_links AS (
    SELECT
        job_skills.record_id,
        job_skills.skill_id,
        job_skills.skill_match_policy
    FROM job_skills
    JOIN skills ON skills.skill_id = job_skills.skill_id
    WHERE job_skills.skill_match_policy = skills.match_policy
      AND job_skills.skill_review_status = skills.review_status
      AND (
          (job_skills.skill_match_policy = 'approved_aliases' AND job_skills.skill_review_status = 'curated')
          OR (job_skills.skill_match_policy = 'exact_only' AND job_skills.skill_review_status = 'curated_exact_only')
      )
), skill_population AS (
    SELECT COUNT(DISTINCT record_id) AS jobs_with_eligible_skills
    FROM reviewed_skill_links
), skill_counts AS (
    SELECT
        skills.skill_id,
        skills.canonical_name,
        skills.category,
        skills.review_status,
        reviewed_skill_links.skill_match_policy,
        COUNT(DISTINCT reviewed_skill_links.record_id) AS job_record_count
    FROM reviewed_skill_links
    JOIN skills ON skills.skill_id = reviewed_skill_links.skill_id
    GROUP BY
        skills.skill_id,
        skills.canonical_name,
        skills.category,
        skills.review_status,
        reviewed_skill_links.skill_match_policy
)
SELECT
    skill_counts.skill_id,
    skill_counts.canonical_name,
    skill_counts.category,
    skill_counts.review_status,
    skill_counts.skill_match_policy,
    skill_counts.job_record_count,
    skill_population.jobs_with_eligible_skills AS denominator_job_records,
    ROUND(100.0 * skill_counts.job_record_count / skill_population.jobs_with_eligible_skills, 2) AS share_of_jobs_with_eligible_skills_percent
FROM skill_counts
CROSS JOIN skill_population
ORDER BY skill_counts.job_record_count DESC, skill_counts.canonical_name COLLATE NOCASE
LIMIT 30;
