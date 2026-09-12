SET SESSION time_zone = '+00:00';

-- 仅回滚查询索引，不修改或删除任何退货订单数据。
ALTER TABLE sale_return_order
  DROP INDEX idx_sale_return_created,
  ALGORITHM=INPLACE,
  LOCK=NONE;
