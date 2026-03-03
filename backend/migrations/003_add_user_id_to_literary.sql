-- 为 literary_translations 表添加 user_id 列（与用户关联）
-- 当接口返回 503 且提示 Unknown column 'user_id' 时执行本文件。
-- 执行：mysql -u root -p aitranslator < backend/migrations/add_user_id_to_literary.sql
-- 若 user_id 已存在会报 Duplicate column，可忽略。

ALTER TABLE literary_translations ADD COLUMN user_id INT NULL COMMENT '用户ID' AFTER id;
ALTER TABLE literary_translations ADD INDEX idx_literary_translations_user_id (user_id);
