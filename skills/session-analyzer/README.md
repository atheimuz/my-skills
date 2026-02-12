# Session Analyzer Skill

클로드 코드 세션 로그를 자동으로 분석하여 날짜별 활동 요약을 생성하는 Skill입니다.

## 기능

- 📊 **전체 통계**: 세션 수, 평균 도구 호출 등
- 🛠 **기술 스택 분석**: 사용한 언어, 프레임워크, 라이브러리 추출
- 🔧 **도구 사용 분석**: Bash, Read, Write 등 도구 사용 빈도
- 📝 **작업 유형 분류**: Coding, Debugging, Learning 등으로 분류
- 💡 **인사이트 추출**: Thinking 블록에서 주요 의사결정 추출
- 📈 **워크플로우 패턴**: 반복되는 도구 사용 패턴 발견

## 설치

이 디렉토리를 `~/.claude/skills/` 아래에 복사하면 자동으로 인식됩니다.

```bash
# 이미 설치되어 있습니다!
ls -la ~/.claude/skills/session-analyzer/
```

## 사용법

### 1. Skill 실행

```
/session-analyzer
```

또는 자연어로:

```
오늘 뭐했는지 요약해줘
최근 7일 활동 분석해줘
어제 작업 내역 보여줘
```

### 2. 날짜 선택

Claude가 질문하면 다음 중 선택:

- **오늘**: 오늘 날짜의 세션만 분석
- **어제**: 어제 세션만 분석
- **최근 7일**: 최근 일주일간 모든 세션 분석
- **특정 날짜**: YYYY-MM-DD 형식으로 날짜 입력

### 3. 결과 확인

생성된 마크다운 파일 확인:

```bash
# 오늘 요약
cat ~/.claude/summaries/daily/$(date +%Y-%m-%d).md

# 모든 요약 목록
ls -lh ~/.claude/summaries/daily/
```

## 출력 예시

```markdown
# 2026-02-11 클로드 코드 활동 요약

## 📊 전체 통계
- 총 세션 수: 5개
- 평균 메시지 수: 8.4개/세션
- 평균 도구 호출: 12.2회/세션

## 🛠 주요 기술 스택
### 언어
- TypeScript (4회)
- Python (1회)

### 프레임워크/라이브러리
- Next.js (3회)
- Tailwind (3회)

## 🔧 도구 사용
- Bash: 25회
- Write: 18회
- Read: 12회

## 📝 작업 유형
- 💻 Coding (3회)
- 🐛 Debugging (1회)
- 📋 Planning (1회)

## 🗂 세션 상세
[세션별 정보]

## 💡 오늘의 학습
[인사이트 목록]
```

## 분석 스크립트

`utils/analyze_sessions.py` - JSONL 파싱, 기술 스택 분석, 작업 유형 분류, 활용도 점수 계산을 통합 수행하는 스크립트입니다.

```bash
# 오늘 세션 분석
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date $(date +%Y-%m-%d)

# 특정 날짜 분석
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date 2026-02-11

# 날짜 범위 분석
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py \
  --date-range 2026-02-01 2026-02-11
```

## 기술적 세부사항

### 데이터 소스

- `~/.claude/projects/`: 모든 세션 로그가 JSONL 형식으로 저장됨
- 각 프로젝트별로 디렉토리 구분
- 세션 파일명: `[session-id].jsonl`

### JSONL 구조

각 라인은 독립적인 JSON 객체:

```jsonl
{"type": "user", "message": {"content": "..."}, "timestamp": "..."}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "..."}, {"type": "tool_use", "name": "Bash", "input": {...}}]}, "timestamp": "..."}
```

### 분석 알고리즘

1. **날짜 필터링**: 첫 줄의 timestamp로 날짜 판별
2. **키워드 추출**: 대소문자 무시하고 패턴 매칭
3. **작업 유형 분류**: 첫 번째 사용자 메시지에서 키워드 매칭
4. **Thinking 블록 추출**: "결정", "선택", "문제", "해결" 등 키워드 포함 문장 추출
5. **워크플로우 패턴**: 도구 호출 순서 3개씩 묶어서 빈도 분석

### 성능 최적화

- **샘플링**: 100개 이상 세션 시 최근 100개만 분석
- **캐싱**: 동일 날짜 재분석 방지 (향후 구현 예정)
- **병렬 처리**: 파일별 독립 분석 (향후 구현 예정)

## 커스터마이징

### 키워드 추가

`utils/analyze_sessions.py`의 상단 키워드 리스트를 수정:

```python
LANGUAGE_KEYWORDS = [
    'python', 'javascript', 'typescript', 'java', 'go', 'rust',
    # 여기에 추가
]
```

### 작업 유형 추가

`utils/analyze_sessions.py`의 `TASK_TYPE_KEYWORDS` 딕셔너리 수정:

```python
TASK_TYPE_KEYWORDS = {
    'Coding': ['구현', 'implement', 'create', ...],
    'Debugging': ['에러', 'error', 'bug', ...],
    # 여기에 추가
}
```

### 마크다운 템플릿 수정

`SKILL.md`의 8단계 "마크다운 템플릿" 섹션 수정

## 문제 해결

### 세션이 없다고 나오는 경우

1. 날짜 확인: 올바른 날짜인지 확인
2. 세션 로그 확인: `ls ~/.claude/projects/*/` 로 파일 존재 확인
3. 스크립트로 확인: `python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date YYYY-MM-DD`

### 파싱 오류

- JSONL 파일이 손상된 경우: 해당 세션 스킵
- JSON 형식 오류: 스크립트가 자동으로 스킵
- 인코딩 문제: UTF-8로 자동 처리

## 라이센스

MIT License

## 기여

버그 리포트나 기능 제안은 GitHub Issue로 등록해주세요.

## 향후 계획

- [ ] 주간/월간 요약 생성
- [ ] 시각화 (차트/그래프)
- [ ] 키워드 검색 기능
- [ ] 웹 대시보드
- [ ] AI 기반 심층 인사이트
- [ ] 캐싱 시스템 구현
- [ ] 병렬 처리 최적화
