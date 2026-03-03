-- ========================================================-- AI Translator 数据库初始化脚本-- 数据库名: aitranslator-- 字符集: utf8mb4 (支持中文、emoji 等)-- ========================================================-- 创建数据库
CREATE DATABASE IF NOT EXISTS aitranslator
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE aitranslator;-- ========================================================-- 用户表（认证用）-- ========================================================DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    email VARCHAR(255) NOT NULL UNIQUE COMMENT '邮箱',
    hashed_password VARCHAR(255) NOT NULL COMMENT '密码哈希',
    display_name VARCHAR(100) NULL COMMENT '显示名称',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_email (email),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ========================================================-- 翻译历史记录表-- ========================================================
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='翻译历史记录表';-- ========================================================-- 批量翻译任务表-- ========================================================
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='批量翻译任务表';-- ========================================================-- 文学全文翻译任务表（新增）-- ========================================================
DROP TABLE IF EXISTS literary_translations;

CREATE TABLE literary_translations (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    title VARCHAR(500) NULL COMMENT '文本标题',
    source_text LONGTEXT NOT NULL COMMENT '原文',
    
    -- 四步翻译结果
    step1_translation LONGTEXT NULL COMMENT '第一步：初译',
    step2_verification LONGTEXT NULL COMMENT '第二步：校验',
    step3_revision LONGTEXT NULL COMMENT '第三步：修改',
    step4_finalization LONGTEXT NULL COMMENT '第四步：定稿',
    
    -- 当前步骤和状态
    current_step INT DEFAULT 1 COMMENT '当前步骤 1-4',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '任务状态：pending/translating/verifying/revising/finalizing/completed/failed',
    
    -- 语言和配置
    source_lang VARCHAR(10) NOT NULL COMMENT '源语言',
    target_lang VARCHAR(10) NOT NULL COMMENT '目标语言',
    literary_type VARCHAR(50) DEFAULT 'general' COMMENT '文学类型: poetry, prose, novel, drama, general',
    
    -- 三美原则评分
    beauty_sound_score DECIMAL(3,1) NULL COMMENT '音美评分 0-10',
    beauty_word_score DECIMAL(3,1) NULL COMMENT '词美评分 0-10',
    beauty_meaning_score DECIMAL(3,1) NULL COMMENT '意美评分 0-10',
    
    -- AI 信息
    ai_provider VARCHAR(50) NULL COMMENT 'AI提供商',
    ai_model VARCHAR(100) NULL COMMENT 'AI模型',
    
    -- 参考文档关联
    reference_document_ids JSON NULL COMMENT '关联的参考文档ID列表',
    
    -- 用户翻译前指明的需求（风格、术语等）
    user_requirements TEXT NULL COMMENT '用户翻译需求说明',
    
    -- 用户编辑的最终译文
    final_translation LONGTEXT NULL COMMENT '用户编辑后的最终译文',
    
    -- 工作流失败时记录的错误原因
    error_message TEXT NULL COMMENT '翻译流程失败时的错误信息',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    
    INDEX idx_status (status),
    INDEX idx_literary_type (literary_type),
    INDEX idx_created_at (created_at),
    INDEX idx_current_step (current_step)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文学全文翻译任务表';-- ========================================================-- 文学翻译段落表（用于对照查看）（新增）-- ========================================================
DROP TABLE IF EXISTS literary_paragraphs;

CREATE TABLE literary_paragraphs (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    translation_id INT NOT NULL COMMENT '关联的翻译任务ID',
    paragraph_index INT NOT NULL COMMENT '段落序号',
    
    source_text LONGTEXT NOT NULL COMMENT '原文段落',
    translated_text LONGTEXT NULL COMMENT '译文段落',
    
    -- 四步结果
    step1_translation LONGTEXT NULL COMMENT '第一步译文',
    step2_verification LONGTEXT NULL COMMENT '第二步译文',
    step3_revision LONGTEXT NULL COMMENT '第三步译文',
    step4_finalization LONGTEXT NULL COMMENT '第四步译文',
    
    -- 用户编辑
    user_edited_text LONGTEXT NULL COMMENT '用户编辑的译文',
    is_edited TINYINT(1) DEFAULT 0 COMMENT '是否被用户编辑过',
    
    -- 三美评分
    beauty_sound_score DECIMAL(3,1) NULL COMMENT '音美评分',
    beauty_word_score DECIMAL(3,1) NULL COMMENT '词美评分',
    beauty_meaning_score DECIMAL(3,1) NULL COMMENT '意美评分',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_translation_id (translation_id),
    INDEX idx_paragraph_index (paragraph_index),
    FOREIGN KEY (translation_id) REFERENCES literary_translations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文学翻译段落表';-- ========================================================-- RAG 参考文档表（新增）-- ========================================================
DROP TABLE IF EXISTS reference_documents;

CREATE TABLE reference_documents (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    name VARCHAR(255) NOT NULL COMMENT '文档名称',
    file_type VARCHAR(50) NOT NULL COMMENT '文件类型: txt, md, docx, pdf',
    file_size INT NOT NULL COMMENT '文件大小（字节）',
    
    -- 文档内容
    content LONGTEXT NOT NULL COMMENT '文档内容',
    
    -- 文档类型
    doc_type VARCHAR(50) DEFAULT 'general' COMMENT '文档类型: terminology, style_guide, reference, general',
    
    -- 语言对
    source_lang VARCHAR(10) NULL COMMENT '源语言',
    target_lang VARCHAR(10) NULL COMMENT '目标语言',
    
    -- 描述
    description TEXT NULL COMMENT '文档描述',
    
    -- 是否启用
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_doc_type (doc_type),
    INDEX idx_is_active (is_active),
    INDEX idx_source_lang (source_lang),
    INDEX idx_target_lang (target_lang)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RAG参考文档表';-- ========================================================-- 系统配置表 (可选扩展)-- ========================================================
DROP TABLE IF EXISTS system_settings;

CREATE TABLE system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    setting_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    setting_value TEXT COMMENT '配置值',
    description VARCHAR(255) COMMENT '配置说明',
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_setting_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';-- ========================================================-- 插入默认配置-- ========================================================
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('app_version', '1.1.0', '应用版本号'),
('default_source_lang', 'auto', '默认源语言'),
('default_target_lang', 'en', '默认目标语言'),
('max_text_length', '5000', '单次最大翻译字符数'),
('literary_translation_enabled', '1', '是否启用文学翻译功能');-- ========================================================-- 专业词库表（新增）-- ========================================================
DROP TABLE IF EXISTS professional_terms;

CREATE TABLE professional_terms (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    source_term VARCHAR(500) NOT NULL COMMENT '源语言词汇',
    target_term VARCHAR(500) NOT NULL COMMENT '目标语言翻译',
    literary_type VARCHAR(50) NOT NULL COMMENT '文学类型: poetry, prose, novel, drama, general',
    category VARCHAR(100) NULL COMMENT '词汇分类/领域',
    source_lang VARCHAR(10) NOT NULL COMMENT '源语言',
    target_lang VARCHAR(10) NOT NULL COMMENT '目标语言',
    usage_count INT DEFAULT 1 COMMENT '使用次数',
    description TEXT NULL COMMENT '词汇说明/例句',
    translation_id INT NULL COMMENT '来源翻译任务ID',
    is_verified TINYINT(1) DEFAULT 1 COMMENT '是否审核通过',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_literary_type (literary_type),
    INDEX idx_category (category),
    INDEX idx_source_lang (source_lang),
    INDEX idx_target_lang (target_lang),
    INDEX idx_is_verified (is_verified),
    INDEX idx_source_term (source_term),
    FOREIGN KEY (translation_id) REFERENCES literary_translations(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='专业词汇库';-- ========================================================-- 翻译词汇总结表（新增）-- ========================================================
DROP TABLE IF EXISTS translation_term_summaries;

CREATE TABLE translation_term_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    translation_id INT NOT NULL COMMENT '关联的翻译任务ID',
    terms JSON NOT NULL COMMENT '本次翻译涉及的专业词汇列表',
    total_terms INT DEFAULT 0 COMMENT '词汇总数',
    new_terms INT DEFAULT 0 COMMENT '新增词汇数',
    updated_terms INT DEFAULT 0 COMMENT '更新词汇数',
    summary_text TEXT NULL COMMENT 'AI对专业词汇的总结说明',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX idx_translation_id (translation_id),
    FOREIGN KEY (translation_id) REFERENCES literary_translations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='翻译任务专业词汇总结';-- ========================================================-- 查看创建结果-- ========================================================
SHOW TABLES;

SELECT 
    table_name AS '表名',
    table_comment AS '说明',
    table_rows AS '行数'
FROM information_schema.tables 
WHERE table_schema = 'aitranslator';
