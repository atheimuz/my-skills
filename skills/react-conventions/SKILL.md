---
name: react-conventions
description: >
    React/TypeScript 프로젝트의 컴포넌트 작성, 폴더 구조, 네이밍, 상태 관리 컨벤션.
    컴포넌트 생성, 수정, 리팩토링 시 이 규칙을 자동으로 적용한다.
    "컴포넌트 만들어", "페이지 추가", "리팩토링", "컴포넌트 생성",
    "component", "react" 등으로 트리거.
---

# React Conventions

React/TypeScript 프로젝트에서 따라야 할 코딩 컨벤션.

<instruction>
이 스킬이 트리거되면 아래 모든 규칙을 코드 생성/수정 시 자동으로 적용하세요.
사용자가 명시적으로 다른 방식을 요청하지 않는 한, 이 규칙을 기본으로 따릅니다.
프로젝트에 CLAUDE.md가 있으면 프로젝트 규칙을 우선 적용하되, 충돌하지 않는 범위에서 이 컨벤션도 함께 적용합니다.
</instruction>

---

## 1. 컴포넌트 작성 규칙

### 1-1. 상수는 컴포넌트 밖에 선언

변하지 않는 값은 컴포넌트 함수 외부 상단에 정의한다.

```tsx
// ✅
const MAX_ITEMS = 5;
const NAV_ITEMS = [
  { href: "/", label: "홈" },
  { href: "/blog", label: "블로그" },
] as const;

export default function Navigation() {
  return (
    <nav>
      {NAV_ITEMS.map((item) => (
        <a key={item.href} href={item.href}>{item.label}</a>
      ))}
    </nav>
  );
}

// ❌ 컴포넌트 내부에 상수 선언
export default function Navigation() {
  const MAX_ITEMS = 5;
  const NAV_ITEMS = [{ href: "/", label: "홈" }];
  // ...
}
```

### 1-2. className 최우선, 조건부 클래스는 cn()

style prop 대신 Tailwind className을 사용한다. 조건부 클래스는 `cn()` 유틸리티(clsx + tailwind-merge)를 사용한다.

프로젝트에 `cn()` 유틸이 없으면 생성한다:

```ts
// lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

```tsx
// ✅
<button className={cn("px-4 py-2 rounded", isActive && "bg-blue-500 text-white")}>
  클릭
</button>

// ❌ style prop 사용
<button style={{ padding: "8px 16px", backgroundColor: isActive ? "blue" : "transparent" }}>
  클릭
</button>
```

### 1-3. map key는 유니크한 값 사용

배열을 map으로 렌더링할 때 index 대신 고유한 식별자를 key로 사용한다. index 사용은 권장하지 않는다.

```tsx
// ✅ 고유 id 사용
{posts.map((post) => (
  <PostCard key={post.id} post={post} />
))}

// ✅ 고유한 값 조합
{categories.map((category) => (
  <Tab key={category.code} label={category.label} />
))}

// ❌ index 사용
{posts.map((post, index) => (
  <PostCard key={index} post={post} />
))}
```

### 1-4. 리스트 아이템은 별도 컴포넌트로 분리

map으로 렌더링하는 아이템은 독립된 컴포넌트로 추출한다.

```tsx
// ✅ 아이템 컴포넌트 분리
function PostList({ posts }: PostListProps) {
  return (
    <ul>
      {posts.map((post) => (
        <PostListItem key={post.id} post={post} />
      ))}
    </ul>
  );
}

// ❌ 인라인으로 아이템 렌더링
function PostList({ posts }: PostListProps) {
  return (
    <ul>
      {posts.map((post) => (
        <li key={post.id}>
          <h3>{post.title}</h3>
          <p>{post.description}</p>
          <span>{post.date}</span>
        </li>
      ))}
    </ul>
  );
}
```

### 1-5. 공통 컴포넌트 우선 재사용

기존 공통 컴포넌트를 먼저 찾아 사용한다. 없으면 재사용 가능성을 판단해 `components/common/`에 생성한다.

```
판단 기준:
- 2곳 이상에서 사용될 가능성이 있으면 → components/common/에 생성
- 특정 feature에서만 사용되면 → components/<Feature>/ 내부에 생성
```

### 1-6. 데이터 페칭 시 로딩/에러 상태 필수

데이터를 가져오는 모든 컴포넌트는 로딩 UI와 에러 UI를 구현한다.

```tsx
// ✅ 로딩 + 에러 + 데이터 상태 모두 처리
function UserProfile({ userId }: UserProfileProps) {
  const { data, isLoading, isError } = useUser(userId);

  if (isLoading) return <UserProfileSkeleton />;
  if (isError) return <ErrorMessage message="프로필을 불러올 수 없습니다" />;

  return <div>{data.name}</div>;
}

