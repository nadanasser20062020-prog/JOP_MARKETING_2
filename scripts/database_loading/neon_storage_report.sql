SELECT
    current_database() AS database_name,
    pg_database_size(current_database()) AS current_database_bytes,
    pg_size_pretty(pg_database_size(current_database())) AS current_database_size;

SELECT
    schemaname,
    relname AS table_name,
    n_live_tup AS estimated_live_rows,
    pg_relation_size(format('%I.%I', schemaname, relname)::regclass) AS heap_bytes,
    pg_indexes_size(format('%I.%I', schemaname, relname)::regclass) AS index_bytes,
    pg_total_relation_size(format('%I.%I', schemaname, relname)::regclass) AS total_bytes_including_toast,
    pg_size_pretty(pg_total_relation_size(format('%I.%I', schemaname, relname)::regclass)) AS total_size
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(format('%I.%I', schemaname, relname)::regclass) DESC;
