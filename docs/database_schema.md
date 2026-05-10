# 📘 PostgreSQL 스키마

이 문서는 프로젝트의 PostgreSQL 테이블 스키마 정의와 REST API 엔드포인트 매핑을 제공한다.

---

## 1. 테이블 정의

### [account] 사용자 계정

- **id**: INTEGER (PK, AUTO_INCREMENT) - 계정 식별자
- **email**: VARCHAR (NOT NULL) - 이메일
- **nickname**: VARCHAR (NULL) - 닉네임
- **kakao_id**: BIGINT (NULL) - 카카오 사용자 ID

### [board] 게시판 게시글

- **id**: INTEGER (PK, AUTO_INCREMENT) - 게시글 식별자
- **title**: VARCHAR (NOT NULL) - 제목
- **content**: TEXT (NOT NULL) - 본문
- **account_id**: BIGINT (NOT NULL) - 작성자 계정 ID
- **created_at**: TIMESTAMP (NOT NULL) - 작성 시각
- **updated_at**: TIMESTAMP (NOT NULL) - 수정 시각

### [post] 포스트

- **id**: INTEGER (PK, AUTO_INCREMENT) - 포스트 식별자
- **title**: VARCHAR (NOT NULL) - 제목
- **content**: TEXT (NOT NULL) - 본문
- **created_at**: TIMESTAMP (NOT NULL) - 작성 시각

### [collected_news] 네이버 API 수집 뉴스

- **id**: INTEGER (PK, AUTO_INCREMENT) - 수집 뉴스 식별자
- **title**: VARCHAR (NOT NULL) - 뉴스 제목
- **description**: TEXT (NULL) - 뉴스 요약
- **url**: TEXT (NOT NULL) - 원문 URL
- **url_hash**: VARCHAR (NOT NULL) - URL SHA-256 해시
- **published_at**: VARCHAR (NULL) - 게시 날짜
- **keyword**: VARCHAR (NOT NULL) - 수집 키워드
- **collected_at**: TIMESTAMP (NOT NULL) - 수집 시각

### [collected_video] 수집된 유튜브 영상

- **id**: INTEGER (PK, AUTO_INCREMENT) - 수집 영상 식별자
- **video_id**: VARCHAR (NOT NULL) - 유튜브 영상 ID
- **title**: VARCHAR (NOT NULL) - 영상 제목
- **channel_name**: VARCHAR (NOT NULL) - 채널명
- **published_at**: TIMESTAMP (NOT NULL) - 게시 시각
- **view_count**: BIGINT (NOT NULL) - 조회수
- **thumbnail_url**: VARCHAR (NOT NULL) - 썸네일 URL
- **video_url**: VARCHAR (NOT NULL) - 영상 URL

### [saved_article] 관심 기사 (구버전)

- **id**: INTEGER (PK, AUTO_INCREMENT) - 기사 식별자
- **title**: VARCHAR (NOT NULL) - 뉴스 제목
- **link**: TEXT (NOT NULL) - 원문 링크
- **link_hash**: VARCHAR (NOT NULL, UNIQUE) - 링크 SHA-256 해시
- **source**: VARCHAR (NULL) - 출처
- **published_at**: VARCHAR (NULL) - 게시 날짜
- **snippet**: TEXT (NULL) - 뉴스 요약
- **content**: TEXT (NULL) - 스크래핑된 본문
- **saved_at**: TIMESTAMP (NOT NULL) - 저장 시각

### [saved_article_body] 관심 기사 본문 (JSONB)

- **id**: INTEGER (PK, AUTO_INCREMENT) - 본문 식별자
- **meta_id**: INTEGER (NOT NULL, INDEX) - saved_article_meta.id 참조
- **data**: JSONB (NOT NULL) - 본문 및 원본 데이터
- **created_at**: TIMESTAMP (NOT NULL) - 저장 시각

### [saved_youtube_video] 저장된 유튜브 영상

- **id**: INTEGER (PK, AUTO_INCREMENT) - 식별자
- **video_id**: VARCHAR (NOT NULL) - 유튜브 영상 ID
- **title**: VARCHAR (NOT NULL) - 영상 제목
- **channel_name**: VARCHAR (NOT NULL) - 채널명
- **published_at**: VARCHAR (NOT NULL) - 게시 날짜
- **view_count**: BIGINT (NOT NULL) - 조회수
- **thumbnail_url**: VARCHAR (NOT NULL) - 썸네일 URL
- **video_url**: VARCHAR (NOT NULL) - 영상 URL
- **saved_at**: TIMESTAMP (NOT NULL) - 저장 시각