// ❌ 로딩/에러 무시
function UserProfile({ userId }: UserProfileProps) {
  const { data } = useUser(userId);
  return <div>{data?.name}</div>;
}
```

### 1-7. 리렌더링 최소화를 위한 컴포넌트 분리

독립적인 상태를 가진 영역은 부모에서 관리하지 않고, 각 자식 컴포넌트 내부에서 자체 관리한다.

```tsx
// ✅ 각 컴포넌트가 자체 상태 관리
function Dashboard() {
  return (
    <>
      <UserTimeline />
      <NotificationList />
    </>
  );
}

// UserTimeline 내부에서 자체 상태 관리
function UserTimeline() {
  const [items, setItems] = useState([]);
  // ...
}

// NotificationList 내부에서 자체 상태 관리
function NotificationList() {
  const [notifications, setNotifications] = useState([]);
  // ...
}

// ❌ 부모에서 모든 상태를 관리하고 props로 전달
function Dashboard() {
  const [items, setItems] = useState([]);
  const [notifications, setNotifications] = useState([]);

  return (
    <>
      <UserTimeline items={items} setItems={setItems} />
      <NotificationList notifications={notifications} setNotifications={setNotifications} />
    </>
  );
}
```

---

## 2. 네이밍 규칙

### 2-1. 변수명은 읽을 수 있는 단어, 축약형 금지

축약형을 사용하지 않는다. 누구나 알 수 있는 명확한 단어를 사용한다.

```tsx
// ✅
categories.map((category) => <CategoryCard key={category.id} category={category} />)
notifications.map((notification) => <NotificationItem key={notification.id} notification={notification} />)
const buttonElement = document.querySelector("button");
const isAuthenticated = checkAuth();

// ❌ 축약형
categories.map((cat) => <CategoryCard key={cat.id} category={cat} />)
notifications.map((noti) => <NotificationItem key={noti.id} notification={noti} />)
const btnEl = document.querySelector("button");
const isAuth = checkAuth();
```

### 2-2. 이벤트 핸들러 네이밍

컴포넌트 내부 핸들러는 `handle<Action>`, props로 받는 콜백은 `on<Action>`.

```tsx
// ✅
interface ButtonProps {
  onClick: () => void;       // props 콜백: on<Action>
  onToggle: () => void;
}

function SearchForm() {
  const handleSubmit = () => { /* ... */ };  // 내부 핸들러: handle<Action>
  const handleInputChange = () => { /* ... */ };

  return <form onSubmit={handleSubmit}>...</form>;
}

// ❌
function SearchForm() {
  const submit = () => { /* ... */ };
  const inputChanged = () => { /* ... */ };
}
```

### 2-3. 파일/폴더 네이밍

| 대상 | 규칙 | 예시 |
|------|------|------|
| 컴포넌트 파일/폴더 | PascalCase | `PostCard/PostCard.tsx` |
| 유틸리티 파일 | camelCase | `dateUtils.ts`, `formatNumber.ts` |
| 커스텀 훅 | camelCase (use 접두사) | `useFetchPosts.ts` |
| 상수 파일 | camelCase | `constants.ts` |
| 타입 파일 | camelCase | `api.ts`, `user.ts` |

---

## 3. 폴더 구조 규칙

### 3-1. 컴포넌트는 폴더 단위로 생성 (플랫 파일 금지)

```
# ✅ 올바른 구조
components/common/Button/
  ├── index.ts              # re-export
  ├── Button.tsx            # 메인 컴포넌트
  ├── Button.test.tsx       # 단위 테스트 (필요시)
  └── ButtonSkeleton.tsx    # 스켈레톤 (필요시)

