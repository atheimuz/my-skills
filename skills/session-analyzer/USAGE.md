# Session Analyzer 사용 가이드

## 빠른 시작

### 1. Skill 실행

```
/session-analyzer
```

### 2. 날짜 선택

Claude가 다음과 같은 질문을 할 것입니다:

```
어떤 기간의 활동을 분석할까요?
1. 오늘 (추천)
2. 어제
3. 최근 7일
4. 특정 날짜
```

원하는 옵션을 선택하세요.

### 3. 결과 확인

분석이 완료되면 다음 위치에 마크다운 파일이 생성됩니다:

```bash
~/.claude/summaries/daily/2026-02-11.md
```

## 명령어로 직접 실행

Python 스크립트를 직접 사용할 수도 있습니다.

### 오늘 세션 분석

```bash
cd ~/.claude/skills/session-analyzer/utils
python3 parse_jsonl.py --date $(date +%Y-%m-%d) | python3 analyze.py > analysis.json
```

### 특정 날짜 분석

```bash
python3 parse_jsonl.py --date 2026-02-10 | python3 analyze.py
```

### 날짜 범위 분석

```bash
python3 parse_jsonl.py --date-range 2026-02-01 2026-02-10 | python3 analyze.py
```

### 특정 파일만 파싱

```bash
python3 parse_jsonl.py --file ~/.claude/projects/my-project/session-123.jsonl
```

## 생성된 요약 보기

### 최신 요약 보기

```bash
# 가장 최근 요약 파일
ls -t ~/.claude/summaries/daily/ | head -1 | xargs -I {} cat ~/.claude/summaries/daily/{}
```

### 모든 요약 목록

```bash
ls -lh ~/.claude/summaries/daily/
```

### 특정 날짜 요약

```bash
cat ~/.claude/summaries/daily/2026-02-11.md
```

## 출력 형식

### summary (간략)

```bash
python3 parse_jsonl.py --date 2026-02-11 --output summary
```

출력:
```
총 세션 수: 3
날짜 범위: 2026-02-11 ~ 2026-02-11

세션 1: 18020550-f682-4518-b36d-4f3ea1d1200b.jsonl
  메시지 수: 45
  도구 호출 수: 8
  Thinking 블록 수: 12
```

### json (상세)

```bash
python3 parse_jsonl.py --date 2026-02-11 --output json
```

출력: 전체 JSON 데이터 (파이프로 analyze.py에 전달 가능)

## 분석 결과 구조

analyze.py의 출력 JSON 구조:

```json
{
  "date_range": {
    "start": "2026-02-11T00:00:00",
    "end": "2026-02-11T23:59:59"
  },
  "statistics": {
    "total_sessions": 3,
    "total_messages": 45,
    "total_tool_calls": 24,
    "avg_messages_per_session": 15.0,
    "avg_tool_calls_per_session": 8.0
  },
  "tech_stack": {
    "languages": {"python": 5, "typescript": 2},
    "frameworks": {"react": 3, "next.js": 2},
    "libraries": {"tailwind": 1},
    "file_extensions": {"py": 10, "md": 5, "ts": 3}
  },
  "task_types": {
    "💻 Coding": 2,
    "📋 Planning": 1
  },
  "tool_usage": {
    "Bash": 10,
    "Write": 8,
    "Read": 6
  },
  "thinking_insights": [
    "[결정] Python 스크립트로 파싱 로직 구현하기로 결정",
    "[해결] JSONL 파싱 문제를 jq로 해결"
  ],
  "workflow_patterns": [
    "Read → Write → Bash (3회)",
    "Grep → Read → Edit (2회)"
  ],
  "session_details": [
    {
      "task_type": "💻 Coding",
      "summary": "Implement session analyzer skill...",
      "message_count": 15,
      "tool_call_count": 8
    }
  ]
}
```

## 팁과 트릭

### 1. 여러 날짜 일괄 분석

```bash
# 최근 7일 각각 분석
for i in {0..6}; do
  date=$(date -v-${i}d +%Y-%m-%d)
  python3 parse_jsonl.py --date $date | python3 analyze.py > /tmp/analysis-$date.json
done
```

### 2. 주간 요약 생성

```bash
# 이번 주 월요일부터 오늘까지
monday=$(date -v-Mon +%Y-%m-%d)
today=$(date +%Y-%m-%d)
python3 parse_jsonl.py --date-range $monday $today | python3 analyze.py
```

### 3. 특정 프로젝트만 분석

```bash
# 프로젝트 디렉토리 지정
python3 parse_jsonl.py --date 2026-02-11 --projects-dir ~/.claude/projects/my-project
```

### 4. jq로 필터링

```bash
# 가장 많이 사용한 언어 Top 3
python3 parse_jsonl.py --date 2026-02-11 | \
  python3 analyze.py | \
  jq -r '.tech_stack.languages | to_entries | sort_by(-.value) | .[0:3] | .[] | "\(.key): \(.value)회"'
```

### 5. 도구 사용 통계만 보기

```bash
python3 parse_jsonl.py --date 2026-02-11 | \
  python3 analyze.py | \
  jq '.tool_usage'
```

## 문제 해결

### "선택한 기간에 세션이 없습니다"

**원인**: 해당 날짜에 세션 파일이 없음

**해결**:
```bash
# 세션 파일 확인
find ~/.claude/projects -name "*.jsonl" -type f -exec head -n 1 {} \; | \
  jq -r '.timestamp' 2>/dev/null | sort
```

### JSON 파싱 오류

**원인**: JSONL 파일이 손상되었거나 형식이 잘못됨

**해결**:
- 손상된 파일 확인: `jq . [파일경로] > /dev/null`
- 스크립트가 자동으로 스킵하므로 일반적으로 무시 가능

### Python 모듈 없음

**원인**: Python이 설치되지 않았거나 버전이 낮음

**해결**:
```bash
# Python 버전 확인 (3.7+ 필요)
python3 --version

# macOS
brew install python3

# Ubuntu/Debian
sudo apt-get install python3
```

### jq 없음

**원인**: jq가 설치되지 않음

**해결**:
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq
```

또는 Python 스크립트만 사용 (jq 불필요)

## 고급 사용법

### 커스텀 키워드 추가

`utils/analyze.py` 파일의 상단 키워드 리스트를 수정:

```python
LANGUAGE_KEYWORDS = [
    'python', 'javascript', 'typescript',
    'my-custom-language',  # 추가
]
```

### 작업 유형 커스터마이징

```python
TASK_TYPE_KEYWORDS = {
    '💻 Coding': ['구현', 'implement', 'create'],
    '🎨 Design': ['디자인', 'design', 'ui', 'ux'],  # 새로운 유형 추가
}
```

### 마크다운 템플릿 변경

SKILL.md의 8단계 "마크다운 템플릿" 섹션을 수정하여 출력 형식 커스터마이징

## 성능 고려사항

- **대용량 세션**: 100개 이상 세션 시 자동 샘플링
- **메모리 사용**: 각 세션 독립적으로 파싱하여 메모리 효율적
- **속도**: 10개 세션 파싱에 약 1-2초 소요

## 다음 단계

- [ ] 주간/월간 요약 자동 생성
- [ ] 웹 대시보드 통합
- [ ] 시각화 (차트/그래프)
- [ ] Git 통계 연동
- [ ] 슬랙/이메일 알림

## 지원

문제가 발생하면:

1. README.md 참조
2. SKILL.md 워크플로우 확인
3. GitHub Issue 생성
