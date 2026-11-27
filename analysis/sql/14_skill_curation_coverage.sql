SELECT
    job_skills.skill_match_policy,
    job_skills.skill_review_status,
    skills.match_policy AS catalog_match_policy,
    skills.review_status AS catalog_review_status,
    CASE
        WHEN job_skills.skill_match_policy = skills.match_policy
         AND job_skills.skill_review_status = skills.review_status
         AND job_skills.skill_match_policy = 'approved_aliases'
         AND job_skills.skill_review_status = 'curated'
            THEN 'included_reviewed'
        WHEN job_skills.skill_match_policy = skills.match_policy
         AND job_skills.skill_review_status = skills.review_status
         AND job_skills.skill_match_policy = 'exact_only'
         AND job_skills.skill_review_status = 'curated_exact_only'
            THEN 'included_reviewed'
        WHEN job_skills.skill_match_policy = 'exact_only'
         AND job_skills.skill_review_status = 'needs_review'
            THEN 'excluded_needs_review'
        WHEN job_skills.skill_match_policy = 'exclude_pending_review'
         AND job_skills.skill_review_status = 'needs_owner_review'
            THEN 'excluded_owner_review'
        ELSE 'excluded_policy_or_status_mismatch'
    END AS analysis_decision,
    COUNT(*) AS job_skill_assignment_count,
    COUNT(DISTINCT job_skills.record_id) AS distinct_job_record_count,
    COUNT(DISTINCT job_skills.skill_id) AS distinct_skill_count,
    COUNT(DISTINCT job_skills.source_dataset) AS source_dataset_count
FROM job_skills
JOIN skills ON skills.skill_id = job_skills.skill_id
GROUP BY
    job_skills.skill_match_policy,
    job_skills.skill_review_status,
    skills.match_policy,
    skills.review_status,
    analysis_decision
ORDER BY
    analysis_decision,
    job_skills.skill_match_policy,
    job_skills.skill_review_status;
