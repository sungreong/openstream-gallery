# Streamlit Self-Hosted Platform

Streamlit.io와 같은 self-hosted 형식의 플랫폼으로, Git 저장소에서 Streamlit 앱을 자동으로 배포하고 관리할 수 있습니다.

## 🚀 주요 기능

- **Git 기반 배포**: GitHub, GitLab 등의 Git 저장소에서 직접 앱 배포
- **자동 Docker 컨테이너화**: 각 앱을 독립적인 Docker 컨테이너로 실행
- **Nginx 리버스 프록시**: 포트 절약 및 경로 기반 라우팅 (예: `/app-name/`)
- **실시간 모니터링**: 앱 실행 상태, 로그, Celery 태스크 실시간 확인
- **사용자 관리**: JWT 기반 인증 시스템
- **반응형 웹 UI**: Material-UI 기반의 현대적인 사용자 인터페이스
- **베이스 이미지 선택**: Python 버전별, 용도별 최적화된 베이스 Dockerfile 제공
- **Git 인증 관리**: Private 저장소 접근을 위한 Git 인증 정보 관리
- **비동기 작업 처리**: Celery를 통한 빌드/배포 작업의 백그라운드 처리
- **Nginx 동적 설정**: 앱 배포 시 자동 Nginx 설정 생성 및 관리

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React (3000)  │    │ FastAPI (8000)  │    │PostgreSQL (5432)│
│   Frontend      │◄──►│   Backend       │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                        ▲                        ▲
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Nginx (1234)   │    │ Docker Engine   │    │  Redis (6379)   │
│ Reverse Proxy   │    │ (Streamlit Apps)│    │ Celery Broker   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲                        ▲
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Celery Worker   │    │  Celery Beat    │
                       │ (Build/Deploy)  │    │  (Scheduler)    │
                       └─────────────────┘    └─────────────────┘
```

## 🛠️ 기술 스택

### Backend

- **FastAPI**: Python 웹 프레임워크
- **PostgreSQL**: 데이터베이스
- **SQLAlchemy**: ORM
- **Celery**: 비동기 작업 큐 (빌드/배포)
- **Redis**: Celery 브로커 및 결과 백엔드
- **Docker CLI**: 컨테이너 관리 (CLI 방식)
- **GitPython**: Git 저장소 클론
- **Jinja2**: 템플릿 엔진 (Dockerfile 생성)

### Frontend

- **React**: 사용자 인터페이스
- **Material-UI (MUI)**: UI 컴포넌트 라이브러리
- **TanStack React Query**: 서버 상태 관리
- **Axios**: HTTP 클라이언트
- **React Router**: 라우팅
- **React Hook Form**: 폼 관리
- **React Hot Toast**: 알림 시스템

### Infrastructure

- **Docker & Docker Compose**: 컨테이너화
- **Nginx**: 리버스 프록시 및 동적 설정 관리
- **Docker Networks**: 서비스 간 통신
- **베이스 Dockerfile**: 다양한 Python 환경 지원 (3.9, 3.10, 3.11, 데이터사이언스, 최소)

## 🚀 빠른 시작

### 사전 요구사항

- Docker & Docker Compose
- Git

### 설치 및 실행

1. **저장소 클론**

```bash
git clone <repository-url>
cd streamlit-platform
```

2. **환경 변수 설정** (선택사항)

```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 설정 변경
```

3. **서비스 시작**

```bash
docker-compose up -d
```

4. **웹 브라우저에서 접속**

```
http://localhost:1234
```

### 기본 계정

- **사용자명**: admin
- **비밀번호**: admin123

> **참고**: 포트 1234를 사용합니다. 필요시 `docker-compose.yml`에서 변경 가능합니다.

## 📖 사용 방법

### 1. 회원가입/로그인

- 웹 인터페이스에서 새 계정을 생성하거나 기본 계정으로 로그인

### 2. Git 인증 정보 설정 (Private 저장소용)

- "Git 인증 관리" 메뉴에서 인증 정보 추가
- Username/Password 또는 Personal Access Token 설정

### 3. 새 앱 생성

- "새 앱 만들기" 버튼 클릭
- Git 저장소 URL, 브랜치, 메인 파일명 입력
- 베이스 Dockerfile 타입 선택 (Python 버전, 용도별)
- Git 인증 정보 선택 (Private 저장소인 경우)
- 앱 생성 완료

### 4. 앱 빌드 및 배포

- 대시보드에서 "빌드" 버튼 클릭하여 Docker 이미지 빌드
- 빌드 완료 후 자동으로 배포 시작
- 실시간 진행률 및 로그 확인 가능
- 배포 완료 후 `http://localhost:1234/앱이름/`으로 접속

