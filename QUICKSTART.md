# 🚀 Dam Analysis System - Quick Start Guide

## 📦 제공된 파일

✅ `dam-analysis-system.tar.gz` - 전체 프로젝트 (22KB)

압축 해제 시 포함 내용:
```
dam-analysis-system/
├── backend/           # FastAPI 백엔드
├── frontend/          # React 프론트엔드
├── scripts/           # Python 분석 스크립트
└── README.md          # 상세 문서
```

---

## ⚡ 5분 안에 실행하기

### Step 1: 압축 해제
```bash
tar -xzf dam-analysis-system.tar.gz
cd dam-analysis-system
```

### Step 2: Backend 실행
```bash
# 터미널 1
cd backend
pip install -r requirements.txt
python main.py

# 실행 확인: http://localhost:8000
```

### Step 3: Frontend 실행
```bash
# 터미널 2 (새 터미널)
cd frontend
npm install
npm start

# 자동으로 브라우저 열림: http://localhost:3000
```

### Step 4: 분석 실행
1. **파일 업로드**
   - DEM: .tif 파일
   - 하천: .shp 또는 .zip
   - 경계: .shp 또는 .zip

2. **조건 설정** (기본값 OK)
   - 하천 등급: 3~5
   - 최소 저수량: 5 Mm³
   - 최대 댐길이: 1000m

3. **분석 시작** 클릭

4. **진행상황 모니터링**
   - 10%: 데이터 검증
   - 50%: 프로파일 생성
   - 100%: 완료!

5. **결과 확인**
   - 지도에서 후보지 확인
   - 4개 파일 다운로드
   - 시각화 앱에 업로드

---

## 🌐 GitHub → Render 배포 (5분)

### Backend 배포

1. **GitHub에 Push**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

2. **Render.com 설정**
   - New Web Service
   - Connect Repository
   - Settings:
     ```
     Name: dam-analysis-backend
     Branch: main
     Root Directory: backend
     Build Command: pip install -r requirements.txt
     Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
     ```

3. **배포 완료!**
   - URL: `https://dam-analysis-backend.onrender.com`

### Frontend 배포

1. **Environment 변수 설정**
   - File: `frontend/.env.production`
   ```
   REACT_APP_API_URL=https://dam-analysis-backend.onrender.com
   ```

2. **Render Static Site**
   - New Static Site
   - Connect Repository
   - Settings:
     ```
     Build Command: cd frontend && npm install && npm run build
     Publish Directory: frontend/build
     ```

3. **배포 완료!**
   - URL: `https://dam-analysis.onrender.com`

---

## 📊 사용 시나리오

### 시나리오 1: Nam Ngiep 유역 재분석
```
1. Nam Ngiep DEM, 하천, 경계 업로드
2. 조건:
   - 하천 등급: 3~5
   - 최소 저수량: 10 Mm³ (더 엄격)
   - 최대 댐길이: 500m (짧은 댐만)
3. 분석 실행
4. 결과: 고품질 10~15개 사이트
5. 다운로드: 4개 JS 파일
6. 시각화 앱에서 상세 검토
```

### 시나리오 2: 새로운 유역 분석
```
1. 새 유역 데이터 업로드
2. 기본 조건 사용
3. 분석 실행
4. 결과 확인 후 조건 조정
5. 재분석 (조건만 변경, 파일 재업로드 불필요)
6. 최종 결과 다운로드
```

### 시나리오 3: 14개 유역 일괄 처리
```
For each basin in basins:
  1. 파일 업로드
  2. 기본 조건 사용
  3. 분석 실행
  4. 결과 저장 (basin_name_results.json)
  5. Next basin

통합:
  - 모든 결과를 하나의 대시보드에 표시
  - 유역별 비교 분석
  - 국가 차원 우선순위 도출
```

---

## 🔧 문제 해결

### "Cannot connect to backend"
**원인**: Backend가 실행되지 않음

**해결**:
```bash
cd backend
python main.py
```

### "Module not found"
**원인**: 의존성 미설치

**해결**:
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### "Analysis failed"
**원인**: 파일 형식 오류 또는 좌표계 불일치

**해결**:
1. DEM: GeoTIFF 형식 확인
2. Shapefile: .shp, .shx, .dbf 모두 필요 (zip으로 묶기)
3. 좌표계: WGS84 또는 UTM 사용
4. Backend 로그 확인: `backend/logs/`

---

## 📁 파일 형식 요구사항

| 파일 | 허용 형식 | 좌표계 | 크기 제한 |
|------|----------|--------|----------|
| DEM | .tif, .tiff | WGS84 / UTM | 100MB |
| 하천 | .shp + 보조파일 또는 .zip | WGS84 / UTM | 50MB |
| 경계 | .shp + 보조파일 또는 .zip | WGS84 / UTM | 10MB |

**하천 레이어 필수 속성:**
- `Order` - 하천 등급
- `DSContArea` - 유역 면적 (m²)
- `Slope` - 경사

---

## 💡 팁

### 성능 최적화
- DEM 해상도: 30m 권장 (10m는 너무 느림)
- 유역 크기: 5,000 km² 이하 권장
- 탐색 간격: 500m 기본, 빠른 스캔은 1000m

### 결과 품질 향상
- 하천 등급: 3~5가 최적 (6은 너무 큼, 1~2는 너무 작음)
- 최소 저수량: 5 Mm³ (경제성 기준)
- 최대 댐길이: 1000m (공사비 제약)

### 데이터 관리
- 결과 파일: 7일간 서버 보관
- 다운로드 후 백업 권장
- 분석 조건 JSON 저장 (재현성)

---

## 🎯 다음 단계

### 1주차: 시스템 숙지
- [x] 로컬 환경 구축
- [ ] Nam Ngiep 재분석
- [ ] 결과 품질 확인

### 2주차: 배포
- [ ] GitHub 저장소 생성
- [ ] Render 배포
- [ ] 팀원에게 URL 공유

### 3주차: 본격 분석
- [ ] 14개 유역 순차 분석
- [ ] 결과 데이터베이스 구축
- [ ] 비교 분석 리포트

### 4주차: 의사결정
- [ ] 우선순위 사이트 선정
- [ ] 상세 타당성 조사 계획
- [ ] 예산 수립

---

## 📞 지원

**질문/버그 리포트:**
- GitHub Issues
- Email: [your-email]

**업데이트:**
- v1.1: 다중 결과 비교
- v1.2: PDF 보고서 생성
- v2.0: 경제성 분석 추가

---

**🎉 축하합니다! 이제 14개 유역을 쉽게 분석할 수 있습니다!**

다음 목표: 전국 댐 개발 마스터플랜 수립 🚀
