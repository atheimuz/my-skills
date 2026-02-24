# Common Bug Patterns

자주 발생하는 버그 패턴과 수정 방법 참조 문서.

## JavaScript/TypeScript 버그

### 1. Null/Undefined Reference

**증상**:
```
TypeError: Cannot read property 'x' of undefined
TypeError: Cannot read properties of null (reading 'x')
```

**원인**:
- 데이터 로딩 전 접근
- API 응답 구조 변경
- 옵셔널 프로퍼티 미처리

**수정 패턴**:
```typescript
// Optional Chaining
const value = data?.nested?.property;

// Nullish Coalescing
const value = data?.property ?? defaultValue;

// Early Return Guard
if (!data?.nested) {
  return null;
}
```

---

### 2. Async/Await 에러

**증상**:
```
Unhandled Promise rejection
Error: [object Object]
```

**원인**:
- try-catch 누락
- Promise 체인 에러 미처리
- async 함수 내 throw 미처리

**수정 패턴**:
```typescript
// try-catch 추가
async function fetchData() {
  try {
    const response = await api.get('/data');
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError) {
      // API 에러 처리
    }
    throw error;
  }
}

// Promise.all 에러 처리
const results = await Promise.allSettled([promise1, promise2]);
const errors = results.filter(r => r.status === 'rejected');
```

---

### 3. Race Condition

**증상**:
- 간헐적 버그
- 언마운트 후 상태 업데이트 경고
- 데이터 불일치

**원인**:
- 컴포넌트 언마운트 후 상태 업데이트
- 중복 API 요청
- 순서 보장 안됨

**수정 패턴**:
```typescript
// AbortController
useEffect(() => {
  const controller = new AbortController();

  fetchData({ signal: controller.signal })
    .then(setData)
    .catch((error) => {
      if (error.name !== 'AbortError') throw error;
    });

  return () => controller.abort();
}, []);

// isMounted flag
useEffect(() => {
  let isMounted = true;

  fetchData().then((data) => {
    if (isMounted) setData(data);
  });

  return () => { isMounted = false; };
}, []);
```

---

### 4. State Sync 문제

**증상**:
- 업데이트 후 이전 데이터 표시
- 캐시 불일치
- 낙관적 업데이트 실패

**원인**:
- 캐시 무효화 누락
- 상태 업데이트 순서 문제
- 서버/클라이언트 상태 불일치

**수정 패턴**:
```typescript
// TanStack Query 캐시 무효화
const mutation = useMutation({
  mutationFn: updateData,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['data'] });
  },
});

// 낙관적 업데이트
const mutation = useMutation({
  mutationFn: updateItem,
  onMutate: async (newItem) => {
    await queryClient.cancelQueries({ queryKey: ['items'] });
    const previous = queryClient.getQueryData(['items']);
    queryClient.setQueryData(['items'], (old) => [...old, newItem]);
    return { previous };
  },
  onError: (err, newItem, context) => {
    queryClient.setQueryData(['items'], context.previous);
  },
});
```

---

## React 버그

### 5. 무한 루프 렌더링

**증상**:
- 브라우저 멈춤
- "Maximum update depth exceeded" 에러

**원인**:
- useEffect 의존성 배열 누락
- 렌더링 중 상태 업데이트
- 객체/배열 의존성 매번 새로 생성

**수정 패턴**:
```typescript
// 의존성 배열 명시
useEffect(() => {
  // effect
}, [dependency]); // 빈 배열이면 마운트 시만

// useMemo로 참조 안정화
const options = useMemo(() => ({
  key: value
}), [value]);

// useCallback으로 함수 안정화
const handleClick = useCallback(() => {
  // handler
}, [dependency]);
```

---

### 6. 이벤트 핸들러 문제

**증상**:
- 클릭이 동작 안 함
- this가 undefined
- 이벤트 전파 문제

**원인**:
- 이벤트 핸들러 바인딩 누락
- 이벤트 전파 미처리
- 폼 기본 동작 미방지

**수정 패턴**:
```typescript
// 폼 제출
const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  // submit logic
};

// 이벤트 전파 중단
const handleClick = (e: React.MouseEvent) => {
  e.stopPropagation();
  // click logic
};

// 조건부 클릭
<button
  onClick={() => isEnabled && handleClick()}
  disabled={!isEnabled}
>
```

