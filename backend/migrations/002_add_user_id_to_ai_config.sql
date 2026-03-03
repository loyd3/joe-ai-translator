-- 为已存在的 ai_config 表添加 user_id 列（与用户关联）
-- 当报错 Unknown column 'ai_config.user_id' 时执行本文件。
-- 执行：mysql -u root -p aitranslator < backend/migrations/add_user_id_to_ai_config.sql
-- 若 user_id 已存在会报 Duplicate column，可忽略。

ALTER TABLE ai_config ADD COLUMN user_id INT NULL COMMENT '用户ID' AFTER id;
ALTER TABLE ai_config ADD UNIQUE INDEX uk_ai_config_user_id (user_id);
ALTER TABLE ai_config ADD CONSTRAINT fk_ai_config_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
