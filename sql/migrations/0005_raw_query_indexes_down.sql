SET SESSION time_zone = '+00:00';

-- 仅回滚 Web 查询索引，不修改或删除任何同步数据。
ALTER TABLE raw_api_data
  DROP INDEX idx_raw_created,
  DROP INDEX idx_raw_account_api_created,
  DROP INDEX idx_raw_last_observed,
  DROP INDEX idx_raw_account_last_observed,
  ALGORITHM=INPLACE,
  LOCK=NONE;
