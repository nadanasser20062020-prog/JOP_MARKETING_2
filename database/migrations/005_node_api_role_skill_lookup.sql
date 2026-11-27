CREATE INDEX idx_api_role_skill_by_role
    ON api_role_skill_rollups (
        role_id, source_dataset, country_key, work_mode_key, experience_key, skill_id
    );
