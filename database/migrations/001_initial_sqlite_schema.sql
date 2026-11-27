CREATE TABLE data_sources (
    source_dataset TEXT PRIMARY KEY NOT NULL,
    display_name TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE source_files (
    source_dataset TEXT NOT NULL,
    source_file TEXT NOT NULL,
    snapshot_group TEXT,
    snapshot_type TEXT,
    notes TEXT,
    PRIMARY KEY (source_dataset, source_file),
    FOREIGN KEY (source_dataset) REFERENCES data_sources (source_dataset)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE import_runs (
    import_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_status TEXT NOT NULL CHECK (run_status IN ('running', 'succeeded', 'failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    pipeline_version TEXT NOT NULL,
    source_fingerprint TEXT,
    quality_report TEXT,
    notes TEXT
);

CREATE INDEX idx_import_runs_fingerprint_status
    ON import_runs (source_fingerprint, run_status);

CREATE TABLE import_run_files (
    import_run_id INTEGER NOT NULL,
    source_dataset TEXT NOT NULL,
    source_file TEXT NOT NULL,
    rows_read INTEGER NOT NULL CHECK (rows_read >= 0),
    rows_loaded INTEGER NOT NULL CHECK (rows_loaded >= 0),
    rows_rejected INTEGER NOT NULL CHECK (rows_rejected >= 0),
    import_status TEXT NOT NULL CHECK (import_status IN ('succeeded', 'partial', 'failed')),
    notes TEXT,
    PRIMARY KEY (import_run_id, source_dataset, source_file),
    FOREIGN KEY (import_run_id) REFERENCES import_runs (import_run_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (source_dataset, source_file)
        REFERENCES source_files (source_dataset, source_file)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CHECK (rows_loaded + rows_rejected <= rows_read)
);

CREATE TABLE skills (
    skill_id TEXT PRIMARY KEY NOT NULL,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,
    match_policy TEXT NOT NULL CHECK (
        match_policy IN ('approved_aliases', 'exact_only', 'exclude_pending_review')
    ),
    review_status TEXT NOT NULL,
    observed_alias_count INTEGER NOT NULL DEFAULT 0 CHECK (observed_alias_count >= 0),
    observed_source_count INTEGER NOT NULL DEFAULT 0 CHECK (observed_source_count >= 0),
    observed_job_skill_occurrences INTEGER NOT NULL DEFAULT 0
        CHECK (observed_job_skill_occurrences >= 0),
    notes TEXT
);

CREATE TABLE skill_aliases (
    alias_normalized TEXT NOT NULL,
    alias_label TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    match_policy TEXT NOT NULL CHECK (
        match_policy IN ('approved_aliases', 'exact_only', 'exclude_pending_review')
    ),
    review_status TEXT NOT NULL,
    observed_source_count INTEGER NOT NULL DEFAULT 0 CHECK (observed_source_count >= 0),
    observed_job_skill_occurrences INTEGER NOT NULL DEFAULT 0
        CHECK (observed_job_skill_occurrences >= 0),
    notes TEXT,
    PRIMARY KEY (alias_normalized, skill_id),
    FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX idx_skill_aliases_skill_id
    ON skill_aliases (skill_id);

CREATE TABLE jobs (
    record_id TEXT PRIMARY KEY NOT NULL,
    source_dataset TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number INTEGER NOT NULL CHECK (source_row_number >= 1),
    source_record_id TEXT,
    record_origin TEXT,
    source_platform TEXT,
    title TEXT,
    title_short TEXT,
    company TEXT,
    country TEXT,
    city TEXT,
    region TEXT,
    location_raw TEXT,
    work_mode_raw TEXT,
    remote_flag TEXT,
    employment_type_raw TEXT,
    experience_raw TEXT,
    category_raw TEXT,
    description TEXT,
    posted_at TEXT,
    source_updated_at TEXT,
    source_date_field TEXT,
    salary_raw TEXT,
    salary_rate TEXT,
    salary_year_avg TEXT,
    salary_hour_avg TEXT,
    salary_currency TEXT,
    salary_basis TEXT,
    salary_source TEXT,
    salary_provenance_status TEXT,
    skills TEXT,
    skills_original TEXT,
    skills_source TEXT,
    skills_enrichment_status TEXT,
    source_url TEXT,
    listing_status TEXT,
    snapshot_type TEXT,
    exact_duplicate_within_source TEXT,
    data_quality_flags TEXT,
    UNIQUE (record_id, source_dataset, source_file),
    FOREIGN KEY (source_dataset, source_file)
        REFERENCES source_files (source_dataset, source_file)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX idx_jobs_source_dataset
    ON jobs (source_dataset);

CREATE INDEX idx_jobs_country
    ON jobs (country);

CREATE INDEX idx_jobs_title
    ON jobs (title);

CREATE INDEX idx_jobs_posted_at
    ON jobs (posted_at);

CREATE TABLE job_skills (
    record_id TEXT NOT NULL,
    source_dataset TEXT NOT NULL,
    source_file TEXT NOT NULL,
    skill_raw TEXT NOT NULL,
    skill_normalized TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    skill_category TEXT NOT NULL,
    skill_match_policy TEXT NOT NULL CHECK (
        skill_match_policy IN ('approved_aliases', 'exact_only', 'exclude_pending_review')
    ),
    skill_review_status TEXT NOT NULL,
    skill_provenance TEXT,
    skill_status TEXT,
    PRIMARY KEY (record_id, skill_id),
    FOREIGN KEY (record_id, source_dataset, source_file)
        REFERENCES jobs (record_id, source_dataset, source_file)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX idx_job_skills_skill_id_record_id
    ON job_skills (skill_id, record_id);

CREATE TABLE skill_observations (
    source_dataset TEXT NOT NULL,
    skill_raw TEXT NOT NULL,
    skill_normalized TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL CHECK (occurrence_count >= 0),
    PRIMARY KEY (source_dataset, skill_normalized, skill_raw),
    FOREIGN KEY (source_dataset) REFERENCES data_sources (source_dataset)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX idx_skill_observations_normalized
    ON skill_observations (skill_normalized);

CREATE TABLE learning_resources (
    resource_id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    provider TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    level TEXT NOT NULL,
    access_status TEXT NOT NULL,
    cost_status TEXT NOT NULL CHECK (
        cost_status IN ('free_verified', 'some_free_options', 'conditional_or_mixed', 'cost_unverified')
    ),
    account_requirement TEXT NOT NULL,
    credential TEXT NOT NULL,
    resource_url TEXT NOT NULL CHECK (substr(resource_url, 1, 8) = 'https://'),
    verification_status TEXT NOT NULL,
    verified_on TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE learning_resource_skills (
    resource_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    PRIMARY KEY (resource_id, skill_id),
    FOREIGN KEY (resource_id) REFERENCES learning_resources (resource_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX idx_learning_resource_skills_skill_id
    ON learning_resource_skills (skill_id, resource_id);

CREATE TABLE learning_resource_languages (
    resource_id TEXT NOT NULL,
    language_label TEXT NOT NULL,
    PRIMARY KEY (resource_id, language_label),
    FOREIGN KEY (resource_id) REFERENCES learning_resources (resource_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_learning_resource_languages_label
    ON learning_resource_languages (language_label, resource_id);
