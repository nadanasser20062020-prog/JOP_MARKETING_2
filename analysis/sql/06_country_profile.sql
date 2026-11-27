SELECT
    trim(country) AS country_or_territory_label,
    COUNT(*) AS job_record_count,
    COUNT(DISTINCT record_id) AS distinct_source_job_records
FROM jobs
WHERE country IS NOT NULL
  AND trim(country) <> ''
  AND lower(trim(country)) NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
GROUP BY lower(trim(country)), trim(country)
ORDER BY job_record_count DESC, country_or_territory_label COLLATE NOCASE;
