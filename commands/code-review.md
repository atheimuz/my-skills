---
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
---

# Code Review

React/TypeScript 코드를 6개 관점에서 종합 리뷰합니다.

## 사용법

```
/code-review [target]
```

- `target`: 리뷰 대상 (파일, 폴더, 또는 생략 시 src/)

예시:
- `/code-review` - src/ 폴더 전체 리뷰
- `/code-review src/components/Button.tsx` - 특정 파일 리뷰
- `/code-review src/features/auth` - 특정 폴더 리뷰

## 워크플로우

### Phase 1: 리뷰 대상 파악

1. target이 지정되면 해당 경로 사용
2. 지정되지 않으면 `src/` 폴더를 기본값으로 사용
3. 대상 파일 목록 확인

### Phase 2: 6개 에이전트 병렬 실행

단일 메시지에서 6개 Task tool을 **동시 호출**:

```
Task(subagent_type="architecture-reviewer", prompt="[대상] 아키텍처 리뷰")
Task(subagent_type="security-reviewer", prompt="[대상] 보안 리뷰")
Task(subagent_type="maintainability-reviewer", prompt="[대상] 유지보수성 리뷰")
Task(subagent_type="a11y-reviewer", prompt="[대상] 접근성 리뷰")
Task(subagent_type="performance-reviewer", prompt="[대상] 성능 리뷰")
Task(subagent_type="type-safety-reviewer", prompt="[대상] 타입 안전성 리뷰")
```

**에이전트 역할:**
| 에이전트 | 색상 | 검토 영역 |
|---------|------|----------|
| architecture-reviewer | blue | 컴포넌트 구조, 의존성 |
| security-reviewer | red | XSS, 민감정보, API 보안 |
| maintainability-reviewer | green | 가독성, 복잡도, 명명 규칙 |
| a11y-reviewer | purple | ARIA, 키보드, 스크린 리더 |
| performance-reviewer | orange | 리렌더링, 번들, 메모리 누수 |
| type-safety-reviewer | cyan | any 사용, Generic, strict typing |

### Phase 3: 결과 통합

1. 모든 에이전트 결과를 심각도별 정렬
2. 중복 이슈 병합
3. 실행 가능한 액션 아이템 생성

## 출력 형식

```markdown
# React Code Review 종합 결과

## Summary
- Critical: X개
- High: X개
- Medium: X개

## Critical Issues (91-100)

### Security
- [이슈] `파일:라인` - 설명

### Performance
- [이슈] `파일:라인` - 설명

## High Issues (76-90)

### Architecture
- [이슈] `파일:라인` - 설명

### Type Safety
- [이슈] `파일:라인` - 설명

...

## Action Items
1. [ ] 즉시 수정: ...
2. [ ] 권장 수정: ...
3. [ ] 개선 고려: ...
```

## 심각도 기준

| 점수 | 레벨 | 의미 |
|-----|------|------|
| 91-100 | Critical | 반드시 수정 |
| 76-90 | High | 수정 권장 |
| 51-75 | Medium | 개선 고려 |
| 0-50 | Low | 참고 사항 |

## 주의사항

- 80점 이상 이슈만 보고
- 각 이슈에 구체적인 파일 경로와 라인 번호 포함
- 해결 방안은 실행 가능한 수준으로 제시
- 중복 이슈는 병합하여 보고
- 6개 에이전트는 반드시 **병렬로** 실행 (단일 메시지에 6개 Task call)
