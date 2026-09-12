SET SESSION time_zone = '+00:00';

-- 保持现有创建时间倒序语义，避免列表首屏扫描并排序整张投影表。
ALTER TABLE sale_return_order
  ADD KEY idx_sale_return_created (created_at, id),
  ALGORITHM=INPLACE,
  LOCK=NONE;
