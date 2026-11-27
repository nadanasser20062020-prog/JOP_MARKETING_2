SELECT
    source_dataset,
    COALESCE(NULLIF(lower(trim(remote_flag)), ''), 'not_supplied') AS remote_flag_source_value,
    COUNT(*) AS job_record_count
FROM jobs
GROUP BY source_dataset, remote_flag_source_value
ORDER BY source_dataset, job_record_count DESC, remote_flag_source_value;
