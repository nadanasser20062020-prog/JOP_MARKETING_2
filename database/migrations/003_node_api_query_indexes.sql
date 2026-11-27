CREATE INDEX idx_jobs_normalized_title_source
    ON jobs (lower(trim(title)), source_dataset);

CREATE INDEX idx_jobs_normalized_country_source
    ON jobs (lower(trim(country)), source_dataset);

CREATE INDEX idx_jobs_source_posted_at
    ON jobs (source_dataset, posted_at);
