-- ========================================================
-- AI Translator 数据库初始化脚本
-- 数据库名: aitranslator
-- 字符集: utf8mb4 (支持中文、emoji 等)
-- ========================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS aitranslator
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE aitranslator;

-- ========================================================
-- 翻译历史记录表
-- ========================================================
DROP TABLE IF EXISTS translation_history;

CREATE TABLE translation_history (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    source_text TEXT NOT NULL COMMENT '源文本',
    translated_text TEXT NOT NULL COMMENT '翻译后的文本',
    source_lang VARCHAR(10) DEFAULT 'auto' COMMENT '源语言代码',
    target_lang VARCHAR(10) NOT NULL COMMENT '目标语言代码',
    context TEXT NULL COMMENT '翻译上下文/场景',
    ai_provider VARCHAR(50) NULL COMMENT 'AI 提供商 (openai/deepseek/siliconflow)',
    ai_model VARCHAR(100) NULL COMMENT '使用的 AI 模型',
    is_favorite TINYINT(1) DEFAULT 0 COMMENT '是否收藏 (0=否, 1=是)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_created_at (created_at),
    INDEX idx_is_favorite (is_favorite),
    INDEX idx_source_lang (source_lang),
    INDEX idx_target_lang (target_lang)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='翻译历史记录表';

-- ========================================================
-- 批量翻译任务表
-- ========================================================
DROP TABLE IF EXISTS batch_translations;

CREATE TABLE batch_translations (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    name VARCHAR(255) NULL COMMENT '任务名称',
    source_lang VARCHAR(10) DEFAULT 'auto' COMMENT '源语言代码',
    target_lang VARCHAR(10) NOT NULL COMMENT '目标语言代码',
    items JSON NOT NULL COMMENT '翻译项目列表 (JSON格式)',
    total_items INT DEFAULT 0 COMMENT '总项目数',
    completed_items INT DEFAULT 0 COMMENT '已完成项目数',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '任务状态 (pending/processing/completed/failed)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='批量翻译任务表';

-- ========================================================
-- 系统配置表 (可选扩展)
-- ========================================================
DROP TABLE IF EXISTS system_settings;

CREATE TABLE system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    setting_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    setting_value TEXT COMMENT '配置值',
    description VARCHAR(255) COMMENT '配置说明',
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_setting_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- ========================================================
-- 插入默认配置
-- ========================================================
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('app_version', '1.0.0', '应用版本号'),
('default_source_lang', 'auto', '默认源语言'),
('default_target_lang', 'en', '默认目标语言'),
('max_text_length', '5000', '单次最大翻译字符数');

-- ========================================================
-- 查看创建结果
-- ========================================================
SHOW TABLES;

SELECT 
    table_name AS '表名',
    table_comment AS '说明',
    table_rows AS '行数'
FROM information_schema.tables 
WHERE table_schema = 'aitranslator';
