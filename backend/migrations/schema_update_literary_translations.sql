-- 文学翻译表结构更新：补充 user_requirements、error_message 列
-- 在项目根目录执行一次: mysql -u root -p aitranslator < backend/migrations/schema_update_literary_translations.sql
-- 若某列已存在会报 Duplicate column，可忽略该行或只执行缺失的 ALTER。

ALTER TABLE literary_translations ADD COLUMN user_requirements TEXT NULL COMMENT '用户翻译需求说明' AFTER reference_document_ids;
ALTER TABLE literary_translations ADD COLUMN error_message TEXT NULL COMMENT '翻译流程失败时的错误信息' AFTER final_translation;
