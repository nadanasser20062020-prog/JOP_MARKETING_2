SELECT
    lower(trim(country)) AS normalized_country_label,
    MIN(trim(country)) AS country_or_territory_label,
    COUNT(DISTINCT record_id) AS job_record_count
FROM jobs
WHERE source_dataset = 'merged_tech_jobs'
  AND country IS NOT NULL
  AND trim(country) <> ''
  AND lower(trim(country)) IN (
      'algeria', 'bahrain', 'comoros', 'djibouti', 'egypt', 'iraq', 'jordan',
      'kuwait', 'lebanon', 'libya', 'mauritania', 'morocco', 'oman',
      'palestine', 'qatar', 'saudi arabia', 'somalia', 'sudan', 'syria',
      'tunisia', 'united arab emirates', 'yemen'
  )
GROUP BY lower(trim(country))
ORDER BY normalized_country_label;
