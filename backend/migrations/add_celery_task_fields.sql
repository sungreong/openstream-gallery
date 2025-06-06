-- Add Celery task fields to apps table
-- 2024-01-XX: Add task tracking fields for Celery integration

-- Add image_name field
ALTER TABLE apps ADD COLUMN IF NOT EXISTS image_name VARCHAR(200);

-- Add Celery task ID fields
ALTER TABLE apps ADD COLUMN IF NOT EXISTS build_task_id VARCHAR(100);
ALTER TABLE apps ADD COLUMN IF NOT EXISTS deploy_task_id VARCHAR(100);
ALTER TABLE apps ADD COLUMN IF NOT EXISTS stop_task_id VARCHAR(100);

-- Update status column comment to include new statuses
COMMENT ON COLUMN apps.status IS 'stopped, building, deploying, running, error, stopping';

-- Create index on task ID fields for faster lookups
CREATE INDEX IF NOT EXISTS idx_apps_build_task_id ON apps(build_task_id);
CREATE INDEX IF NOT EXISTS idx_apps_deploy_task_id ON apps(deploy_task_id);
CREATE INDEX IF NOT EXISTS idx_apps_stop_task_id ON apps(stop_task_id); 