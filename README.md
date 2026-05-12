# 🌊 Dam Site Analysis System

**전자동 댐 적지 분석 시스템** - Laos 14개 유역 분석용 프로덕션 웹 애플리케이션

---

## 📋 시스템 개요

### 특징
- ✅ **풀스택 웹 애플리케이션** (React + FastAPI)
- ✅ **비동기 처리** - 백그라운드 분석 작업
- ✅ **실시간 진행상황** - 2초마다 상태 업데이트
- ✅ **자동 파일 생성** - 4개 JS 파일 (candidates, profiles, flood, damLengths)
- ✅ **인터랙티브 결과** - 지도 시각화 + 다운로드
- ✅ **GitHub-Render 배포** - 원클릭 배포 지원

### 아키텍처
```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  React Frontend │  HTTP   │  FastAPI Backend │ Python  │  Analysis Engine│
│  (Port 3000)    │ ───────>│  (Port 8000)     │ ──────> │  (GIS Scripts)  │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

---

## 🚀 빠른 시작

### Prerequisites
- Python 3.8+
- Node.js 16+
- Git

### 1. 클론
```bash
git clone <your-repo>
cd dam-analysis-system
```

### 2. Backend 설정
```bash
cd backend
pip install -r requirements.txt
python main.py
# 서버 시작: http://localhost:8000
```

### 3. Frontend 설정 (새 터미널)
```bash
cd frontend
npm install
npm start
# 앱 열림: http://localhost:3000
```

### 4. 사용
1. 브라우저에서 http://localhost:3000 접속
2. DEM, 하천, 경계 파일 업로드
3. 조건 설정 (기본값 사용 가능)
4. "분석 시작" 클릭
5. 진행상황 모니터링 (자동)
6. 결과 확인 및 파일 다운로드

---

## 📂 프로젝트 구조

```
dam-analysis-system/
├── backend/
│   ├── main.py                 # FastAPI 애플리케이션
│   ├── requirements.txt        # Python 의존성
│   ├── uploads/                # 업로드된 파일 (자동 생성)
│   └── outputs/                # 분석 결과 (자동 생성)
│
├── frontend/
│   ├── src/
│   │   ├── App.js             # 메인 앱
│   │   ├── components/        # React 컴포넌트
│   │   │   ├── FileUpload.js
│   │   │   ├── CriteriaPanel.js
│   │   │   ├── ResultsPanel.js
│   │   │   └── MapView.js
│   │   └── *.css              # 스타일시트
│   ├── public/
│   └── package.json
│
├── scripts/
│   ├── 01_site_selection.py        # 댐 적지 선정
│   ├── 02_generate_profiles.py     # 프로파일 생성
│   └── 03_generate_flood_damlengths.py  # 침수/댐길이
│
└── README.md
```

---

## 🌐 Render.com 배포

### Backend 배포

1. **Render 계정** 생성 (https://render.com)

2. **New Web Service** 생성
   - Repository 연결
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Environment: Python 3.11

3. **Environment Variables** 설정
   ```
   PYTHON_VERSION=3.11
   ```

4. 배포 완료! (URL: `https://your-app.onrender.com`)

### Frontend 배포

1. **New Static Site** 생성
   - Repository 연결
   - Build Command: `cd frontend && npm install && npm run build`
   - Publish Directory: `frontend/build`

2. **Environment Variables** 설정
   ```
   REACT_APP_API_URL=https://your-backend-app.onrender.com
   ```

3. 배포 완료!

---

## 🛠️ API 엔드포인트

### POST /api/analyze
파일 업로드 및 분석 시작

**Request:**
```
Content-Type: multipart/form-data

dem: File
rivers: File
boundary: File
criteria: JSON string
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "pending"
}
```

### GET /api/status/{task_id}
분석 진행상황 조회

**Response:**
```json
{
  "task_id": "uuid",
  "status": "processing",  // pending, processing, completed, failed
  "progress": 45,
  "message": "프로파일 생성 중..."
}
```

