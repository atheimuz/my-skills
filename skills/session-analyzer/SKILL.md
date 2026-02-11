---
name: session-analyzer
description: |
  클로드 코드 세션 로그를 자동으로 분석하여 날짜별 활동 요약을 생성합니다.
  기술 스택, 작업 유형, 사고 과정, 인사이트를 추출하여 마크다운 리포트를 제공합니다.

  트리거 키워드:
  - /session-analyzer
  - "세션 분석", "활동 로그", "사용 내역", "로그 분석"
  - "오늘 뭐했지", "이번 주 활동", "최근 작업"
---

# 클로드 코드 세션 로그 자동 분석 Skill

이 Skill은 `~/.claude/projects/` 디렉토리에 저장된 JSONL 세션 로그를 파싱하여 날짜별 활동을 분석하고, 마크다운 형식의 요약 리포트를 자동 생성합니다.

## 워크플로우

### 1단계: 분석 범위 확인

AskUserQuestion을 사용하여 사용자에게 분석할 기간을 확인합니다.

```yaml
questions:
  - question: "어떤 기간의 활동을 분석할까요?"
    header: "분석 기간"
    multiSelect: false
    options:
      - label: "오늘"
        description: "오늘(2026-02-11) 세션만 분석합니다."
      - label: "어제"
        description: "어제 세션만 분석합니다."
      - label: "최근 7일"
        description: "최근 일주일간의 모든 세션을 분석합니다."
      - label: "특정 날짜"
        description: "사용자가 지정한 날짜의 세션을 분석합니다."
```

사용자가 "특정 날짜"를 선택하면 다시 날짜를 입력받습니다(YYYY-MM-DD 형식).

### 2단계: 세션 파일 수집

날짜 범위에 해당하는 JSONL 파일을 수집합니다.

**Bash 명령어:**

```bash
# 모든 프로젝트의 JSONL 파일 찾기
find ~/.claude/projects -name "*.jsonl" -type f
```

각 파일의 타임스탬프를 확인하여 날짜 필터링:

```bash
# 파일의 첫 줄에서 타임스탬프 추출 (jq 사용)
head -n 1 [파일경로] | jq -r '.timestamp'
```

**날짜 변환 로직:**
- 타임스탬프(ISO 8601)를 날짜(YYYY-MM-DD)로 변환
- 선택한 날짜 범위와 비교하여 필터링

### 3단계: JSONL 파싱 및 데이터 추출

Read 도구로 각 JSONL 파일을 읽고 분석합니다.

**추출할 정보:**

1. **메타데이터**
   - timestamp: 세션 시작 시간
   - sessionId: 세션 ID
   - ⚠️ cwd(작업 디렉토리), gitBranch는 추출하지 않음 (프로젝트 식별 방지)

2. **메시지 내용**
   - type: "user" → 사용자 메시지
   - type: "assistant" → AI 응답
   - content: 메시지 본문

3. **도구 호출**
   - type: "tool_use"
   - name: 도구 이름 (Bash, Read, Write, Grep, Glob 등)
   - input: 도구 입력 파라미터

4. **Thinking 블록**
   - content.type: "thinking"
   - content.text: 사고 과정 텍스트

**파싱 전략:**
- JSONL 파일의 각 라인은 독립적인 JSON 객체
- Read 도구로 파일 읽기 (limit/offset 활용하여 메모리 효율 관리)
- Bash의 `jq` 명령어로 필요한 필드만 추출

```bash
# 예시: 모든 도구 호출 추출
jq -r 'select(.type == "tool_use") | .name' [파일경로]

# 예시: thinking 블록 추출
jq -r 'select(.content[]?.type == "thinking") | .content[].text' [파일경로]
```

### 4단계: 기술 스택 분석

메시지 내용과 도구 호출에서 기술 스택을 추출합니다.

**분석 대상:**
- 사용자 메시지 content
- AI 응답 content
- Thinking 블록 text
- Bash 명령어
- Read/Write/Edit의 file_path

**키워드 패턴:**

