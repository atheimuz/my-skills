# Bug Fix Workflow Skill

버그 수정 워크플로우 스킬. 분석 → 수정 → 테스트 → 검증 파이프라인을 자동화합니다.

## Triggers

- `/bug-fix`
- `버그 수정`
- `버그 분석`
- `bug fix`

## Description

버그 수정 과정을 체계화된 파이프라인으로 실행합니다:
- 심각도에 따라 단순/복합 워크플로우 자동 선택
- 분석 → 수정 → 테스트 → 검증 단계별 진행
- 프로젝트별 산출물 자동 생성

## Usage

```bash
# 기본 사용
/bug-fix

# 버그 설명과 함께
/bug-fix 로그인 버튼 클릭 시 에러 발생
```

## Workflow

### 단순 버그 (Minor)
- UI 오타, 스타일 문제 등
- 빠른 분석+수정 후 테스트

### 복합 버그 (Major/Critical)
1. **분석**: 근본 원인 파악 (bug-analyzer)
2. **사용자 확인**: 분석 결과 검토
3. **수정**: 코드 수정 (bug-fixer)
4. **테스트**: 회귀 테스트 작성 (regression-tester)
5. **검증**: 테스트 실행 및 확인 (verification-agent)
6. **최종 확인**: 사용자 검토

## Outputs

프로젝트 내 `.claude/bug-reports/{id}/`에 저장:
- `analysis.md` - 분석 리포트
- `fix-plan.md` - 수정 계획
- `test-scenarios.md` - 테스트 시나리오
- `verification.md` - 검증 결과

## Instructions

<instruction>
이 스킬이 트리거되면 다음을 수행하세요:

### 1. 버그 정보 수집

$ARGUMENTS가 있으면 버그 설명으로 사용합니다. 없으면 사용자에게 질문합니다.

AskUserQuestion으로 심각도를 확인합니다:
- **Minor**: UI 오타, 스타일 깨짐 등 기능에 영향 없음
- **Major**: 주요 기능 오류, 데이터 표시 문제
- **Critical**: 앱 크래시, 데이터 손실, 보안 이슈

에러 로그나 재현 단계가 있다면 추가로 수집합니다.

### 2. 산출물 디렉토리 생성

```bash
mkdir -p .claude/bug-reports/$(date +%Y-%m-%d-%H-%M)-{short-id}
```

### 3. 파이프라인 실행

**Minor 버그**:
- 분석과 수정을 통합하여 빠르게 처리
- **UI/인터랙션 버그인 경우**: 수정 전에 Playwright 검증 테스트를 먼저 작성하고, 수정 후 테스트 통과를 확인한다. 빌드 성공만으로 검증 완료로 간주하지 않는다. 테스트 파일은 임시 파일로 생성하고 검증 완료 후 삭제한다.
- **그 외 버그**: 간단한 테스트 작성 및 실행
- 자체 검증 통과 후 최종 결과를 사용자에게 보고

**Major/Critical 버그**:
- `~/.claude/agents/bug-fix/bug-analyzer.md` 참조하여 분석 수행
- 분석 결과를 사용자에게 확인 (AskUserQuestion)
- `~/.claude/agents/bug-fix/bug-fixer.md` 참조하여 수정 수행
- `~/.claude/agents/bug-fix/regression-tester.md` 참조하여 테스트 작성
- `~/.claude/agents/bug-fix/verification-agent.md` 참조하여 검증 수행
- 최종 확인: 사용자 검토

### 심각도 분류 보충 규칙

다음 특성을 가진 버그는 Minor처럼 보여도 **Major로 분류**한다:
- 첫 시도와 재시도의 동작이 다른 경우 (상태, 캐시, 초기화 순서 등 내부 조건에 따라 결과가 달라짐)
- 수정 방향이 직관적으로 명확하지 않은 경우 (어느 레이어를 고쳐야 하는지 불분명)
- 프레임워크/플랫폼 내부 상태(이벤트 라우팅, 생명주기, 활성화 상태 등)에 의존하는 동작

Major로 분류 시: formal bug-analyzer 분석 단계를 거친다. 직감 기반 빠른 수정으로 시작하지 않는다.

### 핵심 검증 규칙 (심각도 무관)

**가정 검증 우선 원칙:**
- 프레임워크 동작(마운트/언마운트 타이밍, 상태 유지 여부, 라이프사이클 순서)에 의존하는 구현 시, 가정을 console.log 또는 테스트 코드로 먼저 검증한 후 구현한다.
- "아마 이렇게 동작할 것" 기반의 구현은 금지한다.

**2회 실패 시 전환 규칙:**
- 동일 버그에 대해 같은 접근법(같은 파일/같은 패턴)으로 2회 수정해도 해결되지 않으면, 즉시 Playwright 등으로 현재 동작을 진단하는 테스트를 작성하여 실제 동작을 확인한 후 접근법을 전환한다.
- 3회 이상 같은 접근법을 반복하지 않는다.

**자체 검증 필수 원칙:**
- 사용자에게 "확인해보세요"라고 요청하기 전에, 가능한 범위에서 자체 검증(빌드, 테스트 실행, dev 서버 + Playwright)을 먼저 수행한다.
- 빌드 성공 ≠ 버그 수정 완료. 실제 동작 검증이 필요하다.
- **자동화 검증이 불가한 버그** (UI 인터랙션, 외부 상태 의존, 환경 의존 동작 등): 수동 재현 체크리스트를 작성하여 사용자에게 제공한다. 형식: "[사전 조건 설정] → [재현 단계] → [예상 결과] 확인"

### 4. 프로젝트 컨텍스트 활용

- CLAUDE.md가 있다면 프로젝트 규칙 준수
- package.json에서 테스트 프레임워크 및 명령어 감지
- 기존 테스트 패턴 분석 및 일관성 유지

### 5. 결과 보고

수정 요약, 변경된 파일, 테스트 결과를 간결하게 보고합니다.
</instruction>

## Related Files

- `~/.claude/agents/bug-fix/bug-analyzer.md`
- `~/.claude/agents/bug-fix/bug-fixer.md`
- `~/.claude/agents/bug-fix/regression-tester.md`
- `~/.claude/agents/bug-fix/verification-agent.md`
- `~/.claude/commands/bug-fix.md`
- `~/.claude/skills/bug-fix-workflow/patterns/common-bugs.md`
