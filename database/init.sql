-- 데이터베이스 초기화 스크립트

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Git 인증 정보 테이블 (apps 테이블보다 먼저 생성)
CREATE TABLE IF NOT EXISTS git_credentials (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    git_provider VARCHAR(50) NOT NULL,
    auth_type VARCHAR(20) NOT NULL,
    username VARCHAR(100),
    token_encrypted TEXT,
    ssh_key_encrypted TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 앱 테이블
CREATE TABLE IF NOT EXISTS apps (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    git_url VARCHAR(500) NOT NULL,
    branch VARCHAR(100) DEFAULT 'main',
    main_file VARCHAR(200) DEFAULT 'streamlit_app.py',
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    git_credential_id INTEGER REFERENCES git_credentials(id) ON DELETE SET NULL,
    base_dockerfile_type VARCHAR(20) DEFAULT 'auto', -- auto, minimal, py311, py310, py309  
    status VARCHAR(20) DEFAULT 'stopped', -- stopped, building, running, error, deploying, stopping
    container_id VARCHAR(100),
    image_name VARCHAR(200),
    port INTEGER,
    subdomain VARCHAR(100) UNIQUE,
    build_task_id VARCHAR(100),
    deploy_task_id VARCHAR(100),
    stop_task_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_deployed_at TIMESTAMP
);

-- 배포 히스토리 테이블
CREATE TABLE IF NOT EXISTS deployments (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES apps(id) ON DELETE CASCADE,
    commit_hash VARCHAR(40),
    status VARCHAR(20) NOT NULL, -- success, failed, in_progress
    build_logs TEXT,
    error_message TEXT,
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 앱 환경변수 테이블
CREATE TABLE IF NOT EXISTS app_env_vars (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES apps(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_apps_user_id ON apps(user_id);
CREATE INDEX IF NOT EXISTS idx_apps_status ON apps(status);
CREATE INDEX IF NOT EXISTS idx_apps_build_task_id ON apps(build_task_id);
CREATE INDEX IF NOT EXISTS idx_apps_deploy_task_id ON apps(deploy_task_id);
CREATE INDEX IF NOT EXISTS idx_apps_stop_task_id ON apps(stop_task_id);
CREATE INDEX IF NOT EXISTS idx_deployments_app_id ON deployments(app_id);
CREATE INDEX IF NOT EXISTS idx_app_env_vars_app_id ON app_env_vars(app_id);
CREATE INDEX IF NOT EXISTS idx_git_credentials_user_id ON git_credentials(user_id);

-- 기본 사용자 생성 (개발용)
INSERT INTO users (username, email, password_hash) 
VALUES ('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJK9.K7u.') -- password: admin123
ON CONFLICT (username) DO NOTHING; 