### 5. 앱 관리 및 모니터링

- **실시간 모니터링**: 컨테이너 상태, 로그, 네트워크 정보
- **Celery 태스크 모니터링**: 빌드/배포 작업 진행률 및 상태
- **앱 편집**: 중지된 상태에서 설정 변경 가능
- **Nginx 설정 관리**: 동적 설정 파일 관리 및 정리
- **앱 제어**: 중지/재시작/삭제

## 🔧 설정

### 환경 변수

| 변수명           | 설명                | 기본값                                                                 |
| ---------------- | ------------------- | ---------------------------------------------------------------------- |
| `DATABASE_URL` | PostgreSQL 연결 URL | `postgresql://postgres:postgres123@postgres:5432/streamlit_platform` |
| `SECRET_KEY`   | JWT 토큰 암호화 키  | `your-secret-key-here`                                               |
| `DOCKER_HOST`  | Docker 소켓 경로    | `unix:///var/run/docker.sock`                                        |

### 포트 설정

- **1234**: Nginx (메인 웹 인터페이스)
- **443**: Nginx (HTTPS, 설정 시)
- **3000**: React 개발 서버
- **8000**: FastAPI 백엔드
- **5432**: PostgreSQL
- **6379**: Redis (Celery 브로커)
- **8501**: Streamlit 앱들 (내부 포트, Nginx를 통해 접근)

## 📁 프로젝트 구조

```
streamlit-platform/
├── backend/                 # FastAPI 백엔드
│   ├── routers/            # API 라우터 (apps, auth, nginx, celery 등)
│   ├── services/           # 비즈니스 로직 (Docker, Nginx, Git)
│   ├── app/tasks/          # Celery 태스크 (빌드/배포)
│   ├── dockerfiles/        # 베이스 Dockerfile 템플릿
│   ├── models.py           # 데이터베이스 모델
│   ├── schemas.py          # Pydantic 스키마
│   └── main.py             # FastAPI 앱
├── frontend/               # React 프론트엔드
│   ├── src/
│   │   ├── components/     # 재사용 컴포넌트
│   │   ├── pages/          # 페이지 컴포넌트 (Dashboard, AppDetail 등)
│   │   ├── contexts/       # React Context (Auth)
│   │   ├── utils/          # 유틸리티 함수
│   │   └── App.js          # 메인 앱
│   └── public/
├── nginx/                  # Nginx 설정
│   ├── conf.d/            # 정적 설정
│   └── conf.d/dynamic/    # 동적 앱 설정 (자동 생성)
├── database/               # 데이터베이스 초기화
├── docker-compose.yml      # Docker Compose 설정
└── README.md
```

## 🔒 보안 고려사항

- JWT 토큰 기반 인증
- Docker 컨테이너 격리
- Nginx를 통한 리버스 프록시
- 환경변수를 통한 민감 정보 관리

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 Apache 2.0 라이선스 하에 배포됩니다.

## 🐛 문제 해결

### 일반적인 문제들

1. **Docker 권한 오류**

   ```bash
   sudo usermod -aG docker $USER
   # 로그아웃 후 다시 로그인
   ```
2. **포트 충돌**

   - docker-compose.yml에서 포트 번호 변경
3. **Git 저장소 접근 오류**

   - 공개 저장소 URL 사용 확인
   - Private 저장소인 경우 Git 인증 정보 설정
   - Personal Access Token 사용 권장
4. **빌드 실패**

   - 베이스 Dockerfile 타입 변경 시도
   - requirements.txt 패키지 버전 확인
   - 로그에서 구체적인 오류 메시지 확인
5. **Nginx 설정 문제**

   - "Nginx 관리" 페이지에서 설정 파일 정리
   - 컨테이너 재시작: `docker-compose restart nginx`

### 로그 확인

```bash
# 전체 서비스 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f nginx
docker-compose logs -f celery_worker

# Streamlit 앱 로그
docker logs streamlit-app-{앱ID}
```

### 주요 디렉토리

- **앱 저장소**: `./storage/apps/` (Git 클론된 소스코드)
- **Nginx 동적 설정**: `./nginx/conf.d/dynamic/` (앱별 설정 파일)
- **베이스 Dockerfile**: `./backend/dockerfiles/` (템플릿 파일들)

## 📞 지원

문제가 발생하거나 질문이 있으시면 GitHub Issues를 통해 문의해주세요.