```yaml
언어:
  - python, javascript, typescript, java, go, rust
  - solidity, haskell, kotlin, swift, c++, c#
  - ruby, php, scala, elixir, dart

프레임워크:
  - react, vue, angular, svelte, solid
  - next.js, nuxt, gatsby, astro, qwik
  - django, fastapi, flask, express, nest.js
  - spring, laravel, rails

라이브러리:
  - tailwind, shadcn/ui, radix-ui, mui
  - axios, fetch, graphql, prisma, drizzle
  - jest, vitest, pytest, mocha

도구:
  - git, docker, kubernetes, terraform
  - npm, pnpm, yarn, pip, cargo
  - vite, webpack, rollup, esbuild
```

**파일 확장자 분석:**

Read/Write/Edit 도구 호출의 file_path에서 확장자 추출:

```bash
# 예시: 파일 확장자 추출
jq -r 'select(.name == "Read" or .name == "Write" or .name == "Edit") | .input.file_path' [파일경로] | \
  awk -F'.' '{print $NF}' | sort | uniq -c | sort -rn
```

**집계:**
- 각 언어/프레임워크 출현 횟수 카운트
- 상위 5개만 추출

### 5단계: 작업 유형 분류

각 세션의 첫 번째 사용자 메시지를 분석하여 작업 유형을 분류합니다.

**작업 유형 키워드:**

| 작업 유형 | 키워드 패턴 |
|---------|-----------|
| **💻 코딩** | 구현, 작성, 개발, 만들, 생성, implement, create, build, develop, add, 추가 |
| **🐛 디버깅** | 에러, 오류, 버그, 고치, error, bug, fix, debug, issue, 안됨, 안돼, 왜 |
| **♻️ 리팩토링** | 리팩토링, 리팩터, refactor, cleanup, 정리, 구조 변경 |
| **✏️ 수정** | 수정, 변경, 바꿔, 고쳐, modify, change, update, edit, 교체 |
| **✅ 테스트** | 테스트, 검증, test, verify, spec, 단위 테스트, e2e |
| **📋 설계/기획** | 계획, 설계, 명세, plan, design, spec, 아키텍처, architecture |
| **⚙️ 설정** | 설정, 환경, 설치, config, setup, install, configure, env |
| **🔍 탐색/분석** | 조사, 분석, 찾아, search, find, investigate, analyze, 확인, 파악 |
| **📚 학습** | 공부, 학습, 이해, 알아보, learn, study, 설명해, 뭐야, 어떻게 |
| **🎨 스타일링** | 스타일, CSS, 디자인, UI, UX, 색상, 레이아웃, 반응형, style |
| **📝 문서화** | 문서, README, 주석, comment, docs, documentation |
| **🚀 배포/CI** | 배포, deploy, CI, CD, pipeline, docker, 빌드 |
| **🔒 보안** | 보안, 인증, 권한, auth, security, token, 암호화 |
| **⚡ 성능 최적화** | 성능, 최적화, 느림, optimize, performance, 빠르게, 캐시, cache |
| **🗃️ 데이터/DB** | 데이터, DB, 마이그레이션, 쿼리, migration, schema, 모델 |

**분류 로직:**

- 하나의 세션이 **복수 카테고리**에 해당할 수 있음 (키워드 매칭 기반)
- 세션 내 모든 사용자 메시지를 대상으로 키워드 매칭
- 비율 = 해당 유형 세션 수 / 전체 세션 수 × 100
- 매칭되는 카테고리가 없으면 **🔧 기타**로 분류

```python
# 의사코드
all_user_messages = extract_all_user_messages(session)
combined_text = " ".join(all_user_messages).lower()
matched_types = []

for task_type, keywords in TASK_TYPE_KEYWORDS.items():
    if any(keyword in combined_text for keyword in keywords):
        matched_types.append(task_type)

if not matched_types:
    matched_types = ["🔧 기타"]
```

**워크플로우 패턴 추출:**

도구 호출 순서를 분석하여 작업 패턴 추출:

