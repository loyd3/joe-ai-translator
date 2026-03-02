-- 文学翻译表增加「失败原因」字段，便于排查 status=failed 的任务
-- 若表已存在且无此列，执行一次即可: mysql -u root -p aitranslator < backend/migrations/add_error_message.sql
ALTER TABLE literary_translations ADD COLUMN error_message TEXT NULL COMMENT '翻译流程失败时的错误信息' AFTER final_translation;
