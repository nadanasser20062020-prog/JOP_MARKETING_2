WITH role_scope AS (
    SELECT
        role_id,
        MIN(role_display_title) AS display_title,
        SUM(job_record_count) AS role_record_count,
        SUM(eligible_job_record_count) AS role_records_with_eligible_skills,
        COUNT(DISTINCT source_dataset) AS source_dataset_count
    FROM api_role_scope_rollups
    WHERE role_id <> ''
    GROUP BY role_id
), top_roles AS (
    SELECT
        role_id,
        display_title,
        role_record_count,
        role_records_with_eligible_skills,
        source_dataset_count,
        ROW_NUMBER() OVER (ORDER BY role_record_count DESC, role_id) AS role_rank
    FROM role_scope
    ORDER BY role_record_count DESC, role_id
    LIMIT 15
), skill_counts AS (
    SELECT
        r.role_id,
        r.skill_id,
        MIN(r.canonical_name) AS skill_name,
        MIN(r.category) AS skill_category,
        SUM(r.job_record_count) AS skill_job_record_count,
        COUNT(DISTINCT r.source_dataset) AS skill_source_dataset_count
    FROM api_role_skill_rollups AS r
    JOIN top_roles AS t ON t.role_id = r.role_id
    GROUP BY r.role_id, r.skill_id
), ranked_skills AS (
    SELECT
        top_roles.role_rank,
        top_roles.role_id,
        top_roles.display_title,
        top_roles.role_record_count,
        top_roles.role_records_with_eligible_skills,
        top_roles.source_dataset_count,
        skill_counts.skill_id,
        skill_counts.skill_name,
        skill_counts.skill_category,
        skill_counts.skill_job_record_count,
        skill_counts.skill_source_dataset_count,
        ROW_NUMBER() OVER (
            PARTITION BY top_roles.role_id
            ORDER BY skill_counts.skill_job_record_count DESC, skill_counts.skill_name COLLATE NOCASE
        ) AS skill_rank
    FROM top_roles
    JOIN skill_counts ON skill_counts.role_id = top_roles.role_id
)
SELECT
    role_rank,
    role_id,
    display_title,
    role_record_count,
    role_records_with_eligible_skills AS denominator_role_records_with_eligible_skills,
    source_dataset_count AS role_source_dataset_count,
    skill_rank,
    skill_id,
    skill_name,
    skill_category,
    skill_job_record_count,
    skill_source_dataset_count,
    ROUND(
        100.0 * skill_job_record_count
        / NULLIF(role_records_with_eligible_skills, 0),
        2
    ) AS share_of_role_records_with_eligible_skills_percent
FROM ranked_skills
WHERE skill_rank <= 10
ORDER BY role_rank, skill_rank;
