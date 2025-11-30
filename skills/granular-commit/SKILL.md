---
name: granular-commit
description: >
  Git 변경사항을 hunk/줄 단위로 분석하여 세밀한 논리적 커밋으로 분리.
  한 파일 내에서도 변경 내용을 의미 단위로 나눠 개별 커밋 생성.
  /granular-commit, "커밋 나눠줘", "세세하게 커밋", "변경사항 분리",
  "atomic commit", "커밋 쪼개줘" 등으로 트리거.
---

# Granular Commit

변경사항을 의미 단위로 분석하여 세밀한 커밋으로 분리.

## 워크플로우

### 1단계: 변경사항 수집

```bash
# 전체 변경사항 백업
git diff HEAD > /tmp/gc_full_backup.patch

# staged + unstaged 변경사항 확인
git diff HEAD

# untracked 파일 확인
git status --porcelain
```

### 2단계: Hunk 분석

`git diff HEAD` 출력을 직접 읽고 각 hunk를 의미적으로 분석:
- 어떤 논리적 변경인가? (버그 수정, 기능 추가, 리팩토링, 스타일 변경 등)
- 서로 관련된 hunk는 무엇인가? (같은 기능의 다른 파일, 호출부와 정의부 등)
- 하나의 hunk 안에서도 독립적인 변경이 섞여 있으면 줄 단위로 분리

### 3단계: 커밋 계획 제시

사용자에게 AskUserQuestion으로 커밋 분리 계획 제시:

```
커밋 분리 계획:

1. feat(auth): 로그인 에러 핸들링 추가
   - src/auth/login.ts (@@ -82,7 +82,10 @@)
   - src/auth/errors.ts (@@ -1,0 +1,15 @@)

2. refactor(utils): 날짜 포맷 함수 분리
   - src/utils/date.ts (@@ -20,5 +20,12 @@)

3. fix(api): 응답 타입 수정
   - src/api/types.ts (전체)
   - src/api/client.ts (@@ -45,8 +45,8 @@ 중 줄 47-49만)
```

사용자 승인/수정 후 실행.

### 4단계: 순차적 커밋 실행

각 커밋 그룹에 대해:

1. 첫 커밋 전: `git stash`로 모든 변경사항 보관
2. `git stash show -p` 출력에서 해당 그룹의 hunk만 골라 patch 파일 작성 (Write 도구 사용)
3. `git apply /tmp/gc_groupN.patch` → `git add -A` → `git commit`
4. `git stash pop`으로 나머지 복원
5. 다음 그룹 반복

#### Patch 파일 작성 규칙

diff 출력에서 원하는 hunk만 골라 유효한 patch 파일을 직접 구성:

```
diff --git a/파일경로 b/파일경로
index abc1234..def5678 100644
--- a/파일경로
+++ b/파일경로
@@ -시작줄,개수 +시작줄,개수 @@ 섹션명
 컨텍스트 줄
-삭제 줄
+추가 줄
```

**줄 단위 선택 시** (하나의 hunk에서 일부 줄만 커밋):
- 포함하지 않을 `+` 줄: 삭제
- 포함하지 않을 `-` 줄: `-`를 ` `(공백)으로 바꿔 컨텍스트로 변환
- hunk header의 라인 카운트 재계산:
  - old count = `-` 줄 수 + 컨텍스트(` `) 줄 수
  - new count = `+` 줄 수 + 컨텍스트(` `) 줄 수

**중요**: 각 커밋 후 `git stash pop`에서 충돌 가능. 충돌 시:
1. `git checkout --theirs .` 또는 수동 해결
2. `git stash drop`으로 stash 정리

### 5단계: 완료 확인

```bash
git log --oneline -10
git diff HEAD  # 남은 변경사항 확인
```

## 커밋 메시지 규칙

한글 Conventional Commits: `<타입>(<범위>): <설명>`

| 타입 | 용도 |
|------|------|
| feat | 새 기능 |
| fix | 버그 수정 |
| refactor | 리팩토링 |
| style | 포맷팅, 세미콜론 등 |
| docs | 문서 수정 |
| test | 테스트 |
| chore | 빌드, 의존성 등 |

## Edge Cases

- **Untracked 파일**: `git add`로 별도 처리. 커밋 그룹에 포함 여부 질문.
- **Binary 파일**: hunk 분석 불가. 별도 커밋으로 처리.
- **파일 삭제**: 관련 변경사항과 같은 커밋에 포함.
- **patch 적용 실패**: `git apply --reject`로 재시도. 실패 시 사용자에게 알림.
- **변경사항 없음**: 조기 종료.

## 안전장치

- 작업 전 `/tmp/gc_full_backup.patch`에 전체 diff 백업
- 모든 커밋 전 계획 미리보기 필수
- 실패 시 `git apply /tmp/gc_full_backup.patch`로 복구
