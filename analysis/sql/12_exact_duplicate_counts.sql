SELECT
    source_dataset,
    COUNT(*) AS total_job_records,
    SUM(CASE WHEN exact_duplicate_within_source = 'yes' THEN 1 ELSE 0 END) AS exact_duplicate_rows_retained,
    SUM(CASE WHEN exact_duplicate_within_source = 'no' THEN 1 ELSE 0 END) AS rows_not_flagged_as_exact_duplicates
FROM jobs
GROUP BY source_dataset
ORDER BY total_job_records DESC;
