# My Skills

Claude Code에서 사용할 수 있는 커스텀 서브에이전트, 커맨드, 스킬 모음입니다.

## 구조

| 디렉토리 | 설명 | 상태 |
|---|---|---|
| [agents/](./agents/) | Task tool 서브에이전트 | 사용 가능 |
| [commands/](./commands/) | 슬래시 커맨드 | 사용 가능 |
| [skills/](./skills/) | Claude Code 스킬 | 사용 가능 |

---

## Agents

Claude Code의 Task tool에서 서브에이전트로 동작하는 커스텀 에이전트 모음입니다.

### 설치

```bash
cp -r agents/* ~/.claude/agents/
```

`~/.claude/agents/` 디렉토리에 에이전트 폴더를 복사하면 Claude Code가 자동으로 인식합니다.

### 에이전트 요약

| 에이전트 | 모델 | 역할 | 그룹 |
|---------|------|------|------|
| product-spec-writer | Opus | 기능 명세서 작성 | 기획/설계 (planning) |
| ui-designer | Sonnet | 디자인 명세서 작성 | 기획/설계 (planning) |
| ux-researcher | Opus | UX 분석 | 기획/설계 (planning) |
| code-analyst | Sonnet | 구현 가이드 생성 | 기획/설계 (planning) |
| playwright-e2e-tester | Sonnet | E2E 테스트 작성 | 테스트 (testing) |
| test-consolidator | Sonnet | TDD 테스트 통합/정리 | 테스트 (testing) |
| bug-analyzer | Sonnet | 버그 근본 원인 분석 | 버그 수정 (bug-fix) |
| bug-fixer | Sonnet | 최소 범위 코드 수정 | 버그 수정 (bug-fix) |
| regression-tester | Sonnet | 회귀 방지 테스트 작성 | 버그 수정 (bug-fix) |
| verification-agent | Haiku | 테스트 실행 및 종합 검증 | 버그 수정 (bug-fix) |
| architecture-reviewer | Sonnet | 컴포넌트 구조, 의존성 | 코드 리뷰 (code-review) |
| security-reviewer | Sonnet | XSS, 민감정보, API 보안 | 코드 리뷰 (code-review) |
| maintainability-reviewer | Sonnet | 가독성, 복잡도, 명명 규칙 | 코드 리뷰 (code-review) |
| a11y-reviewer | Sonnet | ARIA, 키보드, 스크린 리더 | 코드 리뷰 (code-review) |
| performance-reviewer | Sonnet | 리렌더링, 번들, 메모리 누수 | 코드 리뷰 (code-review) |
| type-safety-reviewer | Sonnet | any 사용, Generic, strict typing | 코드 리뷰 (code-review) |
| react-review | Sonnet | 6개 리뷰어 병렬 실행 오케스트레이터 | 코드 리뷰 (code-review) |
| checklist-summary | - | 코드 리뷰 참고 체크리스트 | 코드 리뷰 (code-review) |

### 기획/설계 에이전트 (planning)

#### product-spec-writer (기획자)

| 항목 | 값 |
|---|---|
| 모델 | Opus |
| 도구 | Glob, Grep, Read, WebFetch, WebSearch |

기능 아이디어나 제품 컨셉을 받아 디자이너와 개발자를 위한 **상세 기능 명세서**를 작성하는 시니어 기획자 에이전트입니다.

**모드 A: 신규 기능 기획**

사용자가 새로운 기능을 설명하면 다음 순서로 명세서를 작성합니다:

1. **사용자 관점 정리** — 대상 사용자, 목적/동기, 기대 행동 흐름, 예외 상황
2. **기능 명세서 출력** — 아래 구조를 따릅니다:
   - 기능명 / 기능 요약
   - 사용자 스토리 (`As a [사용자], I want to [행동], so that [목적]`)
   - 상세 사용자 흐름 (진입점 → 각 단계 → 완료/실패)
   - 화면별 요구사항 (디자이너용) — UI 요소, 상태(기본/로딩/에러/빈 상태)
   - 기능 요구사항 (개발자용) — 데이터, API, 비즈니스 로직, 유효성 검증
   - 예외 처리 및 엣지 케이스
   - 우선순위 및 MVP 범위 제안

**모드 B: 기존 기능 분석 및 재설계**