### GET /api/results/{task_id}
분석 결과 조회

**Response:**
```json
{
  "task_id": "uuid",
  "total_sites": 39,
  "sites": [
    {
      "id": "S1",
      "lat": 19.02466,
      "lon": 103.38857,
      "volume": 2821.0,
      "height": 120,
      "damLength": 210,
      "bed": 344,
      "order": 4
    }
  ],
  "files": ["candidates.js", "profiles.js", ...]
}
```

### GET /api/download/{task_id}/{filename}
결과 파일 다운로드

---

## ⚙️ 설정 파라미터

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| min_order | 3 | 최소 하천 등급 |
| max_order | 5 | 최대 하천 등급 |
| min_drainage | 50 | 최소 유역면적 (km²) |
| max_drainage | 5000 | 최대 유역면적 (km²) |
| min_volume | 5.0 | 최소 저수량 (Mm³) |
| max_dam_length | 1000 | 최대 댐길이 (m) |
| max_slope | 35 | 최대 경사 (도) |
| search_interval | 500 | 탐색 간격 (m) |

---

## 📊 워크플로우

### 사용자 관점
1. 파일 업로드 (DEM + 하천 + 경계)
2. 조건 설정
3. 분석 시작 버튼 클릭
4. 진행상황 모니터링 (10% → 50% → 100%)
5. 지도에서 결과 확인
6. 4개 JS 파일 다운로드
7. 시각화 앱에 업로드

### 시스템 내부
1. Backend: 파일 수신 및 저장
2. Task ID 생성 및 반환
3. Background: Python 스크립트 실행
   - 01_site_selection.py (20%)
   - 02_generate_profiles.py (50%)
   - 03_generate_flood_damlengths.py (80%)
4. 결과 파일 생성 (100%)
5. Frontend: 2초마다 상태 폴링
6. 완료 시 결과 로드 및 표시

---

## 🔒 프로덕션 체크리스트

### 보안
- [ ] CORS 허용 도메인 제한
- [ ] 파일 크기 제한 (100MB)
- [ ] 파일 타입 검증
- [ ] Rate limiting
- [ ] HTTPS 적용

### 성능
- [ ] Redis로 task storage 전환
- [ ] Celery로 worker 분리
- [ ] File cleanup (7일 후 삭제)
- [ ] CDN for static files

### 모니터링
- [ ] Sentry 에러 추적
- [ ] Analytics 추가
- [ ] Health check endpoint
- [ ] Logging 시스템

---

## 📝 개발 로드맵

### Phase 1: MVP (완료) ✅
- [x] 기본 파일 업로드
- [x] 비동기 분석 처리
- [x] 결과 시각화
- [x] 파일 다운로드

### Phase 2: 고도화
- [ ] Redis + Celery 통합
- [ ] 다중 결과 비교
- [ ] 결과 히스토리
- [ ] 사용자 인증

### Phase 3: 확장
- [ ] 14개 유역 일괄 처리
- [ ] 경제성 분석
- [ ] PDF 보고서 생성
- [ ] 관리자 대시보드

---

## 🐛 트러블슈팅

### "Module not found"
```bash
cd backend
pip install -r requirements.txt
```

### "Port already in use"
Backend:
```bash
lsof -ti:8000 | xargs kill -9
python main.py
```

Frontend:
```bash
lsof -ti:3000 | xargs kill -9
npm start
```

### CORS 에러
`backend/main.py`에서 CORS 설정 확인:
```python
allow_origins=["http://localhost:3000"]
```

---

## 📞 지원

- GitHub Issues: [링크]
- Email: [이메일]
- Documentation: [문서 링크]

---

## 📜 라이센스

MIT License

---

**Made with 💙 for Laos Hydropower Development**

🎯 **Next:** 14개 유역 분석 완료 → 국가 차원 수력 개발 전략 수립
