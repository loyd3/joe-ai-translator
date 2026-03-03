-- 文学翻译表增加「用户翻译需求」字段
-- 若表已存在且无此列，执行一次即可: mysql -u root -p aitranslator < backend/migrations/add_user_requirements.sql
ALTER TABLE literary_translations ADD COLUMN user_requirements TEXT NULL COMMENT '用户翻译需求说明' AFTER reference_document_ids;