기존 프로젝트 코드를 분석하여 현행(AS-IS) 명세서와 재설계(TO-BE) 명세서를 작성합니다.

1. **코드베이스 분석** — 디렉토리 구조, 라우트, 데이터 모델, API, 컴포넌트, 상태 관리 탐색
2. **AS-IS 명세서** — 프로젝트 개요, 기능 목록, 화면별 현황, 데이터 구조, 문제점/개선 기회
3. **TO-BE 명세서** — AS-IS→TO-BE 비교표, 화면별/기능별 변경사항, 마이그레이션 고려사항, 단계별 실행 제안

**트리거 예시**

```
"프로필 사진 변경 기능을 만들고 싶어"        → 모드 A
"알림 기능을 추가하고 싶은데"               → 모드 A
"이 프로젝트 기능을 파악하고 재설계하고 싶어" → 모드 B
"기존 검색 기능을 분석해서 개선안을 만들어줘" → 모드 B
```

---

#### ui-designer (UI 디자이너)

| 항목 | 값 |
|---|---|
| 모델 | Sonnet |
| 도구 | Read, Glob, Write |

기획서/요구사항을 분석하여 개발자가 바로 구현할 수 있는 **디자인 명세서**를 작성하는 시니어 UI 설계 에이전트입니다. 구현 코드는 작성하지 않습니다.

**모드 A: 신규 설계**

기획 명세서, 와이어프레임, 요구사항 문서를 받아 디자인 명세서로 변환합니다.

**모드 B: 리뉴얼 설계**

기존 구현된 화면을 분석하고 개선 디자인 명세서를 작성합니다. 정보 계층, 레이아웃 효율, 컴포넌트 활용, 반응형, 접근성, 코드 구조 관점에서 문제점을 도출합니다.

**작업 프로세스 (3단계)**

1. **프로젝트 컨텍스트 파악** — 프레임워크, UI 라이브러리, 공통 컴포넌트, 디자인 시스템/토큰, 기존 패턴 탐색
2. **입력 분석** — 기획서 분석(모드 A) 또는 기존 화면 분석(모드 B)
3. **디자인 명세서 작성** — `DESIGN_SPEC.md` 출력:
   - 화면 구조 (ASCII 와이어프레임)
   - 섹션별 명세 (역할, 컴포넌트, 레이아웃, 데이터, 인터랙션)
   - 반응형 설계 (브레이크포인트별 변화)
   - 상태별 UI (로딩/빈 상태/에러/부분 로딩)
   - 인터랙션 상세 (요소 → 이벤트 → 동작)
   - 신규 컴포넌트 (기존에 없는 것만)
   - 접근성 요구사항
   - 리뉴얼 변경사항 (모드 B)

**트리거 예시**

```
"기획서대로 대시보드 화면 설계해줘"     → 모드 A
"이 명세서로 프로필 페이지 설계해줘"    → 모드 A
"이 페이지 레이아웃 리뉴얼 설계해줘"   → 모드 B
"이 화면 반응형 설계 명세 만들어줘"    → 모드 B
```

---

#### ux-researcher (UX 리서처)

| 항목 | 값 |
|---|---|
| 모델 | Opus |
| 도구 | Read, Glob, Grep, WebFetch, WebSearch |

기획 명세서를 UX 관점에서 분석하여 UI Designer에게 인사이트를 제공하는 에이전트입니다. 디자인을 직접 만들지 않고, 사용성 문제와 개선 권장사항을 도출합니다.

**분석 영역**

- **휴리스틱 평가** — Jakob Nielsen의 10가지 휴리스틱 기준 평가
- **사용자 흐름 분석** — 목표까지의 단계 수, 분기점, 이탈 위험 지점
- **정보 구조 분석** — 정보 계층, 그룹핑, 레이블 적절성
- **인지 부하 분석** — 화면 정보량, 선택지 수, 기억 의존도
- **접근성 분석** — 키보드 내비게이션, 색상 외 정보 전달

**출력물**

`UX_ANALYSIS.md` — 이슈 목록(Critical/Major/Minor), 휴리스틱 평가 결과, UI Designer를 위한 핵심 권장사항

**트리거 예시**

