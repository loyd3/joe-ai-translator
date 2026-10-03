-- 翻译文档用户自定义分组
-- mysql -u root -p aitranslator < backend/migrations/add_group_name.sql
ALTER TABLE literary_translations
  ADD COLUMN group_name VARCHAR(200) NULL COMMENT '用户自定义分组，空=未分组' AFTER title;

CREATE INDEX ix_literary_translations_group_name ON literary_translations (group_name);
