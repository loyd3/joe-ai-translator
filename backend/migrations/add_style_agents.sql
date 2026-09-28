-- 系统级文风智能体 + 翻译任务关联
CREATE TABLE IF NOT EXISTS writing_style_agents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL COMMENT '文风名称',
  description TEXT NULL COMMENT '一句话定位',
  preset_key VARCHAR(50) NULL COMMENT '来源预设 key',
  config JSON NOT NULL COMMENT '结构化文风配置',
  is_default TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否默认文风',
  source VARCHAR(32) NULL DEFAULT 'manual' COMMENT 'preset|manual|extract',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE literary_translations
  ADD COLUMN IF NOT EXISTS style_agent_id INT NULL COMMENT '选用的文风智能体' AFTER user_requirements;

-- MySQL 8.0.29 以下不支持 ADD COLUMN IF NOT EXISTS，可用下方幂等方式手工执行
-- ALTER TABLE literary_translations ADD COLUMN style_agent_id INT NULL COMMENT '选用的文风智能体' AFTER user_requirements;
