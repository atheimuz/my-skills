---
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - AskUserQuestion
---

# PR 생성

코드 리뷰어가 빠르게 이해할 수 있는 PR 설명을 작성하고 PR을 생성합니다.

## 사용법

```
/pr
```

## 워크플로우

### Phase 1: 브랜치 확인 및 선택

1. 현재 브랜치와 원격 브랜치 목록을 확인:

```bash
git branch --show-current
git branch -a --sort=-committerdate
```

2. AskUserQuestion으로 사용자에게 확인:

```
어떤 브랜치에서 어떤 브랜치로 PR을 생성할까요?

- source 브랜치 (현재: {현재 브랜치})
- target 브랜치 (예: main, develop)
```

옵션 구성:
- target 브랜치 후보를 최대 4개까지 옵션으로 제시 (main, develop 등 주요 브랜치 우선)
- source 브랜치는 현재 브랜치를 기본값으로 사용하되, 변경 원하면 "Other"로 입력 가능하도록 안내

### Phase 2: 변경사항 분석

1. source와 target 브랜치 간 diff 수집:

```bash
# 커밋 히스토리
git log {target}..{source} --oneline --no-merges

# 변경된 파일 목록
git diff {target}...{source} --stat

# 상세 diff
git diff {target}...{source}
```

2. 변경사항을 분석하여 다음을 파악:
   - 변경 목적 (기능 추가, 버그 수정, 리팩토링 등)
   - 영향 범위 (어떤 모듈/기능에 영향)
   - Breaking changes 여부
   - 테스트 변경 여부

### Phase 3: PR 설명 작성

아래 양식에 맞춰 PR 제목과 본문을 작성:

**제목**: 70자 이내, 변경의 핵심을 한 문장으로

**본문**:

```markdown
## 요약
- 이 PR의 목적과 배경을 2-3문장으로 설명
- "왜" 이 변경이 필요한지 중심으로

## 변경사항
- 파일/모듈 단위로 주요 변경 내용 나열
- 단순 리팩토링과 기능 변경을 구분하여 표시
- 중요도순으로 정렬

## 테스트 가이드
- 리뷰어가 집중적으로 확인해야 할 시나리오 리스트
- 엣지 케이스나 회귀 가능성이 있는 부분 명시
- 구체적인 시나리오로 작성 (ex: "로그인 후 마이페이지 접근 시 권한 체크 확인")

## Breaking Changes
- 기존 동작이 달라지는 부분 (없으면 "없음")
- 마이그레이션 필요 시 방법 안내

## 관련 이슈
- 연관된 티켓/이슈 번호 (없으면 "없음")

## 스크린샷
- UI 변경이 있을 경우 Before/After (없으면 섹션 생략)
```

### Phase 4: 사용자 확인 및 PR 생성

1. 작성한 PR 제목과 본문을 사용자에게 보여주고 AskUserQuestion으로 확인:

```
위 내용으로 PR을 생성할까요?
- 네, 생성합니다
- 수정이 필요합니다
```

2. 사용자가 승인하면:

```bash
# 원격에 source 브랜치 push (필요한 경우)
git push -u origin {source}

# PR 생성
gh pr create --base {target} --head {source} --title "{제목}" --body "$(cat <<'EOF'
{본문}
EOF
)"
```

3. 생성된 PR URL을 사용자에게 전달.

## 작성 규칙

- 간결하게, 불필요한 수식어 제거
- 기술적 용어는 팀이 이해할 수 있는 수준으로
- 변경사항은 중요도순으로 정렬
- 테스트 가이드는 구체적인 시나리오로
- UI 변경이 없으면 스크린샷 섹션 생략
- 관련 이슈가 없으면 "없음"으로 표시

## Edge Cases

- **push되지 않은 커밋**: Phase 4에서 자동으로 push
- **충돌 발생**: 사용자에게 충돌 상태 알리고 해결 후 재시도 안내
- **gh CLI 미설치**: 설치 안내 메시지 출력
- **변경사항 없음**: target과 source가 동일하면 조기 종료