```
"이 기획서 UX 분석해줘"
"사용자 흐름에 문제 없는지 검토해줘"
"기획서의 사용성 이슈 찾아줘"
```

---

#### code-analyst (코드 패턴 분석가)

| 항목 | 값 |
|---|---|
| 모델 | Sonnet |
| 도구 | Read, Glob, Grep, Write |

구현 전 프로젝트의 CLAUDE.md와 기존 코드 패턴을 수집하여 **구현 가이드**를 생성하는 에이전트입니다. 새 기능 구현 시 기존 패턴을 준수하도록 보장합니다. 구현 코드는 작성하지 않습니다.

**3-Tier 탐색**

1. **Tier 1: CLAUDE.md 수집** (필수) — 프로젝트 내 모든 CLAUDE.md에서 코딩 패턴, 사용 가능한 컴포넌트, 금지 사항 추출
2. **Tier 2: 유사 코드 검색** (보완) — 기존 코드에서 유형별 1-2개만 검색하여 실전 사용 예시 확인
3. **Tier 3: 직접 탐색** (Fallback) — CLAUDE.md가 없을 때만 프로젝트 구조 직접 탐색

**출력물**

`specs/{feature}/implementation-guide.md` — 재사용 컴포넌트, 금지 사항, 참고 코드, 코딩 규칙, Mock Data 전략

**트리거 예시**

```
"구현 가이드 만들어줘"
"implementation guide 생성해줘"
"기존 코드 패턴 분석해줘"
```

---

### 테스트 에이전트 (testing)

#### playwright-e2e-tester (E2E 테스터)

| 항목 | 값 |
|---|---|
| 모델 | Sonnet |
| 도구 | Glob, Grep, Read, Write, Edit, Bash |

`specs/{feature}/plan.md` 기반으로 테스트 시나리오를 작성하고, `test-scenarios.md` 기반으로 Playwright E2E 테스트 코드를 구현하는 에이전트입니다.

**핵심 기능**

- **테스트 시나리오 작성** — plan.md → test-scenarios.md 변환
- **테스트 코드 구현** — test-scenarios.md 항목을 Playwright 테스트로 변환
- **"go" 명령어** — 다음 미완료 테스트를 자동으로 찾아 구현

**Red-Green 사이클**

1. test-scenarios.md에서 테스트 항목 가져오기
2. 실패하는 E2E 테스트 작성 (Red)
3. 테스트 통과 대기 또는 다음으로 이동 (Green)
4. test-scenarios.md 업데이트 및 커밋

**산출물**

- `specs/{feature}/test-scenarios.md` — 테스트 시나리오 문서
- `tests/mocks/{feature}.mock.ts` — 목업 데이터
- `tests/{feature}/*.spec.ts` — 테스트 코드

**트리거 예시**

```
/e2e
"E2E 테스트 작성해줘"
"go" (다음 테스트 구현)
```

---

#### test-consolidator (테스트 통합)

| 항목 | 값 |
|---|---|
| 모델 | Sonnet |
| 도구 | 전체 도구 |

TDD 과정에서 생성된 세분화된 테스트를 사용자 시나리오 단위로 통합하고 정리하는 에이전트입니다. 중복/불필요한 테스트를 식별하고, Given-When-Then 패턴의 시나리오 테스트로 리팩토링합니다.

**테스트 유형 분류**

| 유형 | 특징 | 처리 방침 |
|-----|------|----------|
| 단순 렌더링 | `expect(element).toBeVisible()` 만 있음 | 삭제 후보 |
| 단일 검증 | 하나의 액션 + 하나의 검증 | 통합 후보 |
| 시나리오 | 여러 단계 + 최종 검증 | 유지 |

**워크플로우**: 대상 테스트 분석 → 유형 분류 → 통합 제안 생성 → POM 정리

**트리거 예시**

```
"테스트 정리해줘"
"signin 테스트 통합해줘"
"렌더링 테스트들 정리해줘"
```

---

### 버그 수정 에이전트 (bug-fix)

`agents/bug-fix/` 디렉토리에 위치하며, `/bug-fix` 커맨드에서 심각도에 따라 순차적으로 실행됩니다.

