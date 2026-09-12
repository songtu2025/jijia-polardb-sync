SET SESSION time_zone = '+00:00';

-- 迁移前必须停止 worker/cron，并由受控入口持有全局同步锁。
CREATE TABLE IF NOT EXISTS raw_api_data_stat (
  jijia_account_id INT NOT NULL,
  api_code VARCHAR(100) NOT NULL,
  record_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (jijia_account_id, api_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

START TRANSACTION;

DELETE FROM raw_api_data_stat;

INSERT INTO raw_api_data_stat (
  jijia_account_id,
  api_code,
  record_count
)
SELECT
  jijia_account_id,
  api_code,
  COUNT(*)
FROM raw_api_data
GROUP BY jijia_account_id, api_code;

COMMIT;