```
예시:
- Read → Write → Bash → Read → "코드 작성 후 실행 확인"
- Grep → Read → Edit → Bash → "검색 후 수정 및 테스트"
- Bash(git) → Write → Bash(git) → "Git 워크플로우"
```

### 6단계: 사고 과정 추출

Thinking 블록에서 주요 의사결정과 문제 해결 접근법을 추출합니다.

**추출 대상:**

1. **의사결정 관련 문장**
   - 키워드: "결정", "선택", "판단", "decide", "choose", "select", "option"
   - 해당 키워드를 포함한 문장 전체 추출

2. **문제 해결 접근법**
   - 키워드: "문제", "해결", "방법", "접근", "problem", "solve", "approach", "solution"
   - 문맥과 함께 추출

3. **추론 단계**
   - 번호 매겨진 단계: "1. ", "2. ", "- " 형태
   - 단계별로 나열된 사고 과정 추출

**추출 전략:**

```bash
# Thinking 블록에서 의사결정 문장 추출
jq -r 'select(.content[]?.type == "thinking") | .content[].text' [파일경로] | \
  grep -iE "(결정|선택|판단|decide|choose)" | head -5
```

**최대 개수:**
- 세션당 최대 5개의 주요 thinking 블록만 추출 (너무 많으면 요약이 비효율적)

### 7단계: 인사이트 생성

여러 세션을 종합하여 인사이트를 도출합니다.

**집계 항목:**

1. **도구 사용 통계**
   - 가장 많이 사용한 도구 Top 5
   - 평균 세션당 도구 호출 수

2. **작업 유형 분포**
   - 각 작업 유형 빈도
   - 가장 많이 한 작업 Top 3

3. **기술 스택 트렌드**
   - 사용 언어 빈도
   - 사용 프레임워크 빈도

4. **생산성 패턴**
   - 총 세션 수
   - 평균 메시지 수/세션
   - 평균 도구 호출 수/세션

5. **학습 하이라이트**
   - 문제 해결 사례 (Debugging 타입 세션)
   - 주요 의사결정 (Planning 타입 세션)
   - 새로운 기술 탐색 (Learning 타입 세션)

### 7-1단계: Skills/Commands/Sub Agent 설명 동적 수집

출력 템플릿의 Skills/Commands/Sub Agents 테이블에 설명을 채우기 위해, 각 항목의 설명을 **동적으로** 수집한다. 하드코딩된 매핑 테이블은 사용하지 않는다.

**Skills 설명 수집:**

```
1. 세션 로그에서 사용된 Skill 이름 목록 추출 (Skill 도구 호출의 `skill` 파라미터)
2. 각 스킬에 대해 ~/.claude/skills/[스킬명]/SKILL.md 파일을 Read로 읽기
3. frontmatter의 description 필드에서 첫 번째 줄(한 줄 요약)을 추출
4. 파일이 없거나 description이 없으면 "커스텀 스킬"로 표기
```

**Commands 설명 수집:**

```
1. 세션 로그에서 사용된 슬래시 커맨드 목록 추출 (사용자 메시지에서 /로 시작하는 빌트인 커맨드)
2. 분석 시점의 시스템 프롬프트에 로드된 skill 목록의 description 참조
3. 빌트인 커맨드(/compact, /clear 등)는 분석 시 AI가 자체 지식으로 한 줄 설명 생성
4. 알 수 없는 커맨드는 커맨드명 그대로 표시
```

**Sub Agent 설명 수집:**

```
1. 세션 로그에서 Task 도구 호출의 subagent_type과 description 파라미터 추출
2. description 파라미터가 있으면 그것을 한 줄 설명으로 사용
3. description이 없으면 분석 시 AI가 자체 지식으로 해당 agent 유형의 한 줄 설명 생성
```

> **핵심 원칙**: 하드코딩된 매핑 테이블 없이, 세션 로그의 메타데이터 + 스킬 파일의 description + AI 자체 지식을 조합하여 동적으로 설명을 채운다.

### 8단계: 마크다운 요약 생성

Write 도구로 요약 파일을 생성합니다.

