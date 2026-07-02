-- 接口配置快照表：可选地把 YAML 配置同步进数据库，便于排查某次运行使用了哪些接口定义。
CREATE TABLE IF NOT EXISTS api_config (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  api_code VARCHAR(100) NOT NULL,
  api_name VARCHAR(255) NOT NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  method VARCHAR(20) NOT NULL DEFAULT 'POST',
  path VARCHAR(500) NOT NULL,
  config_json JSON NOT NULL,
  remark VARCHAR(500) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_api_config_api_code (api_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 同步批次表：一次程序运行对应一条批次记录，用来汇总本次运行的整体状态。
CREATE TABLE IF NOT EXISTS sync_batch (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sync_batch_no VARCHAR(64) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'running',
  started_at DATETIME NOT NULL,
  finished_at DATETIME NULL,
  total_api_count INT NOT NULL DEFAULT 0,
  success_api_count INT NOT NULL DEFAULT 0,
  failed_api_count INT NOT NULL DEFAULT 0,
  message VARCHAR(1000) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_sync_batch_no (sync_batch_no),
  KEY idx_sync_batch_status_started_at (status, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 单接口执行日志：一个批次内每个 API 各写一条，便于定位具体失败接口。
CREATE TABLE IF NOT EXISTS sync_api_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sync_batch_no VARCHAR(64) NOT NULL,
  api_code VARCHAR(100) NOT NULL,
  status VARCHAR(30) NOT NULL,
  request_count INT NOT NULL DEFAULT 0,
  success_count INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  started_at DATETIME NOT NULL,
  finished_at DATETIME NULL,
  error_message TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_sync_api_log_batch (sync_batch_no),
  KEY idx_sync_api_log_api_status (api_code, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 原始数据备份表：所有 API 返回的单条 JSON 都写到这里，是本项目最核心的数据落点。
CREATE TABLE IF NOT EXISTS raw_api_data (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  api_code VARCHAR(100) NOT NULL,
  source_primary_key VARCHAR(255) NULL,
  data_hash CHAR(64) NOT NULL,
  raw_json JSON NOT NULL,
  data_date DATE NULL,
  sync_batch_no VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_raw_api_primary_key (api_code, source_primary_key),
  UNIQUE KEY uk_raw_api_data_hash (api_code, data_hash),
  KEY idx_raw_api_data_date (api_code, data_date),
  KEY idx_raw_api_batch (sync_batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 同步检查点表：记录每个 API 最近一次同步的分页摘要或后续增量游标。
CREATE TABLE IF NOT EXISTS sync_checkpoint (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  api_code VARCHAR(100) NOT NULL,
  checkpoint_value VARCHAR(255) NULL,
  checkpoint_time DATETIME NULL,
  last_sync_batch_no VARCHAR(64) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_sync_checkpoint_api_code (api_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 失败请求明细表：保存最终重试失败的请求上下文，用于排查和必要时人工重放。
CREATE TABLE IF NOT EXISTS failed_request_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sync_batch_no VARCHAR(64) NULL,
  api_code VARCHAR(100) NOT NULL,
  request_url VARCHAR(1000) NULL,
  request_method VARCHAR(20) NOT NULL DEFAULT 'POST',
  request_params JSON NULL,
  response_status_code INT NULL,
  response_body MEDIUMTEXT NULL,
  error_message TEXT NULL,
  retry_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_failed_request_api_created_at (api_code, created_at),
  KEY idx_failed_request_batch (sync_batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
