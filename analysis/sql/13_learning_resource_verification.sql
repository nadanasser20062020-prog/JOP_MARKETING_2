SELECT
    COUNT(*) AS total_learning_resources,
    SUM(CASE WHEN cost_status = 'free_verified' THEN 1 ELSE 0 END) AS source_marked_free_verified,
    SUM(CASE WHEN cost_status = 'some_free_options' THEN 1 ELSE 0 END) AS source_marked_some_free_options,
    SUM(CASE WHEN cost_status = 'conditional_or_mixed' THEN 1 ELSE 0 END) AS source_marked_conditional_or_mixed,
    SUM(CASE WHEN cost_status = 'cost_unverified' THEN 1 ELSE 0 END) AS source_marked_cost_unverified,
    SUM(CASE WHEN verified_on > '2026-10-28' THEN 1 ELSE 0 END) AS verification_dates_after_archive_build,
    MIN(verified_on) AS earliest_source_verification_date,
    MAX(verified_on) AS latest_source_verification_date
FROM learning_resources;