---

### 7. 조건부 렌더링 에러

**증상**:
- 컴포넌트 깜빡임
- 조건에 따라 빈 화면

**원인**:
- falsy 값 렌더링 (0, '')
- 로딩 상태 미처리
- 에러 경계 누락

**수정 패턴**:
```typescript
// 0 렌더링 방지
{items.length > 0 && <List items={items} />}

// 로딩/에러/데이터 처리
if (isLoading) return <Spinner />;
if (error) return <ErrorMessage error={error} />;
if (!data) return null;
return <Content data={data} />;
```

---

## CSS/스타일 버그

### 8. 레이아웃 깨짐

**증상**:
- 요소 겹침
- 예상치 못한 여백
- 반응형 깨짐

**수정 패턴**:
```css
/* Flexbox 정렬 */
.container {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

/* 오버플로우 처리 */
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 안전한 최소/최대 크기 */
.responsive {
  min-width: 0; /* flex item 오버플로우 방지 */
  max-width: 100%;
}
```

---

## API/네트워크 버그

### 9. API 에러 처리

**증상**:
- 에러 메시지 미표시
- 로딩 상태 멈춤
- 재시도 불가

**수정 패턴**:
```typescript
// Axios interceptor
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 인증 에러 처리
    }
    return Promise.reject(error);
  }
);

// React Query 에러 처리
const { data, error, isError } = useQuery({
  queryKey: ['data'],
  queryFn: fetchData,
  retry: 3,
  retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
});
```

---

## 디버깅 팁

### 콘솔 로깅
```typescript
console.log('[DEBUG]', { state, props, context });
console.trace('[TRACE] Function called');
```

### React DevTools
- Components 탭에서 상태 확인
- Profiler로 렌더링 분석

### Network 탭
- API 요청/응답 확인
- 타이밍 분석

## macOS 네이티브 앱 버그

### 10. 첫 클릭 무반응 (NSPanel/NSWindow 활성화)

**증상**:
- 버튼/드래그가 첫 번째 시도에 동작하지 않음
- 한 번 클릭 후 두 번째 시도부터 동작함
- hover 이벤트는 정상이나 tap/drag는 안 됨

**원인**:
- `NSPanel`에 `.nonactivatingPanel` styleMask 설정 → `NSApp.isActive == false`
- `NSApp`이 비활성 상태에서는 `window.makeKey()`가 no-op
- SwiftUI의 Button 액션 및 `.draggable` 제스처는 key window 또는 active app을 전제

**선행 조건 체인**:
```
NSApp.isActive == true         ← 이게 false면 아래 전부 무의미
    → window.makeKey() 가능
        → SwiftUI 이벤트 라우팅 정상
            → Button/drag 동작
```

**수정 패턴**:
```swift
// NSHostingView 서브클래스에서
override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

override func mouseDown(with event: NSEvent) {
    if !NSApp.isActive {
        NSApp.activate(ignoringOtherApps: true)
    }
    window?.makeKey()
    super.mouseDown(with: event)
}

// NSPanel 서브클래스
class InteractivePanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}

// 패널 생성 시: .nonactivatingPanel 제거
panel = InteractivePanel(
    contentRect: ...,
    styleMask: [.titled, .closable, .fullSizeContentView],  // .nonactivatingPanel 없음
    ...
)
panel.acceptsMouseMovedEvents = true  // mouseDragged 이벤트 수신 보장
```

**진단 체크리스트**:
- [ ] `NSApp.isActive` 확인 (다른 앱 사용 중 클릭 시 false)
- [ ] `styleMask`에 `.nonactivatingPanel` 여부 확인
- [ ] `canBecomeKey` override 여부 확인
- [ ] `acceptsMouseMovedEvents` 설정 여부 (드래그 미동작 시)

---

### 11. 드래그 첫 시도 미동작 (SwiftUI .draggable)

**증상**:
- `.draggable` modifier 사용 시 첫 드래그가 실행 안 됨
- 클릭 후 드래그 시도 시 동작

**원인**:
- `mouseDragged` 이벤트가 비활성 앱 윈도우에 전달 안 됨
- `acceptsMouseMovedEvents = false`인 경우 마우스 이동 추적 안 됨

**수정**: `panel.acceptsMouseMovedEvents = true` + NSApp 활성화 (패턴 10 참조)
