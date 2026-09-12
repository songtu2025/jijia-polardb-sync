SET SESSION time_zone = '+00:00';

-- 只删除可重建的查询投影；raw 快照和历史数据不受影响。
DROP TABLE sale_return_order;
