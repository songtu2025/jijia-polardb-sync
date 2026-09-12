SET SESSION time_zone = '+00:00';

-- M3 既有同步表升级（人工审计后执行，不会自动运行）。
-- 约定：jijia_account_id=0 表示既有 legacy CLI 数据；sync-owned 表不建立 Web 外键。
-- 执行前必须单独执行 0003_sync_scope_and_history_preflight.sql，且确认零重复。
-- 实际执行时必须停止 worker/cron，由同一迁移会话持有 jijia_polardb_sync_task named lock，
-- 持锁后重跑 0003 preflight 的身份、NULL 和 checkpoint 冲突检查，再立即执行本脚本。
-- 本脚本不负责旧快照的正数账号映射，未获得业务确认前不得自动种入。

-- 1. 先加可空字段，便于暂停写入后分步回填。
ALTER TABLE sync_batch
  ADD COLUMN jijia_account_id INT NULL,
  ADD COLUMN sync_job_id INT NULL;
ALTER TABLE sync_api_log
  ADD COLUMN jijia_account_id INT NULL;
ALTER TABLE failed_request_log
  ADD COLUMN jijia_account_id INT NULL;
ALTER TABLE raw_api_data
  ADD COLUMN jijia_account_id INT NULL,
  ADD COLUMN record_identity CHAR(64) NULL,
  ADD COLUMN first_observed_at DATETIME NULL,
  ADD COLUMN last_observed_at DATETIME NULL,
  ADD COLUMN observation_count BIGINT UNSIGNED NULL;
ALTER TABLE sync_checkpoint
  ADD COLUMN jijia_account_id INT NULL,
  ADD COLUMN checkpoint_kind VARCHAR(32) NULL;

-- 2. 回填 legacy 维度和记录身份；不得删除任何 raw 行。
UPDATE sync_batch
SET jijia_account_id = 0,
    updated_at = updated_at
WHERE jijia_account_id IS NULL;
UPDATE sync_api_log
SET jijia_account_id = 0,
    updated_at = updated_at
WHERE jijia_account_id IS NULL;
UPDATE failed_request_log
SET jijia_account_id = 0,
    updated_at = updated_at
WHERE jijia_account_id IS NULL;
UPDATE raw_api_data
SET jijia_account_id = 0,
    record_identity = SHA2(
      CASE
        WHEN source_primary_key IS NOT NULL AND TRIM(source_primary_key) <> ''
          THEN CONCAT('pk:', TRIM(source_primary_key))
        ELSE CONCAT('hash:', data_hash)
      END,
      256
    ),
    first_observed_at = created_at,
    last_observed_at = updated_at,
    observation_count = 1,
    updated_at = updated_at
WHERE jijia_account_id IS NULL OR record_identity IS NULL;
UPDATE sync_checkpoint
SET jijia_account_id = 0,
    checkpoint_kind = 'date_window',
    updated_at = updated_at
WHERE jijia_account_id IS NULL OR checkpoint_kind IS NULL;

-- 3. 迁移 checkpoint_value：合法 JSON 原样保留，旧字符串包入 legacy_value。
ALTER TABLE sync_checkpoint ADD COLUMN checkpoint_value_json JSON NULL;
UPDATE sync_checkpoint
SET checkpoint_value_json = CASE
  WHEN checkpoint_value IS NULL THEN NULL
  WHEN JSON_VALID(checkpoint_value) THEN JSON_EXTRACT(checkpoint_value, '$')
  ELSE JSON_OBJECT('legacy_value', checkpoint_value)
END,
    updated_at = updated_at;
ALTER TABLE sync_checkpoint
  DROP COLUMN checkpoint_value,
  CHANGE COLUMN checkpoint_value_json checkpoint_value JSON NULL;

-- 4. preflight 已确认零重复后，重建唯一键和查询索引。
ALTER TABLE raw_api_data
  DROP INDEX idx_raw_api_data_date,
  DROP INDEX uk_raw_api_primary_key,
  DROP INDEX uk_raw_api_data_hash,
  MODIFY jijia_account_id INT NOT NULL DEFAULT 0,
  MODIFY record_identity CHAR(64) NOT NULL,
  MODIFY first_observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  MODIFY last_observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  MODIFY observation_count BIGINT UNSIGNED NOT NULL DEFAULT 1,
  ADD UNIQUE KEY uk_raw_account_api_identity (jijia_account_id, api_code, record_identity),
  ADD KEY idx_raw_account_api_hash (jijia_account_id, api_code, data_hash),
  ADD KEY idx_raw_account_api_source_pk (jijia_account_id, api_code, source_primary_key),
  ADD KEY idx_raw_api_data_date (jijia_account_id, api_code, data_date);
ALTER TABLE sync_batch
  DROP INDEX idx_sync_batch_status_started_at,
  MODIFY jijia_account_id INT NOT NULL DEFAULT 0,
  ADD UNIQUE KEY uk_sync_batch_job (sync_job_id),
  ADD KEY idx_sync_batch_account_status (jijia_account_id, status, started_at);
ALTER TABLE sync_api_log
  DROP INDEX idx_sync_api_log_api_status,
  MODIFY jijia_account_id INT NOT NULL DEFAULT 0,
  ADD KEY idx_sync_api_log_account_api_status (jijia_account_id, api_code, status);
ALTER TABLE failed_request_log
  DROP INDEX idx_failed_request_api_created_at,
  MODIFY jijia_account_id INT NOT NULL DEFAULT 0,
  ADD KEY idx_failed_request_account_api_created_at (jijia_account_id, api_code, created_at);
ALTER TABLE sync_checkpoint
  DROP INDEX uk_sync_checkpoint_api_code,
  MODIFY jijia_account_id INT NOT NULL DEFAULT 0,
  MODIFY checkpoint_kind VARCHAR(32) NOT NULL DEFAULT 'date_window',
  ADD UNIQUE KEY uk_sync_checkpoint_scope (jijia_account_id, api_code, checkpoint_kind);

-- 5. 历史表仅在启用版本历史的 api_code 写入；本表不因回滚删除数据。
CREATE TABLE IF NOT EXISTS raw_api_data_history (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  jijia_account_id INT NOT NULL DEFAULT 0,
  api_code VARCHAR(100) NOT NULL,
  record_identity CHAR(64) NOT NULL,
  source_primary_key VARCHAR(255) NULL,
  data_hash CHAR(64) NOT NULL,
  raw_json JSON NOT NULL,
  data_date DATE NULL,
  sync_batch_no VARCHAR(64) NOT NULL,
  observed_at DATETIME NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_raw_history_version (jijia_account_id, api_code, record_identity, data_hash),
  KEY idx_raw_history_account_record (jijia_account_id, api_code, record_identity, observed_at),
  KEY idx_raw_history_date (jijia_account_id, api_code, data_date),
  KEY idx_raw_history_batch (sync_batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*
回滚策略：禁止执行破坏性 DDL down。
MySQL DDL 可能隐式提交，删除账号、任务和 checkpoint 维度会造成不可逆的数据归属丢失。
执行本脚本前必须创建可恢复的副本快照；迁移或切换失败时恢复完整快照/PITR。
应用版本回滚必须继续兼容扩展后的表结构，不删除 raw_api_data_history 数据。
*/
