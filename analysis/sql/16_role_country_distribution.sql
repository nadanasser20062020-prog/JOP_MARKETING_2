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
), role_source AS (
    SELECT
        r.role_id,
        r.source_dataset,
        SUM(r.job_record_count) AS role_source_record_count,
        SUM(r.eligible_job_record_count) AS role_source_records_with_eligible_skills
    FROM api_role_scope_rollups AS r
    JOIN top_roles AS t ON t.role_id = r.role_id
    GROUP BY r.role_id, r.source_dataset
), role_country AS (
    SELECT
        r.role_id,
        r.source_dataset,
        r.country_key,
        MIN(r.country_label) AS country_or_territory_label,
        SUM(r.job_record_count) AS role_country_job_record_count,
        SUM(r.eligible_job_record_count) AS role_country_records_with_eligible_skills
    FROM api_role_scope_rollups AS r
    JOIN top_roles AS t ON t.role_id = r.role_id
    WHERE r.country_key <> ''
      AND r.country_key NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
    GROUP BY r.role_id, r.source_dataset, r.country_key
), ranked_countries AS (
    SELECT
        role_country.*,
        SUM(role_country_job_record_count) OVER (
            PARTITION BY role_id, source_dataset
        ) AS country_mapped_role_source_records,
        ROW_NUMBER() OVER (
            PARTITION BY role_id, source_dataset
            ORDER BY role_country_job_record_count DESC, country_key
        ) AS country_rank
    FROM role_country
)
SELECT
    top_roles.role_rank,
    top_roles.role_id,
    top_roles.display_title,
    top_roles.role_record_count,
    top_roles.role_records_with_eligible_skills,
    top_roles.source_dataset_count,
    ranked_countries.source_dataset,
    role_source.role_source_record_count,
    ranked_countries.country_rank,
    ranked_countries.country_key,
    ranked_countries.country_or_territory_label,
    ranked_countries.role_country_job_record_count,
    ranked_countries.country_mapped_role_source_records,
    ROUND(
        100.0 * ranked_countries.role_country_job_record_count
        / NULLIF(ranked_countries.country_mapped_role_source_records, 0),
        2
    ) AS share_of_country_mapped_role_source_records_percent,
    ranked_countries.role_country_records_with_eligible_skills,
    ROUND(
        100.0 * ranked_countries.role_country_records_with_eligible_skills
        / NULLIF(ranked_countries.role_country_job_record_count, 0),
        2
    ) AS role_country_skill_coverage_percent
FROM ranked_countries
JOIN top_roles ON top_roles.role_id = ranked_countries.role_id
JOIN role_source
  ON role_source.role_id = ranked_countries.role_id
 AND role_source.source_dataset = ranked_countries.source_dataset
ORDER BY top_roles.role_rank, ranked_countries.source_dataset, ranked_countries.country_rank;
