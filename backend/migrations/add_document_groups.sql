-- 翻译文档自定义分组表
-- mysql -u root -p aitranslator < backend/migrations/add_document_groups.sql
CREATE TABLE IF NOT EXISTS document_groups (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL COMMENT '分组名称',
  sort_order INT DEFAULT 0 COMMENT '排序，越小越靠前',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_document_groups_name (name),
  KEY ix_document_groups_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 把已有任务上的分组名同步进分组表
INSERT IGNORE INTO document_groups (name, sort_order)
SELECT DISTINCT TRIM(group_name), 0
FROM literary_translations
WHERE group_name IS NOT NULL AND TRIM(group_name) <> '';
