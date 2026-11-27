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
), role_country AS (
    SELECT
        r.role_id,
        r.country_key,
        MIN(r.country_label) AS country_or_territory_label,
        SUM(r.job_record_count) AS role_country_job_record_count,
        SUM(r.eligible_job_record_count) AS role_country_records_with_eligible_skills,
        COUNT(DISTINCT r.source_dataset) AS role_country_source_dataset_count
    FROM api_role_scope_rollups AS r
    JOIN top_roles AS t ON t.role_id = r.role_id
    WHERE r.country_key <> ''
      AND r.country_key NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
    GROUP BY r.role_id, r.country_key
), ranked_countries AS (
    SELECT
        role_country.*,
        SUM(role_country_job_record_count) OVER (PARTITION BY role_id) AS country_mapped_role_records,
        ROW_NUMBER() OVER (
            PARTITION BY role_id
            ORDER BY role_country_job_record_count DESC, country_key
        ) AS country_rank
    FROM role_country
), skill_counts AS (
    SELECT
        r.role_id,
        r.country_key,
        r.skill_id,
        MIN(r.canonical_name) AS skill_name,
        MIN(r.category) AS skill_category,
        SUM(r.job_record_count) AS skill_job_record_count
    FROM api_role_skill_rollups AS r
    JOIN top_roles AS t ON t.role_id = r.role_id
    WHERE r.country_key <> ''
      AND r.country_key NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
    GROUP BY r.role_id, r.country_key, r.skill_id
), ranked_skills AS (
    SELECT
        skill_counts.*,
        ROW_NUMBER() OVER (
            PARTITION BY role_id, country_key
            ORDER BY skill_job_record_count DESC, skill_name COLLATE NOCASE
        ) AS skill_rank
    FROM skill_counts
)
SELECT
    top_roles.role_rank,
    top_roles.role_id,
    top_roles.display_title,
    top_roles.role_record_count,
    ranked_countries.country_rank,
    ranked_countries.country_key,
    ranked_countries.country_or_territory_label,
    ranked_countries.role_country_job_record_count,
    ranked_countries.country_mapped_role_records,
    ROUND(
        100.0 * ranked_countries.role_country_job_record_count
        / NULLIF(ranked_countries.country_mapped_role_records, 0),
        2
    ) AS share_of_country_mapped_role_records_percent,
    ranked_countries.role_country_records_with_eligible_skills AS denominator_role_country_records_with_eligible_skills,
    ranked_countries.role_country_source_dataset_count,
    ranked_skills.skill_rank,
    ranked_skills.skill_id,
    ranked_skills.skill_name,
    ranked_skills.skill_category,
    ranked_skills.skill_job_record_count,
    ROUND(
        100.0 * ranked_skills.skill_job_record_count
        / NULLIF(ranked_countries.role_country_records_with_eligible_skills, 0),
        2
    ) AS share_of_role_country_records_with_eligible_skills_percent
FROM ranked_countries
JOIN top_roles ON top_roles.role_id = ranked_countries.role_id
JOIN ranked_skills
  ON ranked_skills.role_id = ranked_countries.role_id
 AND ranked_skills.country_key = ranked_countries.country_key
WHERE ranked_countries.country_rank <= 5
  AND ranked_skills.skill_rank <= 5
ORDER BY top_roles.role_rank, ranked_countries.country_rank, ranked_skills.skill_rank;
