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
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date $(date +%Y-%m-%d)
```

### 특정 날짜 분석

```bash
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date 2026-02-10
```

### 날짜 범위 분석

```bash
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date-range 2026-02-01 2026-02-10
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

## 분석 결과 구조

`analyze_sessions.py`의 출력 JSON 구조:

```json
{
  "date_range": {
    "start": "2026-02-11",
    "end": "2026-02-11"
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
    "libraries": {"tailwind": 1}
  },
  "task_types": {
    "Coding": 2,
    "Planning": 1
  },
  "tool_usage": {
    "Bash": 10,
    "Write": 8,
    "Read": 6
  },
  "thinking_insights": [
    "[결정] Python 스크립트로 파싱 로직 구현하기로 결정",
    "[해결] JSONL 파싱 문제를 해결"
  ],
  "workflow_patterns": [
    "Read → Write → Bash (3회)",
    "Grep → Read → Edit (2회)"
  ],
  "session_details": [
    {
      "task_types": ["Coding"],
      "summary": "컴포넌트 구현 작업...",
      "message_count": 15,
      "tool_call_count": 8,
      "skill_calls": [],
      "task_calls": [],
      "commands_used": ["npm test", "git status"]
    }
  ],
  "scoring": {
    "complexity": "Medium",
    "total_score": 84,
    "grade": "A",
    "categories": {
      "intent": {"score": 22, "max": 25},
      "efficiency": {"score": 25, "max": 30},
      "tool_fitness": {"score": 20, "max": 25},
      "workflow": {"score": 17, "max": 20}
    },
    "good_points": ["명확한 초기 지시로 수정 없이 작업 완료"],
    "improve_points": ["Bash에서 grep 대신 Grep 전용 도구 활용 권장"]
  }
}
```

## 팁과 트릭

### 1. 여러 날짜 일괄 분석

```bash
# 최근 7일 각각 분석
for i in {0..6}; do
  date=$(date -v-${i}d +%Y-%m-%d)
  python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date $date > /tmp/analysis-$date.json
done
```

### 2. 주간 요약 생성

```bash
# 이번 주 월요일부터 오늘까지
monday=$(date -v-Mon +%Y-%m-%d)
today=$(date +%Y-%m-%d)
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date-range $monday $today
```

### 3. jq로 필터링

```bash
# 가장 많이 사용한 언어 Top 3
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date 2026-02-11 | \
  jq -r '.tech_stack.languages | to_entries | sort_by(-.value) | .[0:3] | .[] | "\(.key): \(.value)회"'
```

### 4. 도구 사용 통계만 보기

```bash
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date 2026-02-11 | \
  jq '.tool_usage'
```

### 5. 활용도 점수만 보기

```bash
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date 2026-02-11 | \
  jq '.scoring'
```

## 문제 해결

### "선택한 기간에 세션이 없습니다"

**원인**: 해당 날짜에 세션 파일이 없음

**해결**:
```bash
# 세션 파일의 날짜 확인
python3 ~/.claude/skills/session-analyzer/utils/analyze_sessions.py --date $(date +%Y-%m-%d)
# 에러 메시지에서 찾은 세션 수 확인
```

### JSON 파싱 오류

**원인**: JSONL 파일이 손상되었거나 형식이 잘못됨

**해결**:
- 스크립트가 손상된 파일을 자동으로 스킵합니다
- 일반적으로 별도 조치 불필요

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

## 고급 사용법

### 커스텀 키워드 추가

`utils/analyze_sessions.py` 파일의 상단 키워드 리스트를 수정:

```python
LANGUAGE_KEYWORDS = [
    'python', 'javascript', 'typescript',
    'my-custom-language',  # 추가
]
```

### 작업 유형 커스터마이징

```python
TASK_TYPE_KEYWORDS = {
    'Coding': ['구현', 'implement', 'create'],
    'Design': ['디자인', 'design', 'ui', 'ux'],  # 새로운 유형 추가
}
```

### 마크다운 템플릿 변경

SKILL.md의 4단계 "마크다운 템플릿" 섹션을 수정하여 출력 형식 커스터마이징

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