**파일 경로:**
- 일일 요약: `~/.claude/summaries/daily/[YYYY-MM-DD].md`
- 주간 요약: `~/.claude/summaries/weekly/[YYYY]-W[WW].md`

**마크다운 템플릿:**

```markdown
# [YYYY-MM-DD] 클로드 코드 활동 요약

> 자동 생성: [생성 시간]

## 📊 전체 통계

- 총 세션 수: [N]개
- 평균 메시지 수: [N]개/세션
- 평균 도구 호출: [N]회/세션

## 🛠 주요 기술 스택

### 언어
- [언어1] ([N]회)
- [언어2] ([N]회)
- ...

### 프레임워크/라이브러리
- [프레임워크1] ([N]회)
- [프레임워크2] ([N]회)
- ...

## 🤖 클로드 코드 활용 방식

### 사용한 모드
- [Plan Mode / 일반 모드 / Accept Edits 모드]

### 활용한 Skills
| Skill | 설명 | 호출 횟수 |
|-------|------|----------|
| [Skill명] | [스킬이 하는 일에 대한 한 줄 설명] | [N]회 |

### 활용한 Commands
| Command | 설명 | 사용 횟수 |
|---------|------|----------|
| [Command명] | [커맨드 기능에 대한 한 줄 설명] | [N]회 |

### 활용한 Sub Agents
| Agent 유형 | 설명 | 호출 횟수 |
|-----------|------|----------|
| [Agent명] | [에이전트 역할에 대한 한 줄 설명] | [N]회 |

### 작업 위임 스타일
- [한 줄 자연어 지시 → 자동 분석 → 수정]
- [높은 수준의 목표만 제시하고 Claude가 분석/실행]

## 🎯 Claude Code 활용도 평가

### 작업 복잡도: [경량/중량/중량급]

### 종합 점수: [N]/100 ([등급])

| 항목 | 점수 | 평가 |
|------|------|------|
| 의도 전달력 | [N]/25 | [평가] |
| 작업 효율성 | [N]/30 | [평가] |
| 도구 적합성 | [N]/25 | [평가] |
| 워크플로우 성숙도 | [N]/20 | [평가] |

### 잘한 점
- [긍정적 피드백]

### 개선 포인트
- [구체적 개선 제안]

## 💬 프롬프트 패턴

### 효과적이었던 프롬프트
- [사용자 프롬프트의 특성: 간결/구체적/개방형 등]
- [기준과 행동을 함께 제시하는 패턴 등]

### 대화 흐름
- [단발 요청 vs 연속 대화]
- [후속 지시 패턴]

## 🔧 도구 활용 통계

| 도구 | 사용 횟수 | 주요 용도 |
|------|----------|----------|
| [도구1] | [N]회 | [용도] |
| [도구2] | [N]회 | [용도] |
| ... | ... | ... |

## 📝 작업 유형

| 유형 | 세션 수 | 비율 |
|------|---------|------|
| 💻 코딩 | [N]개 | [N]% |
| ♻️ 리팩토링 | [N]개 | [N]% |
| 🐛 디버깅 | [N]개 | [N]% |
| ✏️ 수정 | [N]개 | [N]% |
| ... | ... | ... |

> 하나의 세션이 여러 유형에 해당할 수 있어 비율 합계가 100%를 초과할 수 있습니다.

## 🗂 세션 상세

### 세션 [N]: [작업 유형] - [Claude Code 활용 방식]
- **작업 유형**: [작업유형]
- **활용 방식**: [어떻게 Claude Code를 사용했는지]
  - [예: "Explore 에이전트로 코드베이스 분석 후 자동 수정"]
- **수정 규모**: [N]개 파일, [N]건 변경
- ⚠️ 프로젝트 종류나 구체적 기능명은 기록하지 않음

### 세션 [N]: [작업 유형] - [Claude Code 활용 방식]
[...]

## 💡 학습 인사이트

- [일반적인 개발 인사이트, 특정 코드/파일 언급 없이]
- ...

## 📈 워크플로우 패턴

[반복되는 도구 사용 패턴]

- [패턴 1]: Read → Write → Bash
- [패턴 2]: Grep → Edit → Bash
- ...

---

*이 요약은 `/session-analyzer` Skill로 자동 생성되었습니다.*
```