| 에이전트 | 역할 | 산출물 |
|---------|------|--------|
| bug-analyzer | 에러 로그/재현 조건 분석, 근본 원인 파악 | analysis.md |
| bug-fixer | 분석 결과 기반 최소 범위 수정 | fix-plan.md + 코드 수정 |
| regression-tester | 버그 재현 + 회귀 방지 테스트 작성 | test-scenarios.md + 테스트 코드 |
| verification-agent | 테스트 실행 및 수정사항 종합 검증 | verification.md |

#### bug-analyzer (버그 분석가)

에러 로그와 재현 조건을 분석하여 근본 원인을 파악하는 에이전트입니다. 5 Whys 기법으로 증상과 근본 원인을 구분하고, 8가지 버그 유형으로 분류합니다.

**버그 유형 분류**

| 유형 | 설명 |
|-----|------|
| null-undefined | null/undefined 참조 에러 |
| async-error | 비동기 처리 에러 |
| race-condition | 경쟁 상태 |
| type-coercion | 타입 변환 오류 |
| state-sync | 상태 동기화 오류 |
| render-error | 렌더링 오류 |
| event-handler | 이벤트 핸들링 오류 |
| dependency | 의존성 문제 |

**분석 절차**: 증상 수집 → 버그 유형 분류 → 근본 원인 분석 (5 Whys) → 영향 범위 분석

---

#### bug-fixer (버그 수정가)

분석 리포트(`analysis.md`)를 기반으로 최소 범위의 정확한 코드 수정을 수행하는 에이전트입니다.

**수정 원칙**

- 최소 변경 원칙: 버그 수정에 필요한 최소한의 코드만 변경
- 기존 스타일 유지: CLAUDE.md 규칙 준수, 주변 코드 패턴 일치
- 안전한 수정: 타입 안전성 유지, 사이드 이펙트 최소화

---

#### regression-tester (회귀 테스터)

버그 재현 테스트와 회귀 방지 테스트를 작성하는 에이전트입니다. 프로젝트의 테스트 프레임워크(Playwright/Vitest/Jest 등)를 자동 감지하여 AAA 패턴(Arrange-Act-Assert)으로 테스트를 작성합니다.

---

#### verification-agent (검증 에이전트)

테스트를 실행하고 수정 사항을 종합 검증하는 에이전트입니다. 새 테스트, 관련 테스트, 전체 테스트를 단계적으로 실행하며, 수동 검증 체크리스트도 제공합니다.

---

### 코드 리뷰 에이전트 (code-review)

`agents/code-review/` 디렉토리에 위치하며, `/code-review` 커맨드 또는 `react-review` 에이전트에서 6개를 병렬로 실행합니다.

| 에이전트 | 모델 | 색상 | 검토 영역 |
|---------|------|------|----------|
| architecture-reviewer | Sonnet | blue | 컴포넌트 구조(SRP, 300줄 초과), 폴더 구조 일관성, 순환 의존성, 도메인 경계 |
| security-reviewer | Sonnet | red | XSS(dangerouslySetInnerHTML), 민감정보 노출, API 보안(CSRF), 위험 패턴(eval) |
| maintainability-reviewer | Sonnet | green | 가독성(30줄/3중첩 기준), 순환 복잡도, 중복 코드(3회+ 추출), 명명 규칙 |
| a11y-reviewer | Sonnet | purple | ARIA 사용, 키보드 내비게이션(Tab/ESC/포커스 트랩), 스크린 리더 지원, 시맨틱 HTML |
| performance-reviewer | Sonnet | orange | 불필요한 리렌더링, 번들 크기(트리셰이킹, 동적 임포트), 메모리 누수, 지연 로딩 |
| type-safety-reviewer | Sonnet | cyan | any 사용 최소화, 타입 추론 활용, Generic 활용, Discriminated Union |

#### react-review (종합 리뷰 오케스트레이터)

| 항목 | 값 |
|---|---|
| 모델 | Sonnet |
| 도구 | Read, Glob, Grep, Task |

6개 전문 리뷰어를 병렬로 실행하여 React/TypeScript 코드를 종합 리뷰하는 오케스트레이터 에이전트입니다. 결과를 심각도별로 정렬하고 중복을 병합하여 실행 가능한 액션 아이템을 생성합니다.

**트리거 예시**

```
"src/ 폴더 React 리뷰해줘"
"Button.tsx 종합 리뷰해줘"
"이번 PR 변경사항 리뷰해줘"
```

