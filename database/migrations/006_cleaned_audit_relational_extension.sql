-- Loss-preserving extension for the finalized cleaned-audit CSV.
-- All 123 CSV fields are stored with their exact names; the original row JSON
-- remains available for source-level traceability. Existing jobs columns remain
-- the application-facing compatibility projection.
CREATE TABLE job_cleaning_audit (
    "record_id" TEXT NOT NULL PRIMARY KEY,
    "source_dataset" TEXT NOT NULL,
    "source_file" TEXT NOT NULL,
    "source_row_number" INTEGER NOT NULL CHECK ("source_row_number" >= 1),
    "source_record_id" TEXT,
    "source_record_id_duplicate_occurrence" TEXT,
    "record_origin" TEXT,
    "source_platform" TEXT,
    "title_raw" TEXT,
    "title_clean" TEXT,
    "title_key" TEXT,
    "company_raw" TEXT,
    "company_clean" TEXT,
    "country_raw" TEXT,
    "country_standardized" TEXT,
    "location_scope" TEXT,
    "city_raw" TEXT,
    "region_raw" TEXT,
    "location_raw" TEXT,
    "work_mode_raw" TEXT,
    "remote_flag_raw" TEXT,
    "employment_type_raw" TEXT,
    "experience_raw" TEXT,
    "experience_years_min" INTEGER,
    "experience_years_max" INTEGER,
    "experience_parse_status" TEXT,
    "category_raw" TEXT,
    "description_raw" TEXT,
    "description_char_count" INTEGER,
    "posted_at_raw" TEXT,
    "posted_at_iso" TEXT,
    "source_updated_at_raw" TEXT,
    "source_updated_at_iso" TEXT,
    "source_collected_at_raw" TEXT,
    "source_collected_at_iso" TEXT,
    "collection_date_field" TEXT,
    "source_date_field" TEXT,
    "date_quality_flags" TEXT,
    "salary_raw" TEXT,
    "salary_candidate_raw" TEXT,
    "salary_source_field_used" TEXT,
    "salary_local_source_value" TEXT,
    "salary_usd_source_value" TEXT,
    "salary_range_est_source_value" TEXT,
    "salary_currency_raw" TEXT,
    "salary_basis_raw" TEXT,
    "salary_rate_raw" TEXT,
    "salary_source_raw" TEXT,
    "salary_sources_raw" TEXT,
    "salary_fill_source_raw" TEXT,
    "salary_estimate_source_url" TEXT,
    "salary_estimate_source_date" TEXT,
    "salary_estimate_source_date_status" TEXT,
    "salary_value_type" TEXT,
    "salary_provenance_status" TEXT,
    "salary_parse_status" TEXT,
    "salary_amount_1_original_currency" REAL,
    "salary_amount_2_original_currency" REAL,
    "salary_min_original_currency" REAL,
    "salary_max_original_currency" REAL,
    "salary_midpoint_original_currency" REAL,
    "salary_range_kind" TEXT,
    "salary_currency_code" TEXT,
    "salary_currency_detection_status" TEXT,
    "salary_period_code" TEXT,
    "salary_period_detection_status" TEXT,
    "salary_annualized_min_native" REAL,
    "salary_annualized_max_native" REAL,
    "salary_annualized_midpoint_native" REAL,
    "salary_reporting_currency" TEXT,
    "salary_fx_rate_to_reporting_currency" REAL,
    "salary_fx_rate_source" TEXT,
    "salary_fx_rate_date" TEXT,
    "salary_annualized_min_reporting_currency" REAL,
    "salary_annualized_max_reporting_currency" REAL,
    "salary_comparability_status" TEXT,
    "salary_statistics_eligible" TEXT,
    "salary_integrity_flags" TEXT,
    "salary_iqr_outlier_flag" TEXT,
    "skills_raw" TEXT,
    "skills_base_raw" TEXT,
    "skills_tokens_json" TEXT,
    "skill_ids_json" TEXT,
    "skill_token_count_raw" INTEGER,
    "skill_token_count_unique" INTEGER,
    "skill_canonical_id_count" INTEGER,
    "skill_duplicate_token_count" INTEGER,
    "skills_source_raw" TEXT,
    "skills_enrichment_status" TEXT,
    "source_url_raw" TEXT,
    "source_url_syntax_status" TEXT,
    "listing_status" TEXT,
    "snapshot_type" TEXT,
    "exact_duplicate_within_source" TEXT,
    "encoding_suspected_mojibake" TEXT,
    "data_quality_flags" TEXT,
    "source_row_json" TEXT,
    "salary_original" TEXT,
    "salary_source_value_type" TEXT,
    "salary_estimation_status" TEXT,
    "salary_estimate_currency_code" TEXT,
    "salary_estimation_method" TEXT,
    "salary_estimation_source" TEXT,
    "salary_estimation_confidence" TEXT,
    "salary_estimate_reference_count" INTEGER,
    "salary_estimation_as_of_date" TEXT,
    "salary_annualized_midpoint_reporting_currency" REAL,
    "salary_annual_min_usd" REAL,
    "salary_annual_salary_usd" REAL,
    "salary_annual_max_usd" REAL,
    "salary_annual_min_egp" REAL,
    "salary_annual_salary_egp" REAL,
    "salary_annual_max_egp" REAL,
    "salary_annual_min_sar" REAL,
    "salary_annual_salary_sar" REAL,
    "salary_annual_max_sar" REAL,
    "salary_estimate_range_basis" TEXT,
    "role_family" TEXT,
    "seniority_band" TEXT,
    "location_clean" TEXT,
    "location_key" TEXT,
    "work_mode_standardized" TEXT,
    "employment_type_standardized" TEXT,
    FOREIGN KEY ("record_id", "source_dataset", "source_file")
        REFERENCES "jobs" ("record_id", "source_dataset", "source_file")
        ON UPDATE CASCADE
        ON DELETE CASCADE
) WITHOUT ROWID;

CREATE INDEX idx_job_cleaning_audit_source_file
    ON job_cleaning_audit (source_dataset, source_file);
CREATE INDEX idx_job_cleaning_audit_country
    ON job_cleaning_audit (country_standardized);
CREATE INDEX idx_job_cleaning_audit_title_key
    ON job_cleaning_audit (title_key);
CREATE INDEX idx_job_cleaning_audit_posted_at
    ON job_cleaning_audit (posted_at_iso);
CREATE INDEX idx_job_cleaning_audit_salary_status
    ON job_cleaning_audit (salary_value_type, salary_statistics_eligible);
CREATE INDEX idx_job_cleaning_audit_role_family
    ON job_cleaning_audit (role_family);

CREATE VIEW cleaned_jobs AS
SELECT * FROM job_cleaning_audit;

CREATE VIEW actual_salary_rows AS
SELECT * FROM job_cleaning_audit
WHERE salary_value_type = 'actual_reported'
  AND salary_statistics_eligible = 'yes';

CREATE VIEW synthetic_salary_estimates AS
SELECT * FROM job_cleaning_audit
WHERE salary_value_type = 'estimated_synthetic';
