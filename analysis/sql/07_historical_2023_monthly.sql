SELECT
    substr(posted_at, 1, 7) AS posting_month,
    COUNT(*) AS job_record_count
FROM jobs
WHERE source_dataset = 'international_jobs'
  AND posted_at IS NOT NULL
  AND trim(posted_at) <> ''
  AND substr(posted_at, 1, 4) = '2023'
GROUP BY substr(posted_at, 1, 7)
ORDER BY posting_month;
