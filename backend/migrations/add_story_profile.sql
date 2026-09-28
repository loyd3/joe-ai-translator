-- 故事类文本的结构档案（人物、故事线、设定、叙述）
-- mysql -u root -p aitranslator < backend/migrations/add_story_profile.sql
ALTER TABLE literary_translations ADD COLUMN story_profile JSON NULL COMMENT '故事结构档案' AFTER error_message;
