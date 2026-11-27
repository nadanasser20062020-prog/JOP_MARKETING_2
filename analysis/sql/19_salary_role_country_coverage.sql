SELECT
    j.source_dataset,
    lower(trim(j.title)) AS normalized_title,
    MIN(trim(j.title)) AS display_title,
    lower(trim(j.country)) AS country_key,
    MIN(trim(j.country)) AS country_or_territory_label,
    COALESCE(NULLIF(trim(j.salary_currency), ''), 'not_supplied') AS salary_currency,
    COALESCE(NULLIF(lower(trim(j.salary_basis)), ''), 'not_supplied') AS salary_basis,
    COALESCE(NULLIF(lower(trim(j.salary_rate)), ''), 'not_supplied') AS salary_rate,
    COALESCE(NULLIF(j.salary_provenance_status, ''), 'not_available') AS salary_provenance_status,
    COUNT(*) AS records_with_any_salary_field,
    SUM(CASE WHEN j.salary_raw IS NOT NULL AND trim(j.salary_raw) <> '' THEN 1 ELSE 0 END) AS salary_raw_text_records,
    SUM(CASE WHEN j.salary_year_avg IS NOT NULL AND trim(j.salary_year_avg) <> '' THEN 1 ELSE 0 END) AS annual_value_field_records,
    SUM(CASE WHEN j.salary_hour_avg IS NOT NULL AND trim(j.salary_hour_avg) <> '' THEN 1 ELSE 0 END) AS hourly_value_field_records,
    SUM(CASE WHEN j.salary_currency IS NOT NULL AND trim(j.salary_currency) <> '' THEN 1 ELSE 0 END) AS records_with_explicit_currency,
    SUM(CASE
        WHEN lower(trim(COALESCE(j.salary_basis, ''))) IN ('year', 'annual', 'yearly', 'per year', 'hour', 'hourly', 'per hour', 'month', 'monthly', 'per month', 'week', 'weekly', 'per week', 'day', 'daily', 'per day')
         AND lower(trim(COALESCE(j.salary_rate, ''))) IN ('year', 'annual', 'yearly', 'per year', 'hour', 'hourly', 'per hour', 'month', 'monthly', 'per month', 'week', 'weekly', 'per week', 'day', 'daily', 'per day')
        THEN 1 ELSE 0 END
    ) AS records_with_recognized_period_fields,
    SUM(CASE
        WHEN j.salary_year_avg IS NOT NULL AND trim(j.salary_year_avg) <> ''
         AND j.salary_currency IS NOT NULL AND trim(j.salary_currency) <> ''
         AND lower(trim(COALESCE(j.salary_basis, ''))) IN ('year', 'annual', 'yearly', 'per year')
         AND lower(trim(COALESCE(j.salary_rate, ''))) IN ('year', 'annual', 'yearly', 'per year')
        THEN 1 ELSE 0 END
    ) AS annual_values_with_currency_and_matching_period,
    SUM(CASE
        WHEN j.salary_hour_avg IS NOT NULL AND trim(j.salary_hour_avg) <> ''
         AND j.salary_currency IS NOT NULL AND trim(j.salary_currency) <> ''
         AND lower(trim(COALESCE(j.salary_basis, ''))) IN ('hour', 'hourly', 'per hour')
         AND lower(trim(COALESCE(j.salary_rate, ''))) IN ('hour', 'hourly', 'per hour')
        THEN 1 ELSE 0 END
    ) AS hourly_values_with_currency_and_matching_period,
    SUM(CASE WHEN j.salary_provenance_status = 'source_or_origin_unverified' THEN 1 ELSE 0 END) AS records_with_unverified_source_provenance,
    SUM(CASE WHEN j.salary_provenance_status = 'estimate_or_research_indicated' THEN 1 ELSE 0 END) AS records_with_estimate_or_research_provenance
FROM jobs AS j
WHERE j.title IS NOT NULL
  AND trim(j.title) <> ''
  AND j.country IS NOT NULL
  AND trim(j.country) <> ''
  AND lower(trim(j.country)) NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
  AND (
      (j.salary_raw IS NOT NULL AND trim(j.salary_raw) <> '')
      OR (j.salary_year_avg IS NOT NULL AND trim(j.salary_year_avg) <> '')
      OR (j.salary_hour_avg IS NOT NULL AND trim(j.salary_hour_avg) <> '')
  )
GROUP BY
    j.source_dataset,
    lower(trim(j.title)),
    lower(trim(j.country)),
    COALESCE(NULLIF(trim(j.salary_currency), ''), 'not_supplied'),
    COALESCE(NULLIF(lower(trim(j.salary_basis)), ''), 'not_supplied'),
    COALESCE(NULLIF(lower(trim(j.salary_rate)), ''), 'not_supplied'),
    COALESCE(NULLIF(j.salary_provenance_status, ''), 'not_available')
ORDER BY records_with_any_salary_field DESC, j.source_dataset, normalized_title, country_key;