### [video_comment] 유튜브 영상 댓글

- **id**: INTEGER (PK, AUTO_INCREMENT) - 댓글 식별자
- **comment_id**: VARCHAR (NOT NULL) - 유튜브 댓글 ID
- **video_id**: VARCHAR (NOT NULL) - 영상 ID
- **author_name**: VARCHAR (NOT NULL) - 작성자명
- **content**: TEXT (NOT NULL) - 댓글 본문
- **published_at**: TIMESTAMP (NOT NULL) - 게시 시각
- **like_count**: BIGINT (NOT NULL) - 좋아요 수

### [companies] 공시 대상 기업 정보

- **id**: INTEGER (PK, AUTO_INCREMENT) - 기업 식별자
- **corp_code**: VARCHAR (NOT NULL, UNIQUE) - DART 기업 코드
- **corp_name**: VARCHAR (NOT NULL) - 기업명
- **stock_code**: VARCHAR (NULL) - 종목 코드
- **market_type**: VARCHAR (NULL) - 시장 구분
- **market_cap_rank**: INTEGER (NULL) - 시가총액 순위
- **is_top300**: BOOLEAN (NOT NULL) - 상위 300대 기업 여부
- **is_collect_target**: BOOLEAN (NOT NULL) - 수집 대상 여부
- **is_active**: BOOLEAN (NOT NULL) - 활성 여부
- **last_requested_at**: TIMESTAMP (NULL) - 마지막 수집 요청 시각
- **created_at**: TIMESTAMP (NOT NULL) - 등록 시각
- **updated_at**: TIMESTAMP (NOT NULL) - 수정 시각

### [disclosures] 공시 목록

- **id**: INTEGER (PK, AUTO_INCREMENT) - 공시 식별자
- **rcept_no**: VARCHAR (NOT NULL, UNIQUE) - 접수 번호
- **corp_code**: VARCHAR (NOT NULL, FK) - 기업 코드
- **report_nm**: VARCHAR (NOT NULL) - 공시 보고서명
- **rcept_dt**: DATE (NOT NULL) - 접수 날짜
- **pblntf_ty**: VARCHAR (NULL) - 공시 유형
- **pblntf_detail_ty**: VARCHAR (NULL) - 공시 상세 유형
- **rm**: VARCHAR (NULL) - 비고
- **disclosure_group**: VARCHAR (NULL) - 공시 그룹 분류
- **source_mode**: VARCHAR (NOT NULL) - 수집 방식
- **is_core**: BOOLEAN (NOT NULL) - 핵심 공시 여부
- **created_at**: TIMESTAMP (NOT NULL) - 등록 시각
- **updated_at**: TIMESTAMP (NOT NULL) - 수정 시각

### [disclosure_documents] 공시 문서 및 분석

- **id**: INTEGER (PK, AUTO_INCREMENT) - 문서 식별자
- **rcept_no**: VARCHAR (NOT NULL) - 접수 번호
- **document_type**: VARCHAR (NOT NULL) - 문서 유형
- **raw_text**: TEXT (NULL) - 원문 텍스트
- **parsed_json**: JSONB (NULL) - 파싱된 구조화 데이터
- **summary_text**: TEXT (NULL) - GPT 요약
- **stored_in_rag**: BOOLEAN (NOT NULL) - RAG 저장 여부
- **collected_at**: TIMESTAMP (NOT NULL) - 수집 시각
- **created_at**: TIMESTAMP (NOT NULL) - 등록 시각
- **updated_at**: TIMESTAMP (NOT NULL) - 수정 시각

### [collection_jobs] 수집 작업 이력

- **id**: INTEGER (PK, AUTO_INCREMENT) - 작업 식별자
- **job_name**: VARCHAR (NOT NULL) - 작업명
- **job_type**: VARCHAR (NOT NULL) - 작업 유형
- **started_at**: TIMESTAMP (NOT NULL) - 시작 시각
- **finished_at**: TIMESTAMP (NULL) - 완료 시각
- **status**: VARCHAR (NOT NULL) - 상태
- **collected_count**: INTEGER (NOT NULL) - 수집 건수
- **saved_count**: INTEGER (NOT NULL) - 저장 건수
- **message**: TEXT (NULL) - 결과 메시지
- **created_at**: TIMESTAMP (NOT NULL) - 등록 시각