## 보안 가이드라인 (필수)

출력물은 다른 유저들과 공유될 수 있으므로, 아래 정보는 **절대 포함하지 않는다**:

| 금지 항목 | 예시 |
|----------|------|
| 프로젝트명/종류 | "웹 앱 프로젝트", "블로그 프로젝트", "이커머스" 등 일반화된 표현도 금지 |
| 파일 경로 | `src/components/Foo.tsx`, `app/api/bar/route.ts` |
| 커밋 메시지 | `feat: 로그인 기능 추가` |
| 세션 ID | `76539087-f46e-4e72-...` |
| 작업 디렉토리 | `/Users/username/workspace/...` |
| Git 브랜치명 | `main`, `feature/xxx` |
| 사용자명/경로 | `/Users/atheimuz/...` |
| API 키/토큰 | 인증 관련 문자열 |
| 파일 타입 섹션 | `.tsx`, `.ts` 등 확장자 나열 금지 |

**대체 방법:**
- 프로젝트명/종류 → **기록하지 않음** (어떤 프로젝트인지 식별 가능한 정보 일절 제외)
- 파일 경로 → 작업 유형으로 대체 ("코드 수정", "설정 변경")
- 커밋 메시지 → 작업 유형 ("설정 변경 커밋", "코드 수정 커밋")
- 수정 내용 → "N개 파일 수정", "N건 변경"
- 구체적 기능명 → 추상적 작업 설명 ("컴포넌트 수정", "API 작업" 등 프로젝트를 유추할 수 없는 표현만 허용)

## 클로드 코드 활용 분석 중점 항목

출력물의 핵심은 **사용자가 클로드 코드를 어떻게 활용했는지**이다:

1. **모드 활용**: Plan Mode, Accept Edits, 일반 모드 중 어떤 것을 사용했는가
2. **에이전트 활용**: Explore, Plan 에이전트를 어떻게 위임했는가
3. **Skills 활용**: /granular-commit, /commit 등 어떤 스킬을 사용했는가
4. **프롬프트 스타일**: 지시가 간결한가, 구체적인가, 개방형인가
5. **대화 흐름**: 한번에 끝내는가, 후속 지시로 다듬는가
6. **작업 위임 수준**: 세부 지시 vs 높은 수준 목표만 제시
7. **도구 활용 효율**: 어떤 도구를 얼마나 사용했고 어떤 용도였는가

## 🎯 활용도 평가 점수 계산 로직

### 핵심 철학

"기능을 많이 쓰면 좋다"가 아니라 **"작업에 적합한 방식으로 사용했는가"**를 평가한다. 간단한 작업을 간단하게 끝내는 것도 높은 점수이며, 복잡한 작업에서 적절한 도구를 활용하는 것도 높은 점수다. **"해당 없음"인 항목은 자동 만점** 처리하여, 작업 성격에 따라 불필요한 기능을 사용하지 않았다고 벌점을 받지 않는다.

### Step 1: 작업 복잡도 자동 분류

점수 계산 전에 세션의 작업 복잡도를 먼저 판단한다. "도구 적합성"과 "워크플로우 성숙도" 카테고리에서 복잡도별 기대치가 달라진다.

```yaml
경량 (Light):
  조건: 수정 파일 < 3 AND 도구 호출 < 15 AND 메시지 < 10
  특징: 단순 수정, 질문, 짧은 탐색
  기대 행동: 빠르게 끝내기. Sub Agent/Skills 불필요할 수 있음

중량 (Medium):
  조건: 수정 파일 3-10 OR 도구 호출 15-50 OR 메시지 10-30
  특징: 기능 구현, 리팩토링, 중간 규모 디버깅
  기대 행동: 적절한 탐색 도구 활용, 필요시 Sub Agent

중량급 (Heavy):
  조건: 수정 파일 > 10 OR 도구 호출 > 50 OR 메시지 > 30
  특징: 대규모 작업, 아키텍처 변경, 복잡한 디버깅
  기대 행동: Sub Agent 위임, 계획 수립, 컨텍스트 관리 적극 활용
```

