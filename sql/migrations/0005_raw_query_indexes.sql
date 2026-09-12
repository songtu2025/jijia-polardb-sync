SET SESSION time_zone = '+00:00';

-- Web 只读查询索引；执行前先确认不存在同名或同列顺序的等价索引。
ALTER TABLE raw_api_data
  ADD KEY idx_raw_created (created_at, id),
  ADD KEY idx_raw_account_api_created (jijia_account_id, api_code, created_at, id),
  ADD KEY idx_raw_last_observed (last_observed_at),
  ADD KEY idx_raw_account_last_observed (jijia_account_id, last_observed_at),
  ALGORITHM=INPLACE,
  LOCK=NONE;
