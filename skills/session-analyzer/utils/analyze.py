#!/usr/bin/env python3
"""
세션 데이터 분석 유틸리티

파싱된 세션 데이터를 받아서 기술 스택, 작업 유형, thinking 블록을 분석하고
JSON 형식으로 결과를 출력합니다.

사용법:
    python parse_jsonl.py --date 2026-02-11 | python analyze.py
"""

import json
import sys
import re
from collections import Counter
from typing import List, Dict, Any


# 키워드 정의
LANGUAGE_KEYWORDS = [
    'python', 'javascript', 'typescript', 'java', 'go', 'rust',
    'solidity', 'haskell', 'kotlin', 'swift', 'c++', 'c#',
    'ruby', 'php', 'scala', 'elixir', 'dart', 'cpp', 'csharp',
]

FRAMEWORK_KEYWORDS = [
    'react', 'vue', 'angular', 'svelte', 'solid',
    'next.js', 'nextjs', 'nuxt', 'gatsby', 'astro', 'qwik',
    'django', 'fastapi', 'flask', 'express', 'nest.js', 'nestjs',
    'spring', 'laravel', 'rails',
]

LIBRARY_KEYWORDS = [
    'tailwind', 'shadcn', 'radix-ui', 'radix', 'mui', 'material-ui',
    'axios', 'fetch', 'graphql', 'prisma', 'drizzle',
    'jest', 'vitest', 'pytest', 'mocha', 'chai',
]

TASK_TYPE_KEYWORDS = {
    '💻 Coding': [
        '구현', '작성', '개발', '만들', '생성', 'implement', 'create', 'build', 'develop', 'add'
    ],
    '🐛 Debugging': [
        '에러', '오류', '버그', '고치', '수정', 'error', 'bug', 'fix', 'debug', 'issue'
    ],
    '♻️ Refactoring': [
        '리팩토링', '개선', '최적화', 'refactor', 'optimize', 'improve', 'cleanup'
    ],
    '✅ Testing': [
        '테스트', '검증', '확인', 'test', 'verify', 'check', 'validate'
    ],
    '📚 Learning': [
        '공부', '학습', '이해', '알아보', 'learn', 'study', 'explore', 'understand'
    ],
    '📋 Planning': [
        '계획', '설계', '명세', 'plan', 'design', 'spec', 'documentation', '아키텍처'
    ],
    '⚙️ Configuration': [
        '설정', '환경', '설치', 'config', 'setup', 'install', 'configure'
    ],
    '🔍 Research': [
        '조사', '분석', '찾아', 'search', 'find', 'investigate', 'analyze'
    ],
}


def extract_keywords(text: str, keywords: List[str]) -> List[str]:
    """텍스트에서 키워드 추출 (대소문자 무시)"""
    if not text:
        return []

    text_lower = text.lower()
    found = []
    for keyword in keywords:
        if keyword.lower() in text_lower:
            found.append(keyword)
    return found