### Step 2: 4개 카테고리 평가 (100점)

#### 1. 의도 전달력 (25점)

> 어떤 작업이든 명확한 지시는 중요하다. 작업 성격과 무관하게 보편적으로 적용.

**탐지 방법**:

| 시그널 | 탐지 방법 | 분석 대상 |
|--------|----------|----------|
| 수정 지시 비율 | 사용자 메시지에서 "다시", "아니", "그게 아니라", "원래대로", "취소", "되돌려" 등 correction 키워드 탐지 | user 메시지 content |
| 초기 컨텍스트 | 첫 사용자 메시지의 길이 및 구체성 (에러 메시지, 파일명, 기대 동작 포함 여부) | 첫 user 메시지 |
| 방향 일관성 | 후속 메시지가 같은 맥락 심화인지, 완전히 다른 요청으로 전환인지 | user 메시지 시퀀스 |

**점수 계산**:

```yaml
수정 지시 비율 (15점):
  correction_ratio = correction_keywords 포함 user 메시지 수 / 전체 user 메시지 수
  - 0~10%: 15점 (명확한 지시, 수정 거의 없음)
  - 10~25%: 10점 (보통)
  - 25%+: 5점 (빈번한 수정 → 초기 지시 개선 필요)

초기 컨텍스트 제공 (5점):
  first_msg_length = 첫 user 메시지 글자 수
  has_specifics = 에러 메시지/파일 참조/구체적 요구사항 포함 여부
  - 50자+ AND has_specifics: 5점
  - 30~50자 OR has_specifics: 3점
  - 30자 미만 AND !has_specifics: 1점

방향 일관성 (5점):
  topic_switches = 완전히 다른 주제로 전환된 횟수 (연속 메시지 간 키워드 겹침률로 판단)
  - 전환 0-1회: 5점
  - 전환 2-3회: 3점
  - 전환 4회+: 1점
```

#### 2. 작업 효율성 (30점)

> 목표 대비 얼마나 낭비 없이 작업을 수행했는가. 간단한 작업을 간단하게 끝내는 것도 높은 점수.

**탐지 방법**:

| 시그널 | 탐지 방법 | 분석 대상 |
|--------|----------|----------|
| 재작업 비율 | 같은 파일을 Edit/Write로 3회 이상 수정한 파일 수 / 전체 수정 파일 수 | Edit/Write 도구의 file_path |
| 도구 성공률 | tool_result에서 에러가 아닌 비율 | tool_result 내용 |
| 작업 완결 시그널 | 세션 후반부에 "완료", "done", "커밋", "확인", "잘 됩니다" 등 완료 키워드 | 마지막 3개 user 메시지 |

**점수 계산**:

```yaml
재작업 비율 (10점):
  rework_files = Edit/Write 3회+ 수정된 고유 파일 수
  total_files = Edit/Write로 수정된 고유 파일 수
  rework_ratio = rework_files / total_files (total_files=0이면 ratio=0)
  - 0~10%: 10점 (한번에 잘 수정)
  - 10~30%: 7점 (일부 재작업)
  - 30%+: 4점 (잦은 재작업 → 사전 분석 부족)
  - 수정 파일 없음 (탐색/질문 세션): 10점 (해당 없음 → 만점)

도구 성공률 (10점):
  success_rate = 에러 미포함 tool_result 수 / 전체 도구 호출 수
  - 90%+: 10점
  - 70~90%: 7점
  - 70% 미만: 4점

작업 완결 (10점):
  has_completion_signal = 세션 후반 30% 메시지에서 완료 키워드 존재 여부
  - 완료 시그널 있음: 10점
  - 없음 (진행중/탐색 세션): 7점 (경량 벌점만)
```

#### 3. 도구 적합성 (25점)

> **이 카테고리는 작업 복잡도에 따라 기대치가 달라진다.** 핵심 변경점.

**탐지 방법**:

