-- M3 升级前纯只读检查：返回必须为空，否则禁止执行应用脚本。
-- 此查询使用旧表字段提前计算迁移后身份，不依赖新增列。
SELECT
  0 AS jijia_account_id,
  api_code,
  SHA2(
    CASE
      WHEN source_primary_key IS NOT NULL AND TRIM(source_primary_key) <> ''
        THEN CONCAT('pk:', TRIM(source_primary_key))
      ELSE CONCAT('hash:', data_hash)
    END,
    256
  ) AS record_identity,
  COUNT(*) AS duplicate_count
FROM raw_api_data
GROUP BY api_code, record_identity
HAVING COUNT(*) > 1;
