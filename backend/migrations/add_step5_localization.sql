-- 第五步：本地化
-- mysql -u root -p aitranslator < backend/migrations/add_step5_localization.sql

ALTER TABLE literary_translations
  ADD COLUMN step5_localization TEXT NULL COMMENT '第五步：本地化' AFTER step4_finalization;

ALTER TABLE literary_paragraphs
  ADD COLUMN step5_localization TEXT NULL AFTER step4_finalization;