### [rag_document_chunks] RAG용 공시 문서 청크

- **id**: INTEGER (PK, AUTO_INCREMENT) - 청크 식별자
- **rcept_no**: VARCHAR (NOT NULL) - 접수 번호
- **corp_code**: VARCHAR (NOT NULL) - 기업 코드
- **disclosure_document_id**: BIGINT (NULL, FK) - 공시 문서 ID
- **report_nm**: VARCHAR (NOT NULL) - 보고서명
- **document_type**: VARCHAR (NOT NULL) - 문서 유형
- **section_title**: VARCHAR (NULL) - 섹션 제목
- **chunk_index**: INTEGER (NOT NULL) - 청크 순서
- **chunk_text**: TEXT (NOT NULL) - 청크 본문
- **embedding**: VECTOR (NULL) - 임베딩 벡터

### [integrated_analysis_results] 통합 투자 분석 결과

- **id**: INTEGER (PK, AUTO_INCREMENT) - 식별자
- **ticker**: VARCHAR (NOT NULL, INDEX) - 종목 코드
- **query**: TEXT (NOT NULL) - 분석 쿼리
- **overall_signal**: VARCHAR (NOT NULL) - 종합 투자 신호
- **confidence**: DOUBLE (NOT NULL) - 신뢰도 (0.0 ~ 1.0)
- **summary**: TEXT (NOT NULL) - 분석 요약
- **key_points**: JSON (NOT NULL) - 핵심 포인트 목록
- **sub_results**: JSON (NOT NULL) - 세부 에이전트 분석 결과
- **execution_time_ms**: INTEGER (NOT NULL) - 실행 시간
- **created_at**: TIMESTAMP (NOT NULL) - 분석 시각

### [collection_job_items] 수집 작업 개별 항목

- **id**: INTEGER (PK, AUTO_INCREMENT) - 항목 식별자
- **job_id**: BIGINT (NOT NULL, FK) - 작업 ID
- **rcept_no**: VARCHAR (NULL) - 접수 번호
- **corp_code**: VARCHAR (NULL) - 기업 코드
- **status**: VARCHAR (NOT NULL) - 처리 상태
- **message**: TEXT (NULL) - 처리 결과 메시지
- **created_at**: TIMESTAMP (NOT NULL) - 등록 시각

### [company_data_coverage] 기업별 공시 데이터 수집 현황

- **id**: INTEGER (PK, AUTO_INCREMENT) - 식별자
- **corp_code**: VARCHAR (NOT NULL, UNIQUE) - 기업 코드
- **has_b001**: BOOLEAN (NOT NULL) - 사업보고서 수집 여부
- **has_d002_d005**: BOOLEAN (NOT NULL) - 분기/반기 보고서 여부
- **has_d001**: BOOLEAN (NOT NULL) - 감사보고서 여부
- **has_e001**: BOOLEAN (NOT NULL) - 주요사항보고서 여부
- **has_c001**: BOOLEAN (NOT NULL) - 합병 관련 공시 여부
- **has_a001**: BOOLEAN (NOT NULL) - 유가증권신고서 여부
- **has_a002**: BOOLEAN (NOT NULL) - 증권신고서 여부
- **has_a003**: BOOLEAN (NOT NULL) - 투자설명서 여부
- **has_event_documents**: BOOLEAN (NOT NULL) - 이벤트 문서 여부
- **last_collected_at**: TIMESTAMP (NULL) - 마지막 수집 시각
- **last_on_demand_at**: TIMESTAMP (NULL) - 마지막 온디맨드 요청 시각
- **created_at**: TIMESTAMP (NOT NULL) - 등록 시각
- **updated_at**: TIMESTAMP (NOT NULL) - 수정 시각

### [stock_theme] 주식 테마 종목

- **id**: INTEGER (PK, AUTO_INCREMENT) - 식별자
- **name**: VARCHAR (NOT NULL) - 종목명
- **code**: VARCHAR (NOT NULL) - 종목 코드
- **themes**: JSON (NOT NULL) - 해당 테마 목록

