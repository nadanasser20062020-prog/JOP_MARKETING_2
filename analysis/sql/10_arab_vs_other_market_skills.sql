WITH classified_jobs AS (
    SELECT
        record_id,
        CASE
            WHEN lower(trim(country)) IN (
                'algeria', 'bahrain', 'comoros', 'djibouti', 'egypt', 'iraq', 'jordan',
                'kuwait', 'lebanon', 'libya', 'mauritania', 'morocco', 'oman',
                'palestine', 'qatar', 'saudi arabia', 'somalia', 'sudan', 'syria',
                'tunisia', 'united arab emirates', 'yemen'
            ) THEN 'Arab markets'
            ELSE 'Other represented markets'
        END AS market_group
    FROM jobs
    WHERE source_dataset = 'merged_tech_jobs'
      AND country IS NOT NULL
      AND trim(country) <> ''
      AND lower(trim(country)) NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
), eligible_skill_jobs AS (
    SELECT DISTINCT classified_jobs.record_id
    FROM classified_jobs
    JOIN job_skills ON job_skills.record_id = classified_jobs.record_id
    JOIN skills ON skills.skill_id = job_skills.skill_id
    WHERE job_skills.skill_match_policy = skills.match_policy
      AND job_skills.skill_review_status = skills.review_status
      AND (
          (job_skills.skill_match_policy = 'approved_aliases' AND job_skills.skill_review_status = 'curated')
          OR (job_skills.skill_match_policy = 'exact_only' AND job_skills.skill_review_status = 'curated_exact_only')
      )
), market_population AS (
    SELECT
        classified_jobs.market_group,
        COUNT(DISTINCT classified_jobs.record_id) AS country_mapped_job_records,
        COUNT(DISTINCT eligible_skill_jobs.record_id) AS jobs_with_eligible_skills
    FROM classified_jobs
    LEFT JOIN eligible_skill_jobs ON eligible_skill_jobs.record_id = classified_jobs.record_id
    GROUP BY classified_jobs.market_group
), market_skill_counts AS (
    SELECT
        classified_jobs.market_group,
        skills.skill_id,
        skills.canonical_name,
        skills.match_policy,
        skills.review_status,
        COUNT(DISTINCT job_skills.record_id) AS job_record_count
    FROM classified_jobs
    JOIN job_skills ON job_skills.record_id = classified_jobs.record_id
    JOIN skills ON skills.skill_id = job_skills.skill_id
    WHERE job_skills.skill_match_policy = skills.match_policy
      AND job_skills.skill_review_status = skills.review_status
      AND (
          (job_skills.skill_match_policy = 'approved_aliases' AND job_skills.skill_review_status = 'curated')
          OR (job_skills.skill_match_policy = 'exact_only' AND job_skills.skill_review_status = 'curated_exact_only')
      )
    GROUP BY
        classified_jobs.market_group,
        skills.skill_id,
        skills.canonical_name,
        skills.match_policy,
        skills.review_status
)
SELECT
    market_skill_counts.market_group,
    market_skill_counts.skill_id,
    market_skill_counts.canonical_name,
    market_skill_counts.match_policy,
    market_skill_counts.review_status,
    market_skill_counts.job_record_count,
    market_population.country_mapped_job_records,
    market_population.jobs_with_eligible_skills,
    ROUND(100.0 * market_skill_counts.job_record_count / market_population.jobs_with_eligible_skills, 2) AS share_of_jobs_with_eligible_skills_percent
FROM market_skill_counts
JOIN market_population ON market_population.market_group = market_skill_counts.market_group
ORDER BY market_skill_counts.market_group, market_skill_counts.job_record_count DESC, market_skill_counts.canonical_name COLLATE NOCASE;