---

#### checklist-summary (리뷰 체크리스트)

코드 리뷰 시 참고용 체크리스트 모음입니다. Architecture, Security, Maintainability, Accessibility, Performance, Type Safety 6개 영역의 체크리스트를 포함합니다.

---

### 워크플로우

**기본 흐름**

1. **product-spec-writer**로 기능 명세서 작성 → `specs/{feature}/plan.md`
2. **ui-designer**로 디자인 명세서 작성 → `specs/{feature}/design.md`
3. 개발자가 명세서를 보고 구현

**확장 흐름 (TDD 포함)**

1. **product-spec-writer** → 기획 명세서
2. **ux-researcher** → UX 분석 (선택)
3. **ui-designer** + **playwright-e2e-tester** + **code-analyst** → 디자인 명세서 + 테스트 시나리오/코드 + 구현 가이드 (병렬)
4. 개발자가 TDD 방식으로 구현
5. **test-consolidator** → TDD 후 테스트 통합/정리 (선택)

> `/feature` 커맨드를 사용하면 이 전체 파이프라인을 자동으로 실행할 수 있습니다.

**코드 리뷰 흐름**

> `/code-review` 커맨드를 사용하면 6개 리뷰 에이전트가 병렬로 실행됩니다.

**버그 수정 흐름**

단순 버그 (Minor):
```
[분석+수정 통합] → [테스트+검증 통합] → [사용자 최종 확인]
```

복합 버그 (Major/Critical):
```
[bug-analyzer] → [사용자 확인] → [bug-fixer] → [regression-tester] → [verification-agent] → [최종 확인]
```

산출물: `.claude/bug-reports/{BUG_ID}/` 하위에 analysis.md, fix-plan.md, test-scenarios.md, verification.md

> `/bug-fix` 커맨드를 사용하면 이 전체 파이프라인을 자동으로 실행할 수 있습니다.

### 공통 작성 원칙

- 모호한 표현 금지 — "적절하게", "필요시" 대신 구체적 조건/수치 명시
- 디자이너가 바로 화면을 그릴 수 있는 수준의 UI 상태 기술
- 개발자가 바로 구현할 수 있는 수준의 로직/조건 기술
- 불명확한 부분은 추측하지 않고 사용자에게 질문
- 코드 분석 시 실제 코드를 근거로 기술

### 새 에이전트 추가하기

`agents/{그룹}/` 디렉토리에 `.md` 파일을 추가하면 됩니다. 적절한 그룹 디렉토리(`planning/`, `testing/`, `bug-fix/`, `code-review/`)를 선택하세요. 파일은 YAML frontmatter와 시스템 프롬프트로 구성됩니다:

```markdown
---
name: agent-name
description: "에이전트 설명 및 트리거 조건"
tools: Tool1, Tool2
model: opus
color: green
---

에이전트 시스템 프롬프트 내용
```

추가 후 `~/.claude/agents/{그룹}/`에 복사하면 Claude Code에서 사용할 수 있습니다.

---

## Commands

Claude Code에서 슬래시 커맨드로 실행할 수 있는 워크플로우 모음입니다.

### 설치

```bash
cp commands/*.md ~/.claude/commands/
```

`~/.claude/commands/` 디렉토리에 `.md` 파일을 복사하면 Claude Code가 자동으로 인식합니다.

### 커맨드 목록

#### feature (기능 개발 파이프라인)

기능 개발 전체 파이프라인을 실행하는 커맨드입니다.

```
/feature <feature-name>
```

**예시:** `/feature license-management`

**워크플로우**

1. **Phase 1 - 기획**: product-spec-writer로 `specs/{feature}/plan.md` 작성
2. **Phase 1.5 - API 명세**: 목업 데이터 / API 명세서 제공 여부 확인
3. **Phase 2 - 검토**: 사용자 확인 (Blocking)
4. **Phase 3 - 설계/테스트/분석**: ui-designer + playwright-e2e-tester + code-analyst 병렬 실행
   - `specs/{feature}/design.md`
   - `specs/{feature}/test-scenarios.md`
   - `specs/{feature}/implementation-guide.md`
   - `tests/mocks/{feature}.mock.ts`
   - `tests/{feature}/*.spec.ts`
