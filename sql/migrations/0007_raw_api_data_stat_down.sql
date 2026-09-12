SET SESSION time_zone = '+00:00';

-- 仅删除可由 raw_api_data 重建的统计投影，不修改原始数据。
DROP TABLE raw_api_data_stat;