| 시그널 | 탐지 방법 | 분석 대상 |
|--------|----------|----------|
| 전용 도구 우선 사용 | Bash 명령어에서 grep/cat/find/head/tail/sed/awk 사용 횟수 | Bash 도구의 command 입력 |
| 규모 대비 위임 적절성 | 작업 복잡도 vs Sub Agent/Skills 사용 여부 | Task/Skill 도구 호출 + 복잡도 |
| 변경 후 검증 | Edit/Write 후 Bash로 테스트/빌드/린트 실행 여부 | Edit/Write → Bash 시퀀스 |

**점수 계산**:

```yaml
전용 도구 우선 사용 (10점):
  bash_antipatterns = Bash에서 grep/cat/find/head/tail/sed/awk 사용 횟수
  - 0회: 10점 (전용 도구를 적절히 사용)
  - 1~3회: 7점 (가끔 Bash 사용)
  - 4회+: 3점 (전용 도구 활용 부족)

규모 대비 위임 적절성 (10점):  ← 복잡도별 분기
  IF 경량(Light):
    - Sub Agent 미사용: 10점 (적절 - 불필요한 위임 안 함)
    - Sub Agent 사용: 7점 (과잉이지만 감점 최소화)
  IF 중량(Medium):
    - Sub Agent 또는 적절한 도구 조합 사용: 10점
    - 직접 수동 처리: 7점
  IF 중량급(Heavy):
    - Explore/Plan 에이전트 활용: 10점
    - 에이전트 미사용, 수동 처리: 5점 (위임이 효율적이었을 상황)
    - 병렬 에이전트 활용: +2점 보너스 (최대 10점 캡)

변경 후 검증 (5점):  ← 수정 규모별 분기
  edit_count = Edit/Write 호출 수
  has_verification = Edit/Write 후 Bash(test/build/lint/run) 호출 존재
  IF edit_count >= 5:
    - 검증 있음: 5점
    - 검증 없음: 2점
  IF edit_count < 5:
    - 5점 (소규모 수정은 검증 선택적 → 자동 만점)
  IF edit_count == 0:
    - 5점 (해당 없음)
```

#### 4. 워크플로우 성숙도 (20점)

> 반복 작업의 자동화, 에러 대응, 세션 관리의 성숙도를 평가.

**탐지 방법**:

| 시그널 | 탐지 방법 | 분석 대상 |
|--------|----------|----------|
| 반복 작업 자동화 | Git 커밋 작업 시 /commit 등 스킬 사용 여부 | Skill 도구 호출 + Bash git 명령 |
| 에러 적응력 | 도구 실패 후 같은 도구 동일 입력 재시도 vs 다른 접근 | tool_use → tool_result(error) → 다음 tool_use |
| 컨텍스트 관리 | 긴 세션에서 /compact 또는 세션 분리 활용 | 복잡도 + /compact 사용 여부 |

**점수 계산**:

```yaml
반복 작업 자동화 (7점):
  has_git_commit = Bash에서 "git commit" 실행 여부
  has_commit_skill = /commit 또는 /granular-commit 사용 여부
  has_other_skills = 기타 스킬 사용 여부
  IF has_git_commit AND !has_commit_skill:
    - 4점 (수동 커밋 → 스킬 활용 가능)
  IF has_commit_skill OR has_other_skills:
    - 7점 (자동화 활용)
  IF !has_git_commit AND !has_commit_skill:
    - 7점 (해당 없음 → 만점. 커밋이 필요 없는 세션)

에러 적응력 (7점):
  same_error_retries = 같은 도구+유사 입력으로 연속 실패한 횟수 (3회+ 카운트)
  - 연속 실패 0건: 7점 (적응적 대응 또는 에러 없음)
  - 연속 실패 1건: 5점
  - 연속 실패 2건+: 3점 (같은 실수 반복)

컨텍스트 관리 (6점):  ← 복잡도별 분기
  IF 경량(Light):
    - 6점 (짧은 세션은 관리 불필요 → 자동 만점)
  IF 중량(Medium):
    - 6점 (보통 크기도 자동 만점)
  IF 중량급(Heavy):
    - /compact 사용 OR 적절한 세션 분리: 6점
    - 미사용: 3점 (긴 세션에서 컨텍스트 관리 권장)
```