5. **Phase 4 - 구현**: implementation-guide.md를 참조하여 TDD 방식으로 구현

**산출물 구조**

```
specs/
└── {feature}/
    ├── plan.md                # Phase 1: 기획 명세서
    ├── api-spec.md            # Phase 1.5: API 명세서 (선택)
    ├── design.md              # Phase 3: 디자인 명세서
    ├── test-scenarios.md      # Phase 3: 테스트 시나리오
    └── implementation-guide.md # Phase 3: 구현 가이드

tests/
├── mocks/
│   └── {feature}.mock.ts     # Phase 3: 목업 데이터
└── {feature}/
    └── *.spec.ts              # Phase 3: 테스트 코드

src/
└── ...                        # Phase 4: 구현 코드
```

---

#### code-review (코드 종합 리뷰)

React/TypeScript 코드를 6개 관점에서 종합 리뷰하는 커맨드입니다.

```
/code-review [target]
```

**예시:**
- `/code-review` — src/ 폴더 전체 리뷰
- `/code-review src/components/Button.tsx` — 특정 파일 리뷰
- `/code-review src/features/auth` — 특정 폴더 리뷰

**워크플로우**

1. **Phase 1 - 대상 파악**: target이 지정되지 않으면 `src/` 기본값
2. **Phase 2 - 병렬 리뷰**: 6개 코드 리뷰 에이전트 동시 실행
3. **Phase 3 - 결과 통합**: 심각도별 정렬, 중복 병합, 액션 아이템 생성

**심각도 기준**

| 점수 | 레벨 | 의미 |
|-----|------|------|
| 91-100 | Critical | 반드시 수정 |
| 76-90 | High | 수정 권장 |
| 51-75 | Medium | 개선 고려 |
| 0-50 | Low | 참고 사항 |

80점 이상 이슈만 보고됩니다.

---

#### bug-fix (버그 수정 파이프라인)

버그 분석부터 수정, 테스트, 검증까지 전체 파이프라인을 실행하는 커맨드입니다.

```
/bug-fix
/bug-fix {버그 설명}
```

**예시:**
- `/bug-fix` — 대화형으로 버그 정보 수집
- `/bug-fix 로그인 버튼 클릭 시 에러 발생` — 버그 설명과 함께 실행

**워크플로우**

심각도에 따라 자동으로 워크플로우를 선택합니다:

| 심각도 | 워크플로우 |
|-------|-----------|
| Minor | 분석+수정 통합 → 테스트+검증 통합 → 사용자 확인 (빠른 경로) |
| Major/Critical | bug-analyzer → 사용자 확인 → bug-fixer → regression-tester → verification-agent → 최종 확인 |

1. **Phase 1 - 정보 수집**: 버그 설명, 심각도, 에러 로그, 재현 단계 확인
2. **Phase 2 - 분석**: bug-analyzer로 근본 원인 파악 → `analysis.md`
3. **Phase 3 - 수정**: bug-fixer로 최소 범위 코드 수정 → `fix-plan.md`
4. **Phase 4 - 테스트**: regression-tester로 회귀 방지 테스트 작성 → `test-scenarios.md`
5. **Phase 5 - 검증**: verification-agent로 테스트 실행 및 종합 검증 → `verification.md`

**산출물 구조**

```
.claude/bug-reports/
└── {BUG_ID}/
    ├── analysis.md        # Phase 2: 분석 리포트
    ├── fix-plan.md        # Phase 3: 수정 계획
    ├── test-scenarios.md  # Phase 4: 테스트 시나리오
    └── verification.md    # Phase 5: 검증 결과
```

---

## Skills

Claude Code의 스킬(skill)로 동작하는 커스텀 스킬 모음입니다.

### 설치

```bash
cp -r skills/* ~/.claude/skills/
```

`~/.claude/skills/` 디렉토리에 `SKILL.md` 파일이 포함된 폴더를 복사하면 Claude Code가 자동으로 인식합니다.

### 스킬 목록

#### granular-commit (세밀한 커밋 분리)

Git 변경사항을 hunk/줄 단위로 분석하여 세밀한 논리적 커밋으로 분리합니다. 한 파일 내에서도 변경 내용을 의미 단위로 나눠 개별 커밋을 생성합니다.