def analyze_tech_stack(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """기술 스택 분석"""
    languages = Counter()
    frameworks = Counter()
    libraries = Counter()
    file_extensions = Counter()

    for session in sessions:
        # 메시지와 thinking 블록에서 키워드 검색
        all_text = []

        for msg in session.get('messages', []):
            content = msg.get('content', '')
            if isinstance(content, str):
                all_text.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        all_text.append(item['text'])

        for thinking in session.get('thinking_blocks', []):
            all_text.append(thinking)

        combined_text = ' '.join(all_text)

        # 언어 추출
        for lang in extract_keywords(combined_text, LANGUAGE_KEYWORDS):
            languages[lang] += 1

        # 프레임워크 추출
        for fw in extract_keywords(combined_text, FRAMEWORK_KEYWORDS):
            frameworks[fw] += 1

        # 라이브러리 추출
        for lib in extract_keywords(combined_text, LIBRARY_KEYWORDS):
            libraries[lib] += 1

        # 파일 확장자 추출
        for tool_call in session.get('tool_calls', []):
            if tool_call.get('name') in ['Read', 'Write', 'Edit']:
                file_path = tool_call.get('input', {}).get('file_path', '')
                if file_path and '.' in file_path:
                    ext = file_path.rsplit('.', 1)[-1]
                    if len(ext) <= 10:  # 확장자가 너무 길지 않은 경우만
                        file_extensions[ext] += 1

    return {
        'languages': dict(languages.most_common(10)),
        'frameworks': dict(frameworks.most_common(10)),
        'libraries': dict(libraries.most_common(10)),
        'file_extensions': dict(file_extensions.most_common(10)),
    }


def classify_task_type(session: Dict[str, Any]) -> str:
    """세션의 작업 유형 분류"""
    messages = session.get('messages', [])

    # 첫 번째 사용자 메시지 찾기
    first_user_message = None
    for msg in messages:
        if msg.get('type') == 'user':
            first_user_message = msg.get('content', '')
            break

    if not first_user_message:
        return 'General'

    # 문자열로 변환
    if isinstance(first_user_message, list):
        text_parts = []
        for item in first_user_message:
            if isinstance(item, dict) and 'text' in item:
                text_parts.append(item['text'])
        first_user_message = ' '.join(text_parts)

    message_lower = first_user_message.lower()

    # 키워드 매칭
    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        if any(keyword.lower() in message_lower for keyword in keywords):
            return task_type

    return 'General'


def analyze_tool_usage(sessions: List[Dict[str, Any]]) -> Dict[str, int]:
    """도구 사용 빈도 분석"""
    tool_counter = Counter()

    for session in sessions:
        for tool_call in session.get('tool_calls', []):
            tool_name = tool_call.get('name')
            if tool_name:
                tool_counter[tool_name] += 1

    return dict(tool_counter.most_common(10))


def extract_thinking_insights(sessions: List[Dict[str, Any]], max_per_session: int = 5) -> List[str]:
    """Thinking 블록에서 인사이트 추출"""
    insights = []

    decision_keywords = ['결정', '선택', '판단', 'decide', 'choose', 'select', 'option']
    problem_keywords = ['문제', '해결', '방법', '접근', 'problem', 'solve', 'approach', 'solution']

    for session in sessions:
        session_insights = []

        for thinking in session.get('thinking_blocks', [])[:max_per_session]:
            # 문장 단위로 분리
            sentences = re.split(r'[.!?]\s+', thinking)

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                # 의사결정 관련 문장
                if any(kw in sentence.lower() for kw in decision_keywords):
                    session_insights.append(f"[결정] {sentence}")

                # 문제 해결 관련 문장
                elif any(kw in sentence.lower() for kw in problem_keywords):
                    session_insights.append(f"[해결] {sentence}")

        insights.extend(session_insights[:max_per_session])

    return insights[:20]  # 최대 20개


def analyze_workflow_patterns(sessions: List[Dict[str, Any]]) -> List[str]:
    """워크플로우 패턴 분석"""
    patterns = Counter()

    for session in sessions:
        tool_sequence = [tc.get('name') for tc in session.get('tool_calls', []) if tc.get('name')]

        # 3개씩 묶어서 패턴 추출
        for i in range(len(tool_sequence) - 2):
            pattern = ' → '.join(tool_sequence[i:i+3])
            patterns[pattern] += 1

    # 상위 5개 패턴
    return [f"{pattern} ({count}회)" for pattern, count in patterns.most_common(5)]


def analyze_sessions(data: Dict[str, Any]) -> Dict[str, Any]:
    """전체 세션 데이터 분석"""
    sessions = data.get('sessions', [])

    if not sessions:
        return {'error': '분석할 세션이 없습니다.'}

    # 기술 스택 분석
    tech_stack = analyze_tech_stack(sessions)

    # 작업 유형 분류
    task_types = Counter()
    for session in sessions:
        task_type = classify_task_type(session)
        task_types[task_type] += 1

    # 도구 사용 분석
    tool_usage = analyze_tool_usage(sessions)

    # Thinking 인사이트 추출
    thinking_insights = extract_thinking_insights(sessions)

    # 워크플로우 패턴 분석
    workflow_patterns = analyze_workflow_patterns(sessions)

    # 통계 계산
    total_messages = sum(len(s.get('messages', [])) for s in sessions)
    total_tool_calls = sum(len(s.get('tool_calls', [])) for s in sessions)
    avg_messages = total_messages / len(sessions) if sessions else 0
    avg_tool_calls = total_tool_calls / len(sessions) if sessions else 0

    # 세션 상세 정보
    session_details = []
    for session in sessions:
        task_type = classify_task_type(session)
        messages = session.get('messages', [])
        first_user_msg = next((m.get('content', '') for m in messages if m.get('type') == 'user'), '')

        # 첫 메시지 요약 (최대 100자)
        if isinstance(first_user_msg, list):
            text_parts = []
            for item in first_user_msg:
                if isinstance(item, dict) and 'text' in item:
                    text_parts.append(item['text'])
            first_user_msg = ' '.join(text_parts)

        summary = first_user_msg[:100] + '...' if len(first_user_msg) > 100 else first_user_msg

        session_details.append({
            'file_path': session.get('file_path'),
            'task_type': task_type,
            'summary': summary,
            'metadata': session.get('metadata', {}),
            'message_count': len(messages),
            'tool_call_count': len(session.get('tool_calls', [])),
        })

    return {
        'date_range': data.get('date_range', {}),
        'statistics': {
            'total_sessions': len(sessions),
            'total_messages': total_messages,
            'total_tool_calls': total_tool_calls,
            'avg_messages_per_session': round(avg_messages, 1),
            'avg_tool_calls_per_session': round(avg_tool_calls, 1),
        },
        'tech_stack': tech_stack,
        'task_types': dict(task_types.most_common()),
        'tool_usage': tool_usage,
        'thinking_insights': thinking_insights,
        'workflow_patterns': workflow_patterns,
        'session_details': session_details,
    }


def main():
    # stdin으로부터 JSON 데이터 읽기
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 실패: {e}", file=sys.stderr)
        sys.exit(1)

    # 분석 수행
    result = analyze_sessions(input_data)

    # 결과 출력
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