### 평가 등급

| 점수 범위 | 등급 | 설명 |
|----------|------|------|
| 90-100 | S | Claude Code 마스터 |
| 75-89 | A | 숙련된 사용자 |
| 60-74 | B | 중급 사용자 |
| 40-59 | C | 초급 사용자 |
| 0-39 | D | 입문자 |

### 피드백 생성 로직

**잘한 점 (긍정적 피드백):**
- 각 카테고리에서 80%+ 점수인 항목의 구체적 행동 언급
- 예: "초기 메시지에서 에러 로그와 기대 동작을 함께 제공하여 한번에 정확한 수정이 이루어졌습니다"
- 예: "소규모 수정 작업을 Sub Agent 없이 빠르게 직접 처리했습니다"

**개선 포인트 (구체적 제안):**
- 각 카테고리에서 50% 미만인 항목의 개선 제안
- 단, **"해당 없음"으로 만점인 항목은 제외**
- 예: "같은 파일을 5회 이상 수정했습니다. 수정 전 파일을 먼저 Read로 확인하면 재작업을 줄일 수 있습니다"
- 예: "Bash에서 grep을 4회 사용했습니다. Grep 전용 도구를 사용하면 더 정확하고 빠릅니다"

## 분석 설정

```yaml
필터링 기준:
  최소_메시지_수: 3        # 너무 짧은 세션 제외
  최소_도구_호출_수: 1     # 도구를 한 번도 안 쓴 세션 제외

추출 제한:
  thinking_블록_최대: 5    # 세션당 최대 5개
  명령어_기록_최대: 20     # 세션당 최대 20개 Bash 명령어
  세션_샘플링_최대: 100    # 대용량 시 최근 100개만

키워드_대소문자_무시: true
```

## 에러 핸들링

1. **세션이 없는 경우**
   - 메시지: "선택한 기간에 세션이 없습니다."
   - 사용자에게 다른 날짜 선택 제안

2. **JSONL 파싱 오류**
   - 손상된 파일 스킵
   - 정상 파일만 분석
   - 최종 요약에 "일부 파일 파싱 실패" 표시

3. **jq 없는 경우**
   - Bash로 수동 파싱 (느리지만 작동)
   - 또는 Python 스크립트 사용 (utils/parse_jsonl.py)

4. **빈 데이터**
   - 키워드 매칭 실패 시 "기타" 카테고리로 분류
   - 최소한의 기본 통계는 제공

## 성능 최적화

**대용량 로그 처리:**

1. **샘플링**
   - 100개 이상 세션 시 최근 100개만 분석
   - 또는 시간순으로 균등 샘플링

2. **병렬 처리**
   - Bash의 xargs로 파일별 병렬 파싱
   - 각 세션 독립적으로 분석 후 집계

3. **캐싱**
   - 이미 분석한 세션은 재분석 안 함
   - 메타데이터 캐시 파일 생성 고려

## 사용 예시

```
사용자: /session-analyzer
Claude: [날짜 선택 질문 표시]
사용자: 오늘
Claude: [분석 진행...]
Claude: ✅ 분석 완료! ~/.claude/summaries/daily/2026-02-11.md 생성됨

# 생성된 파일 확인
$ cat ~/.claude/summaries/daily/2026-02-11.md
```

자연어로도 실행 가능:

```
사용자: 오늘 뭐했는지 요약해줘
Claude: [자동으로 /session-analyzer 실행]

사용자: 최근 7일 활동 분석해줘
Claude: [최근 7일 선택하여 실행]

사용자: 어제 작업 내역 보여줘
Claude: [어제 선택하여 실행]
```

## 향후 확장

- [ ] 주간/월간 요약 생성
- [ ] 시각화 (차트/그래프)
- [ ] 키워드 검색 기능
- [ ] 웹 대시보드
- [ ] AI 기반 심층 인사이트
