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
   - cwd: 작업 디렉토리
   - gitBranch: Git 브랜치 (있는 경우)
   - sessionId: 세션 ID

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
| **💻 Coding** | 구현, 작성, 개발, 만들, 생성, implement, create, build, develop, add |
| **🐛 Debugging** | 에러, 오류, 버그, 고치, 수정, error, bug, fix, debug, issue |
| **♻️ Refactoring** | 리팩토링, 개선, 최적화, refactor, optimize, improve, cleanup |
| **✅ Testing** | 테스트, 검증, 확인, test, verify, check, validate |
| **📚 Learning** | 공부, 학습, 이해, 알아보, learn, study, explore, understand |
| **📋 Planning** | 계획, 설계, 명세, plan, design, spec, documentation, 아키텍처 |
| **⚙️ Configuration** | 설정, 환경, 설치, config, setup, install, configure |
| **🔍 Research** | 조사, 분석, 찾아, search, find, investigate, analyze |

**분류 로직:**

```python
# 의사코드
first_user_message = extract_first_user_message(session)
message_lower = first_user_message.lower()

for task_type, keywords in TASK_TYPE_KEYWORDS.items():
    if any(keyword in message_lower for keyword in keywords):
        return task_type

return "General"  # 기본값
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
- 작업 시간대: [HH:MM] ~ [HH:MM]

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

### 활용한 기능
- [Explore 에이전트, Plan 에이전트, Skills 등]
- [AskUserQuestion을 통한 대화형 확인]

### 작업 위임 스타일
- [한 줄 자연어 지시 → 자동 분석 → 수정]
- [높은 수준의 목표만 제시하고 Claude가 분석/실행]

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

- [이모지] [작업유형1] ([N]회)
- [이모지] [작업유형2] ([N]회)
- ...

## 🗂 세션 상세

### 세션 [N]: [작업 내용 요약 - 구체적 파일명/경로 없이]
- **시작 시간**: [HH:MM]
- **작업 유형**: [작업유형]
- **활용 방식**: [어떻게 Claude Code를 사용했는지]
  - [예: "Explore 에이전트로 코드베이스 분석 후 자동 수정"]
- **주요 작업**: [파일명 없이 일반화된 설명]
  - [예: "UI 컴포넌트 간 레이아웃 불일치 15건 자동 탐지 및 수정"]
- **수정 규모**: [N]개 파일, [N]건 변경

### 세션 [N]: [작업 내용 요약]
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
| 파일 경로 | `src/components/Foo.tsx`, `app/api/bar/route.ts` |
| 커밋 메시지 | `feat: 로그인 기능 추가` |
| 세션 ID | `76539087-f46e-4e72-...` |
| 작업 디렉토리 | `/Users/username/workspace/...` |
| Git 브랜치명 | `main`, `feature/xxx` |
| 사용자명/경로 | `/Users/atheimuz/...` |
| API 키/토큰 | 인증 관련 문자열 |
| 파일 타입 섹션 | `.tsx`, `.ts` 등 확장자 나열 금지 |

**대체 방법:**
- 프로젝트명 → 일반화 ("웹 앱 프로젝트", "블로그 프로젝트")
- 파일 경로 → 기능 설명 ("스켈레톤 UI 컴포넌트", "로딩 화면")
- 커밋 메시지 → 작업 유형 ("설정 변경 커밋", "UI 수정 커밋")
- 수정 내용 → "N개 파일 수정", "N건 변경"

## 클로드 코드 활용 분석 중점 항목

출력물의 핵심은 **사용자가 클로드 코드를 어떻게 활용했는지**이다:

1. **모드 활용**: Plan Mode, Accept Edits, 일반 모드 중 어떤 것을 사용했는가
2. **에이전트 활용**: Explore, Plan 에이전트를 어떻게 위임했는가
3. **Skills 활용**: /granular-commit, /commit 등 어떤 스킬을 사용했는가
4. **프롬프트 스타일**: 지시가 간결한가, 구체적인가, 개방형인가
5. **대화 흐름**: 한번에 끝내는가, 후속 지시로 다듬는가
6. **작업 위임 수준**: 세부 지시 vs 높은 수준 목표만 제시
7. **도구 활용 효율**: 어떤 도구를 얼마나 사용했고 어떤 용도였는가

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
