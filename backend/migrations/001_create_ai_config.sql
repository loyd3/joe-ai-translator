-- 创建 ai_config 表（大模型配置，按用户）
-- 当 GET /api/system/ai-config 返回 503「配置表暂不可用」时执行。
-- 执行：mysql -u root -p aitranslator < backend/migrations/create_ai_config.sql
-- 若表已存在会报错，可忽略。

CREATE TABLE IF NOT EXISTS ai_config (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL COMMENT '用户ID',
  provider VARCHAR(50) NOT NULL DEFAULT 'deepseek' COMMENT 'AI 提供商',
  api_key VARCHAR(500) NULL COMMENT 'API Key',
  model VARCHAR(200) NULL COMMENT '模型名称',
  base_url VARCHAR(500) NULL COMMENT '自定义 API 地址',
  temperature FLOAT NULL COMMENT '温度参数',
  max_tokens INT NULL COMMENT '最大 token 数',
  updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_id (user_id),
  INDEX idx_user_id (user_id),
  CONSTRAINT fk_ai_config_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='大模型配置';
