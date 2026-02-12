# React + TypeScript 리뷰 체크리스트 요약

React/TypeScript 코드 리뷰 시 참고용 체크리스트입니다.

---

## Architecture

- [ ] 단일 책임 원칙 준수 (컴포넌트당 하나의 역할)
- [ ] 컴포넌트 크기 300줄 이하
- [ ] 순환 의존성 없음
- [ ] 폴더 구조 일관성 (기능별 or 레이어별)
- [ ] 도메인 경계 명확 (features 간 직접 참조 금지)
- [ ] 공유 컴포넌트는 components/ 폴더에 위치

---

## Security

- [ ] `dangerouslySetInnerHTML` 사용 시 DOMPurify sanitize
- [ ] 민감정보 환경변수 관리 (하드코딩 금지)
- [ ] console.log에 토큰/비밀번호 출력 금지
- [ ] URL 파라미터에 민감정보 포함 금지
- [ ] 외부 URL href 사용 시 protocol 검증
- [ ] `eval()`, `new Function()` 사용 금지
- [ ] API 에러 메시지 그대로 노출 금지

---

## Maintainability

- [ ] 함수 30줄 이하
- [ ] 중첩 3단계 이하
- [ ] 순환 복잡도 5 이하
- [ ] 매직 넘버 상수화
- [ ] 3회 이상 반복 코드 추출
- [ ] 컴포넌트명 PascalCase
- [ ] 함수명 camelCase, 동사로 시작
- [ ] 불리언 변수 is/has/can 접두사
- [ ] 이벤트 핸들러 handle 접두사
- [ ] 커스텀 훅 use 접두사

---

## Accessibility (A11y)

- [ ] 시맨틱 HTML 사용 (header, nav, main, footer)
- [ ] 아이콘 버튼에 aria-label
- [ ] 동적 상태 aria-expanded, aria-selected 반영
- [ ] 모든 상호작용 요소 Tab 접근 가능
- [ ] 모달에 포커스 트랩 + ESC 닫기
- [ ] 커스텀 버튼 Enter/Space 키 처리
- [ ] 이미지에 alt 텍스트 (장식용은 alt="")
- [ ] 폼 요소에 label 연결
- [ ] 에러 메시지 aria-describedby 연결
- [ ] 동적 콘텐츠 aria-live 알림
- [ ] 제목 레벨 순서대로 (h1 -> h2 -> h3)

---

## Performance

- [ ] JSX 내 인라인 객체/함수 지양
- [ ] useCallback/useMemo 적절 사용
- [ ] 상태는 최소 범위에서 관리 (상태 캡슐화)
- [ ] 무관한 자식 리렌더링 방지 (memo 또는 상태 분리)
- [ ] 대용량 라이브러리 직접 임포트 (lodash/debounce)
- [ ] 무거운 컴포넌트 동적 임포트 (React.lazy)
- [ ] useEffect cleanup 함수 구현
- [ ] 타이머/인터벌 cleanup
- [ ] 이벤트 리스너 cleanup
- [ ] fetch AbortController 사용

---

## Type Safety

- [ ] `any` 사용 최소화
- [ ] 알 수 없는 데이터는 `unknown` + 타입 가드
- [ ] 이벤트 핸들러 타입 명시 (React.ChangeEvent 등)
- [ ] 빈 배열/객체 초기화 시 타입 명시
- [ ] 리터럴 값 불필요한 타입 명시 제거
- [ ] 재사용 가능한 훅/컴포넌트 Generic 활용
- [ ] 상태 타입 Discriminated Union 활용
- [ ] Props 확장 시 ComponentPropsWithoutRef 사용
- [ ] tsconfig strict: true 설정

---

## Quick Reference

### 심각도 기준
| 점수 | 레벨 | 의미 |
|-----|------|------|
| 91-100 | Critical | 반드시 수정 |
| 76-90 | High | 수정 권장 |
| 51-75 | Medium | 개선 고려 |
| 0-50 | Low | 참고 사항 |

### 에이전트 색상
| 에이전트 | 색상 | 트리거 예시 |
|---------|------|-----------|
| architecture-reviewer | blue | "구조 리뷰" |
| security-reviewer | red | "보안 검토" |
| maintainability-reviewer | green | "가독성 리뷰" |
| a11y-reviewer | purple | "접근성 검토" |
| performance-reviewer | orange | "성능 분석" |
| type-safety-reviewer | cyan | "타입 리뷰" |
| react-review | yellow | "종합 리뷰" |
