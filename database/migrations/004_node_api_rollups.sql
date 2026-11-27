CREATE TABLE api_scope_rollups (
    source_dataset TEXT NOT NULL,
    country_key TEXT NOT NULL,
    country_label TEXT NOT NULL,
    work_mode_key TEXT NOT NULL,
    work_mode_label TEXT NOT NULL,
    experience_key TEXT NOT NULL,
    experience_label TEXT NOT NULL,
    job_record_count INTEGER NOT NULL CHECK (job_record_count >= 0),
    eligible_job_record_count INTEGER NOT NULL CHECK (eligible_job_record_count >= 0),
    PRIMARY KEY (source_dataset, country_key, work_mode_key, experience_key)
) WITHOUT ROWID;

CREATE INDEX idx_api_scope_country
    ON api_scope_rollups (country_key, source_dataset, work_mode_key, experience_key);

CREATE TABLE api_scope_skill_rollups (
    source_dataset TEXT NOT NULL,
    country_key TEXT NOT NULL,
    work_mode_key TEXT NOT NULL,
    experience_key TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,
    job_record_count INTEGER NOT NULL CHECK (job_record_count > 0),
    PRIMARY KEY (source_dataset, country_key, work_mode_key, experience_key, skill_id),
    FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) WITHOUT ROWID;

CREATE INDEX idx_api_scope_skill_by_skill
    ON api_scope_skill_rollups (skill_id, source_dataset, country_key, work_mode_key, experience_key);

CREATE INDEX idx_api_scope_skill_country
    ON api_scope_skill_rollups (country_key, source_dataset, work_mode_key, experience_key, skill_id);

CREATE TABLE api_role_scope_rollups (
    source_dataset TEXT NOT NULL,
    country_key TEXT NOT NULL,
    country_label TEXT NOT NULL,
    work_mode_key TEXT NOT NULL,
    work_mode_label TEXT NOT NULL,
    experience_key TEXT NOT NULL,
    experience_label TEXT NOT NULL,
    role_id TEXT NOT NULL,
    role_display_title TEXT NOT NULL,
    job_record_count INTEGER NOT NULL CHECK (job_record_count >= 0),
    eligible_job_record_count INTEGER NOT NULL CHECK (eligible_job_record_count >= 0),
    records_with_salary_text INTEGER NOT NULL CHECK (records_with_salary_text >= 0),
    records_with_explicit_currency INTEGER NOT NULL CHECK (records_with_explicit_currency >= 0),
    records_with_unverified_salary INTEGER NOT NULL CHECK (records_with_unverified_salary >= 0),
    PRIMARY KEY (source_dataset, country_key, work_mode_key, experience_key, role_id)
) WITHOUT ROWID;

CREATE INDEX idx_api_role_scope_country
    ON api_role_scope_rollups (country_key, source_dataset, work_mode_key, experience_key, role_id);

CREATE INDEX idx_api_role_scope_role
    ON api_role_scope_rollups (role_id, source_dataset, country_key, work_mode_key, experience_key);

CREATE TABLE api_role_skill_rollups (
    source_dataset TEXT NOT NULL,
    country_key TEXT NOT NULL,
    work_mode_key TEXT NOT NULL,
    experience_key TEXT NOT NULL,
    role_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,
    job_record_count INTEGER NOT NULL CHECK (job_record_count > 0),
    PRIMARY KEY (source_dataset, country_key, work_mode_key, experience_key, role_id, skill_id),
    FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) WITHOUT ROWID;

CREATE INDEX idx_api_role_skill_by_skill
    ON api_role_skill_rollups (skill_id, source_dataset, country_key, work_mode_key, experience_key, role_id);

CREATE INDEX idx_api_role_skill_by_country
    ON api_role_skill_rollups (country_key, source_dataset, work_mode_key, experience_key, role_id, skill_id);

CREATE TABLE api_source_field_coverage (
    source_dataset TEXT PRIMARY KEY NOT NULL,
    job_record_count INTEGER NOT NULL CHECK (job_record_count >= 0),
    title_records INTEGER NOT NULL CHECK (title_records >= 0),
    company_records INTEGER NOT NULL CHECK (company_records >= 0),
    country_records INTEGER NOT NULL CHECK (country_records >= 0),
    city_records INTEGER NOT NULL CHECK (city_records >= 0),
    description_records INTEGER NOT NULL CHECK (description_records >= 0),
    source_url_records INTEGER NOT NULL CHECK (source_url_records >= 0),
    salary_raw_records INTEGER NOT NULL CHECK (salary_raw_records >= 0),
    posted_at_records INTEGER NOT NULL CHECK (posted_at_records >= 0),
    work_mode_raw_records INTEGER NOT NULL CHECK (work_mode_raw_records >= 0),
    FOREIGN KEY (source_dataset) REFERENCES data_sources (source_dataset)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) WITHOUT ROWID;

CREATE TABLE api_historical_month_rollups (
    source_dataset TEXT NOT NULL,
    month TEXT NOT NULL,
    country_key TEXT NOT NULL,
    country_label TEXT NOT NULL,
    job_record_count INTEGER NOT NULL CHECK (job_record_count > 0),
    PRIMARY KEY (source_dataset, month, country_key)
) WITHOUT ROWID;
