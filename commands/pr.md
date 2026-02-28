---
allowed-tools: Bash(gh:*), Bash(git status:*), Bash(git diff:*), Bash(git branch:*), Bash(git log:*), Bash(git remote:*)
description: PR 생성 (커밋 히스토리 기반 자동 본문 작성)
---

## 컨텍스트

- 현재 브랜치: !`git branch --show-current`
- 리모트 상태: !`git remote -v | head -1`
- 최근 커밋: !`git log --oneline -5`

## 작업

### 1. 사전 확인

- gh CLI 인증 상태 확인: `gh auth status`
- 인증 안됨 → 사용자에게 `gh auth login` 실행 안내

### 2. 브랜치 선택

AskUserQuestion 도구를 사용하여 다음 질문:

1. **Source 브랜치**: 현재 브랜치를 기본값으로 제안
   - 질문: "Source 브랜치를 선택하세요"
   - 옵션: 현재 브랜치 (기본), 다른 브랜치 직접 입력

2. **Target(base) 브랜치**: 사용자에게 항상 질문
   - 질문: "Target(base) 브랜치를 선택하세요"
   - 옵션: main, develop, staging, 다른 브랜치 직접 입력

### 3. 변경사항 분석

```bash
# PR에 포함될 커밋 목록
git log <base>..HEAD --oneline

# 변경 파일 통계
git diff <base>...HEAD --stat
```

### 4. PR 본문 작성

커밋 히스토리와 diff를 분석하여 다음 형식으로 작성.
Background에는 변경 동기(문제점, 개선 필요성, 요청 배경 등)를 파악하여 채운다:

```markdown
## Background

- (이 변경을 하게 된 배경/동기 — 왜 이 작업이 필요했는지)

## Summary

- (주요 변경사항 요약 - 불릿 포인트)

## Changes

### 새로운 기능

- (신규 컴포넌트/기능 목록)

### 리팩토링

- (리팩토링 내용)

### 테스트

- (테스트 관련 변경사항)

## Test plan

- (테스트 항목 목록)
- npm test
```

### 5. PR 생성

```bash
gh pr create \
  --base <base-branch> \
  --head <current-branch> \
  --title "<커밋 타입>: <요약>" \
  --body "<본문>"
```

### 6. 결과 출력

- 생성된 PR URL 표시
