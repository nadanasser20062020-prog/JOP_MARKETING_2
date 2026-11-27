SELECT
    lower(trim(title)) AS normalized_title,
    MIN(trim(title)) AS display_title,
    COUNT(*) AS job_record_count
FROM jobs
WHERE title IS NOT NULL
  AND trim(title) <> ''
GROUP BY lower(trim(title))
ORDER BY job_record_count DESC, normalized_title
LIMIT 30;
