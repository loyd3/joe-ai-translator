-- 外部专业词典 + 任务绑定 + 命中表上限设置
-- mysql -u root -p aitranslator < backend/migrations/add_domain_dictionaries.sql

CREATE TABLE IF NOT EXISTS domain_dictionaries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL COMMENT '词典名称',
  description TEXT NULL COMMENT '说明',
  literary_type VARCHAR(50) NULL COMMENT '领域类型；空或 general=通用',
  source_lang VARCHAR(10) NOT NULL COMMENT '源语言',
  target_lang VARCHAR(10) NOT NULL COMMENT '目标语言',
  source VARCHAR(32) DEFAULT 'upload' COMMENT 'upload|manual',
  is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
  is_default_for_domain TINYINT(1) DEFAULT 0 COMMENT '同领域+语言对新建任务时是否默认挂载',
  term_count INT DEFAULT 0 COMMENT '词条数',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS domain_dictionary_terms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  dictionary_id INT NOT NULL,
  source_term VARCHAR(500) NOT NULL COMMENT '源语言词汇',
  target_term VARCHAR(500) NOT NULL COMMENT '目标语言译名',
  aliases JSON NULL COMMENT '异写/缩写列表',
  category VARCHAR(100) NULL COMMENT '分类',
  description TEXT NULL COMMENT '备注',
  priority INT DEFAULT 0 COMMENT '同词典内优先级，越大越优先',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_domain_dict_term_source (dictionary_id, source_term),
  KEY ix_domain_dictionary_terms_dictionary_id (dictionary_id),
  CONSTRAINT fk_domain_dict_terms_dict
    FOREIGN KEY (dictionary_id) REFERENCES domain_dictionaries(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 已有库补列（若已存在会报错，可忽略）
ALTER TABLE literary_translations
  ADD COLUMN domain_dictionary_ids JSON NULL COMMENT '关联的专业词典ID列表' AFTER reference_document_ids;

ALTER TABLE ai_config
  ADD COLUMN term_hit_table_max_entries INT NULL COMMENT '术语命中表每段上限（默认40）';