# ❌ 금지
components/common/Button.tsx
```

index.ts 예시:
```ts
export { default } from "./Button";
// 또는
export { Button } from "./Button";
```

### 3-2. feature별 폴더 구분

```
src/components/
├── common/                  # 공통 재사용 컴포넌트
│   ├── Button/
│   ├── Input/
│   ├── Modal/
│   └── ErrorMessage/
└── features/                # 기능별 그룹
    ├── Auth/
    │   ├── LoginForm/
    │   └── SignupForm/
    ├── Blog/
    │   ├── PostCard/
    │   ├── PostList/
    │   └── PostBody/
    └── Admin/
        ├── TrendList/
        └── CategoryManager/
```

### 3-3. 전체 프로젝트 구조

```
src/
├── components/
│   ├── common/              # 공통 컴포넌트
│   └── features/            # 기능별 컴포넌트
├── hooks/                   # 커스텀 훅
├── lib/                     # 비즈니스 로직, 유틸리티
├── types/                   # 공유 타입 (2개 이상 모듈에서 사용)
└── app/                     # Next.js App Router (또는 pages/)

tests/                       # 통합/E2E 테스트만
├── e2e/
└── integration/
```

---

## 4. 타입 관리

### 4-1. props 타입은 컴포넌트 파일 상단에 선언

별도 `.types.ts` 파일로 분리하지 않는다.

```tsx
// ✅ Button.tsx 상단에 interface 선언
interface ButtonProps {
  variant: "primary" | "secondary";
  size: "sm" | "md" | "lg";
  onClick: () => void;
}

export function Button({ variant, size, onClick }: ButtonProps) {
  // ...
}
```

### 4-2. 복잡한 타입만 예외적으로 분리

타입이 50줄 이상으로 길어서 컴포넌트 가독성을 해치는 경우에만 `Component.types.ts`로 분리한다.

### 4-3. 공유 타입은 types/ 폴더

2개 이상 모듈에서 사용하는 타입은 `src/types/`에 둔다.

```
src/types/
├── api.ts        # API 응답 타입
├── user.ts       # 유저 관련 공통 타입
└── common.ts     # 범용 유틸리티 타입
```

---

## 5. 테스트 파일 위치

| 테스트 종류 | 위치 | 기준 |
|-------------|------|------|
| 단위 테스트 | 컴포넌트 폴더 내부 | 1:1 대응 (`Button/Button.test.tsx`) |
| 통합/E2E 테스트 | `tests/` 폴더 | 여러 컴포넌트에 걸치는 테스트 |

---

## 6. 추가 패턴

### 6-1. import 정렬 순서

```tsx
// 1. 외부 패키지
import { useState, useCallback } from "react";
import Link from "next/link";

// 2. 내부 모듈 (@/ alias)
import { cn } from "@/lib/utils";
import { useFetchPosts } from "@/hooks/useFetchPosts";

// 3. 컴포넌트
import { PostListItem } from "components/Post/PostListItem";
```

### 6-2. Server/Client 경계

- 서버 컴포넌트를 기본으로 사용한다
- `"use client"`는 인터랙션이 필요한 최소 범위의 컴포넌트에만 선언한다
- 데이터 페칭은 서버 컴포넌트에서, 인터랙션은 클라이언트 컴포넌트에서 담당한다

```tsx
// ✅ 서버 컴포넌트에서 데이터 페칭 → 클라이언트 컴포넌트에 props 전달
// PostPage.tsx (서버)
export default async function PostPage({ params }: Props) {
  const post = await getPost(params.id);
  return <PostBody post={post} />;  // PostBody만 "use client"
}

// ❌ 클라이언트 컴포넌트에서 불필요하게 데이터 페칭
"use client";
export default function PostPage({ params }: Props) {
  const { data: post } = useFetchPost(params.id);
  // ...
}
```

### 6-3. 커스텀 훅 네이밍

`use<동사><명사>` 형식을 따른다.

```tsx
// ✅
useFetchPosts()
useToggleTheme()
useSubmitForm()
useFilterCategories()

// ❌
usePosts()        // 동사 없음
useData()         // 너무 모호
```