### [defense_stock] 방산 관련 종목

- **id**: INTEGER (PK, AUTO_INCREMENT) - 식별자
- **name**: VARCHAR (NOT NULL) - 종목명
- **code**: VARCHAR (NOT NULL) - 종목 코드
- **themes**: JSON (NOT NULL) - 방산 테마 목록

### [stock_vector_document] 주식 관련 벡터 문서

- **id**: INTEGER (PK, AUTO_INCREMENT) - 식별자
- **chunk_id**: VARCHAR (NOT NULL) - 청크 ID
- **entity_id**: VARCHAR (NOT NULL) - 엔티티 ID (종목 코드 등)
- **source**: VARCHAR (NOT NULL) - 데이터 출처
- **dedup_key**: VARCHAR (NOT NULL) - 중복 방지 키
- **chunk_index**: INTEGER (NOT NULL) - 청크 순서
- **content**: TEXT (NOT NULL) - 청크 본문
- **embedding_vector**: ARRAY (NOT NULL) - 임베딩 벡터
- **collected_at**: TIMESTAMPTZ (NOT NULL) - 수집 시각

### [user_saved_article] 관심 기사 메타데이터

- **id**: INT (PK, AUTO_INCREMENT) - 기사 메타 식별자
- **account_id**: INT (NOT NULL, INDEX) - 저장 사용자 ID
- **title**: VARCHAR(500) (NOT NULL) - 뉴스 제목
- **source**: VARCHAR(255) (NULL) - 출처
- **link**: TEXT (NOT NULL) - 원문 링크
- **link_hash**: VARCHAR(64) (NOT NULL) - 링크 SHA-256 해시
- **published_at**: VARCHAR(100) (NULL) - 게시 날짜
- **snippet**: TEXT (NULL) - 뉴스 요약
- **saved_at**: DATETIME (NOT NULL) - 저장 시각

### [article_content_jsonb] 관심 기사 본문

- **id**: INTEGER (PK, AUTO_INCREMENT) - 식별자
- **user_saved_article_id**: INTEGER (NOT NULL, INDEX) - user_saved_article.id 참조
- **content**: JSONB (NULL) - 기사 본문 및 비정형 데이터
- **created_at**: TIMESTAMPTZ (NOT NULL) - 저장 시각

---

## 2. REST API 엔드포인트 (총 36개)

### 카카오 OAuth

- `GET /api/v1/kakao-authentication/request-oauth-link`
- `GET /api/v1/kakao-authentication/request-access-token-after-redirection`

### 기본 인증

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/session/{token}`
- `DELETE /api/v1/auth/logout/{token}`

### 사용자 정보

- `GET /authentication/me`

### 계정

- `POST /api/v1/account/sign-up`

### 게시판

- `GET /api/v1/board/list`
- `GET /api/v1/board/read/{board_id}`
- `POST /api/v1/board/register`
- `PUT /api/v1/board/edit/{board_id}`
- `DELETE /api/v1/board/delete/{board_id}`

### 포스트

- `GET /api/v1/post/list`
- `GET /api/v1/post/{post_id}`
- `POST /api/v1/post`

### 뉴스

- `GET /api/v1/news/search`
- `POST /api/v1/news/save`
- `GET /api/v1/news/analyze/{article_id}`
- `POST /api/v1/news/interest`
- `GET /api/v1/news/agent-result`
- `POST /api/v1/news/collect`

### 주식

- `GET /api/v1/stock/{ticker}`
- `GET /api/v1/stock/{ticker}/collect`

### 주식 테마

- `GET /api/v1/stock-theme`
- `POST /api/v1/stock-theme/recommend`

### 유튜브

- `GET /api/v1/youtube/list`
- `POST /api/v1/youtube/collect`
- `POST /api/v1/youtube/collect-comments`
- `GET /api/v1/youtube/nouns`

### 시장 분석

- `POST /api/v1/market-analysis/ask`

### 공시

- `GET /api/v1/disclosure/analyze`
- `POST /api/v1/disclosure/process-documents`

### 에이전트

- `POST /api/v1/agent/query`
- `GET /api/v1/agent/history`
- `POST /api/v1/agent/finance-analysis`

### API 스키마

- `GET /api/v1/agent-schema`