**워크플로우**: 변경사항 수집 → Hunk 분석 → 커밋 계획 제시 → 순차적 커밋 실행 → 완료 확인 → 푸시 여부 확인

**트리거 예시**

```
/granular-commit
"커밋 나눠줘"
"세세하게 커밋"
"변경사항 분리"
"커밋 쪼개줘"
```

---

#### retrospective (세션 회고)

개발 세션 후 회고를 수행하여 CLAUDE.md와 에이전트 프롬프트를 개선합니다. 세션에서 발생한 반복 수정, 패턴 불일치, 수동 교정 등을 분석하여 프로젝트 설정을 업그레이드합니다.

**워크플로우**: 세션 컨텍스트 분석 → 프로젝트 설정 수집 → 학습 항목 도출 → 변경 제안서 → 사용자 승인 후 적용

**트리거 예시**

```
/retrospective
"회고"
"세션 정리"
"CLAUDE.md 업데이트"
"프로젝트 규칙 개선"
```

---

#### sequence-diagram (코드 흐름 시퀀스 다이어그램)

특정 기능의 코드 흐름을 분석하여 Mermaid 시퀀스 다이어그램을 생성하고 PNG/SVG 이미지로 렌더링합니다. 진입점부터 호출 체인을 추적하여 파일 간 의존관계를 시각화합니다.

**워크플로우**: 분석 대상 확인 → 코드 탐색/추적 → 다이어그램 설계 → Mermaid 파일 생성 → 이미지 렌더링

**트리거 예시**

```
/sequence-diagram
"시퀀스 다이어그램 그려줘"
"코드 흐름 분석해줘"
"호출 흐름 시각화"
```

---

#### bug-fix-workflow (버그 수정 워크플로우)

버그 수정 과정을 체계화된 파이프라인으로 자동화합니다. 심각도에 따라 단순/복합 워크플로우를 자동 선택하고, 분석 → 수정 → 테스트 → 검증 단계를 순차적으로 실행합니다. `patterns/common-bugs.md`에 일반적인 버그 패턴 참조 문서를 포함합니다.

**워크플로우**: 버그 정보 수집 → 심각도 판단 → 파이프라인 실행 (bug-analyzer → bug-fixer → regression-tester → verification-agent) → 결과 보고

**트리거 예시**

```
/bug-fix
"버그 수정"
"버그 분석"
"bug fix"
```

---

#### session-analyzer (세션 로그 분석)

Claude Code 세션 로그(.jsonl)를 자동으로 분석하여 날짜별 활동 요약을 생성합니다. 기술 스택, 작업 유형, 사고 과정, 인사이트를 추출하고 **Claude Code 활용도를 100점 만점으로 평가**하여 마크다운 리포트를 제공합니다. `utils/analyze_sessions.py` 통합 분석 스크립트를 포함합니다.

**주요 기능**

- **활동 통계**: 세션 수, 메시지/도구 호출 수, 기술 스택, 도구 사용 빈도
- **Claude Code 활용 분석**: 사용한 모드(Plan/일반/Accept Edits), Skills, Commands, Sub Agents 추적
- **활용도 평가 (100점)**: 4개 카테고리 점수 + S/A/B/C/D 등급
  - 의도 전달력 (25점) — 수정 지시 비율, 초기 컨텍스트, 방향 일관성
  - 작업 효율성 (30점) — 재작업 비율, 도구 성공률, 작업 완결
  - 도구 적합성 (25점) — 전용 도구 사용, 위임 적절성, 변경 후 검증
  - 워크플로우 성숙도 (20점) — 반복 작업 자동화, 에러 적응력, 컨텍스트 관리
- **보안**: 프로젝트명, 파일 경로, 커밋 메시지 등 식별 가능 정보를 제외하여 공유 가능한 출력물 생성

**워크플로우**: 분석 범위 확인 → `analyze_sessions.py` 실행 → Skills/Commands/Sub Agent 설명 동적 수집 → 마크다운 요약 생성 (`~/.claude/summaries/daily/[YYYY-MM-DD].md`)

**트리거 예시**

```
/session-analyzer
"세션 분석"
"활동 로그"
"오늘 뭐했지"
"최근 7일 활동 분석"
```
