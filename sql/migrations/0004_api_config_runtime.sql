-- 运行前先备份 api_config；本迁移只扩展现有接口配置表，不修改同步数据表。
ALTER TABLE api_config
  ADD COLUMN platform_enabled TINYINT(1) NOT NULL DEFAULT 0 AFTER enabled,
  ADD COLUMN config_version INT NOT NULL DEFAULT 1 AFTER config_json,
  ADD COLUMN config_hash CHAR(64) NULL AFTER config_version,
  ADD COLUMN read_only_verified TINYINT(1) NOT NULL DEFAULT 0 AFTER config_hash,
  ADD COLUMN official_doc_id INT NULL AFTER read_only_verified,
  ADD COLUMN classification VARCHAR(64) NULL AFTER official_doc_id,
  ADD COLUMN execution_stage VARCHAR(64) NULL AFTER classification,
  ADD COLUMN published_at DATETIME NULL AFTER execution_stage;

UPDATE api_config
SET config_hash = SHA2(CAST(config_json AS CHAR), 256),
    published_at = COALESCE(updated_at, created_at)
WHERE config_hash IS NULL OR published_at IS NULL;

ALTER TABLE api_config
  MODIFY config_hash CHAR(64) NOT NULL,
  MODIFY published_at DATETIME NOT NULL,
  ADD KEY idx_api_config_enabled (enabled, platform_enabled, read_only_verified);

-- 迁移完成后必须运行配置发布命令，只有通过官方目录校验的接口才会变为只读已核验。
