ALTER TABLE data_sources ADD COLUMN source_kind TEXT;
ALTER TABLE data_sources ADD COLUMN snapshot_bucket TEXT;
ALTER TABLE data_sources ADD COLUMN date_semantics TEXT;
ALTER TABLE data_sources ADD COLUMN listing_status TEXT;
ALTER TABLE data_sources ADD COLUMN source_file_count INTEGER CHECK (source_file_count IS NULL OR source_file_count >= 0);
ALTER TABLE data_sources ADD COLUMN source_row_count INTEGER CHECK (source_row_count IS NULL OR source_row_count >= 0);

ALTER TABLE source_files ADD COLUMN source_file_id TEXT;
ALTER TABLE source_files ADD COLUMN source_dataset_original TEXT;
ALTER TABLE source_files ADD COLUMN physical_file_name TEXT;
ALTER TABLE source_files ADD COLUMN logical_file_name TEXT;
ALTER TABLE source_files ADD COLUMN file_format TEXT;
ALTER TABLE source_files ADD COLUMN file_role TEXT;
ALTER TABLE source_files ADD COLUMN archive_member_name TEXT;
ALTER TABLE source_files ADD COLUMN byte_size INTEGER CHECK (byte_size IS NULL OR byte_size >= 0);
ALTER TABLE source_files ADD COLUMN sha256 TEXT;
ALTER TABLE source_files ADD COLUMN source_row_count INTEGER CHECK (source_row_count IS NULL OR source_row_count >= 0);
ALTER TABLE source_files ADD COLUMN archive_member_count INTEGER CHECK (archive_member_count IS NULL OR archive_member_count >= 0);
CREATE UNIQUE INDEX idx_source_files_source_file_id
    ON source_files (source_file_id)
    WHERE source_file_id IS NOT NULL;

ALTER TABLE import_runs ADD COLUMN source_archive_run_id TEXT;
ALTER TABLE import_runs ADD COLUMN archive_generated_on_utc TEXT;
ALTER TABLE import_runs ADD COLUMN archive_generator TEXT;
ALTER TABLE import_runs ADD COLUMN archive_build_status TEXT;
ALTER TABLE import_runs ADD COLUMN archive_source_file_count INTEGER CHECK (archive_source_file_count IS NULL OR archive_source_file_count >= 0);
ALTER TABLE import_runs ADD COLUMN archive_job_rows INTEGER CHECK (archive_job_rows IS NULL OR archive_job_rows >= 0);
ALTER TABLE import_runs ADD COLUMN archive_job_skill_rows INTEGER CHECK (archive_job_skill_rows IS NULL OR archive_job_skill_rows >= 0);

ALTER TABLE import_run_files ADD COLUMN source_file_id TEXT;
ALTER TABLE import_run_files ADD COLUMN job_rows_emitted INTEGER CHECK (job_rows_emitted IS NULL OR job_rows_emitted >= 0);
ALTER TABLE import_run_files ADD COLUMN job_skill_rows_emitted INTEGER CHECK (job_skill_rows_emitted IS NULL OR job_skill_rows_emitted >= 0);
ALTER TABLE import_run_files ADD COLUMN reference_rows_emitted INTEGER CHECK (reference_rows_emitted IS NULL OR reference_rows_emitted >= 0);
ALTER TABLE import_run_files ADD COLUMN output_tables TEXT;
ALTER TABLE import_run_files ADD COLUMN processing_role TEXT;
