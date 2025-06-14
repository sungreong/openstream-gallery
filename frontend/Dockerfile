FROM node:18-alpine

WORKDIR /app

# package.json과 package-lock.json 복사
COPY package*.json ./

# 의존성 설치
RUN npm install --only=production

# 소스 코드 복사
COPY . .

# 포트 노출
EXPOSE 3000

# 개발 서버 실행
CMD ["npm", "start"]

ENV REACT_APP_API_URL=http://localhost:8000/api
ENV REACT_APP_BASE_URL=http://localhost:1234 