-- 修复 ai_config.id 非自增导致保存配置失败：
--   (1364) Field 'id' doesn't have a default value
--
-- 执行：
-- mysql -u root -p aitranslator < backend/migrations/007_fix_ai_config_id_autoincrement.sql

-- 1) 确保 id 列存在且为主键
ALTER TABLE ai_config
  MODIFY COLUMN id INT NOT NULL;

-- 2) 将 id 改为自增（核心修复）
ALTER TABLE ai_config
  MODIFY COLUMN id INT NOT NULL AUTO_INCREMENT;
