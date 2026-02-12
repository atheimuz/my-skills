#!/usr/bin/env python3
"""
Session Analyzer - JSONL 세션 로그 통합 분석 스크립트

파싱, 기술 스택 분석, 작업 유형 분류, 워크플로우 패턴, 활용도 점수를
모두 포함한 JSON을 stdout으로 출력합니다.

사용법:
    python3 analyze_sessions.py --date 2026-02-11
    python3 analyze_sessions.py --date-range 2026-02-01 2026-02-11
"""

import json
import argparse
import sys
import re
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict, Any, Tuple


# ============================================================================
# Section 1: Constants & Keywords
# ============================================================================

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
    'Coding': [
        '구현', '작성', '개발', '만들', '생성', 'implement', 'create',
        'build', 'develop', 'add', '추가',
    ],
    'Debugging': [
        '에러', '오류', '버그', '고치', 'error', 'bug', 'fix', 'debug',
        'issue', '안됨', '안돼', '왜',
    ],
    'Refactoring': [
        '리팩토링', '리팩터', 'refactor', 'cleanup', '정리', '구조 변경',
    ],
    'Modification': [
        '수정', '변경', '바꿔', '고쳐', 'modify', 'change', 'update',
        'edit', '교체',
    ],
    'Testing': [
        '테스트', '검증', 'test', 'verify', 'spec', '단위 테스트', 'e2e',
    ],
    'Planning': [
        '계획', '설계', '명세', 'plan', 'design', 'spec', '아키텍처',
        'architecture',
    ],
    'Configuration': [
        '설정', '환경', '설치', 'config', 'setup', 'install', 'configure',
        'env',
    ],
    'Research': [
        '조사', '분석', '찾아', 'search', 'find', 'investigate', 'analyze',
        '확인', '파악',
    ],
    'Learning': [
        '공부', '학습', '이해', '알아보', 'learn', 'study', '설명해',
        '뭐야', '어떻게',
    ],
    'Styling': [
        '스타일', 'css', '디자인', 'ui', 'ux', '색상', '레이아웃',
        '반응형', 'style',
    ],
    'Documentation': [
        '문서', 'readme', '주석', 'comment', 'docs', 'documentation',
    ],
    'Deployment': [
        '배포', 'deploy', 'ci', 'cd', 'pipeline', 'docker', '빌드',
    ],
    'Security': [
        '보안', '인증', '권한', 'auth', 'security', 'token', '암호화',
    ],
    'Performance': [
        '성능', '최적화', '느림', 'optimize', 'performance', '빠르게',
        '캐시', 'cache',
    ],
    'Data': [
        '데이터', 'db', '마이그레이션', '쿼리', 'migration', 'schema',
        '모델',
    ],
}

CORRECTION_KEYWORDS = [
    '다시', '아니', '그게 아니라', '원래대로', '취소', '되돌려',
    '아닌데', '아니야', '틀렸', '잘못', '이전 거', '롤백',
    '아까', '아니요', '그거 말고', '그게 아니고', '다른 거',
    '수정해', '고쳐', '바꿔', '변경해',
]

COMPLETION_KEYWORDS = [
    '완료', 'done', '커밋', '확인', '잘 됩니다', '감사',
    '좋아', '됐어', '끝', 'commit', 'push', '고마워',
    'ㅇㅋ', 'ok', '잘 돼', '잘 동작',
]

SPECIFICS_PATTERNS = [
    r'error', r'에러', r'오류',
    r'\.tsx?', r'\.jsx?', r'\.py', r'\.md', r'\.json',
    r'src/', r'app/', r'pages/', r'components/',
    r'```',
    r'http', r'localhost',
    r'\d{3,}',
]

BASH_ANTIPATTERNS = [
    r'(?<!\w)grep\s',
    r'(?<!\w)cat\s+[^<]',
    r'(?<!\w)find\s+\.',
    r'(?<!\w)head\s+-',
    r'(?<!\w)tail\s+-',
    r'(?<!\w)sed\s+',
    r'(?<!\w)awk\s+',
]

BASH_ANTIPATTERN_EXCEPTIONS = [
    r'git\s+grep',
    r'npm\s+run',
    r'cat\s*<<',
    r'grep.*node_modules',
]


# ============================================================================
# Section 2: Core Parsing
# ============================================================================

def parse_timestamp(timestamp_str: str) -> datetime:
    """ISO 8601 타임스탬프를 datetime으로 변환"""
    try:
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
        ]:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except Exception:
        return datetime.now()


def find_session_files(projects_dir: Path, start_date: datetime, end_date: datetime) -> List[Path]:
    """날짜 범위에 해당하는 메인 세션 JSONL 파일 찾기 (subagents 제외)"""
    session_files = []

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            if 'subagents' in str(jsonl_file):
                continue

            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for raw_line in f:
                        raw_line = raw_line.strip()
                        if not raw_line:
                            continue
                        first_obj = json.loads(raw_line)
                        timestamp = first_obj.get('timestamp')
                        if not timestamp:
                            continue
                        session_date = parse_timestamp(timestamp)
                        if start_date <= session_date <= end_date:
                            session_files.append(jsonl_file)
                        break
            except Exception:
                continue

    return sorted(session_files)


def parse_session_enhanced(file_path: Path) -> Dict[str, Any]:
    """세션 파일을 분석에 필요한 모든 데이터로 파싱"""
    data = {
        'user_messages': [],
        'tool_uses': [],
        'tool_results': [],
        'thinking_blocks': [],
        'all_text': [],
        'total_messages': 0,
        'total_user_messages': 0,
        'total_assistant_messages': 0,
        'edit_write_files': Counter(),
        'bash_commands': [],
        'has_task_calls': [],
        'has_skill_calls': [],
        'has_compact': False,
        'has_git_commit_bash': False,
        'tool_sequence': [],
        'commands_used': [],
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get('type')
                message = obj.get('message', {})

                if msg_type == 'user':
                    data['total_messages'] += 1
                    content = message.get('content', '') if isinstance(message, dict) else ''

                    if isinstance(content, str):
                        if content.strip():
                            data['user_messages'].append(content.strip())
                            data['all_text'].append(content.strip())
                            data['total_user_messages'] += 1
                            if '/compact' in content:
                                data['has_compact'] = True
                            # 슬래시 커맨드 탐지
                            cmd_match = re.findall(r'(?:^|[\s])(\/\w[\w-]*)', content)
                            for cmd in cmd_match:
                                if cmd not in data['commands_used']:
                                    data['commands_used'].append(cmd)
                    elif isinstance(content, list):
                        has_text = False
                        for item in content:
                            if not isinstance(item, dict):
                                continue
                            item_type = item.get('type', '')

                            if item_type == 'text':
                                text = item.get('text', '').strip()
                                if text:
                                    data['user_messages'].append(text)
                                    data['all_text'].append(text)
                                    has_text = True
                                    if '/compact' in text:
                                        data['has_compact'] = True
                                    cmd_match = re.findall(r'(?:^|[\s])(\/\w[\w-]*)', text)
                                    for cmd in cmd_match:
                                        if cmd not in data['commands_used']:
                                            data['commands_used'].append(cmd)

                            elif item_type == 'tool_result':
                                is_error = item.get('is_error', False)
                                data['tool_results'].append({
                                    'is_error': is_error is True,
                                    'content': str(item.get('content', ''))[:200],
                                    'tool_use_id': item.get('tool_use_id', ''),
                                })
                        if has_text:
                            data['total_user_messages'] += 1

                elif msg_type == 'assistant':
                    data['total_messages'] += 1
                    data['total_assistant_messages'] += 1
                    content = message.get('content', [])

                    if isinstance(content, list):
                        for item in content:
                            if not isinstance(item, dict):
                                continue
                            item_type = item.get('type', '')

                            if item_type == 'thinking':
                                thinking_text = item.get('thinking', '') or item.get('text', '')
                                if thinking_text:
                                    data['thinking_blocks'].append(thinking_text)

                            elif item_type == 'text':
                                text = item.get('text', '').strip()
                                if text:
                                    data['all_text'].append(text)

                            elif item_type == 'tool_use':
                                tool_name = item.get('name', '')
                                tool_input = item.get('input', {})
                                data['tool_uses'].append({
                                    'name': tool_name,
                                    'input': tool_input,
                                    'id': item.get('id', ''),
                                })
                                data['tool_sequence'].append(tool_name)

                                if tool_name in ('Edit', 'Write'):
                                    fp = tool_input.get('file_path', '')
                                    if fp:
                                        data['edit_write_files'][fp] += 1

                                if tool_name == 'Bash':
                                    cmd = tool_input.get('command', '')
                                    if cmd:
                                        data['bash_commands'].append(cmd)
                                        if 'git commit' in cmd:
                                            data['has_git_commit_bash'] = True

                                if tool_name == 'Task':
                                    data['has_task_calls'].append({
                                        'subagent_type': tool_input.get('subagent_type', ''),
                                        'description': tool_input.get('description', ''),
                                    })

                                if tool_name == 'Skill':
                                    data['has_skill_calls'].append({
                                        'skill': tool_input.get('skill', ''),
                                    })

    except Exception as e:
        print(f"파싱 실패: {file_path} - {e}", file=sys.stderr)

    return data


# ============================================================================
# Section 3: Analysis Functions
# ============================================================================

def extract_keywords(text: str, keywords: List[str]) -> List[str]:
    """텍스트에서 키워드 추출 (대소문자 무시)"""
    if not text:
        return []
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def analyze_tech_stack(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """기술 스택 분석"""
    languages = Counter()
    frameworks = Counter()
    libraries = Counter()

    for session in sessions:
        combined_text = ' '.join(session.get('all_text', []))

        for lang in extract_keywords(combined_text, LANGUAGE_KEYWORDS):
            languages[lang] += 1
        for fw in extract_keywords(combined_text, FRAMEWORK_KEYWORDS):
            frameworks[fw] += 1
        for lib in extract_keywords(combined_text, LIBRARY_KEYWORDS):
            libraries[lib] += 1

    return {
        'languages': dict(languages.most_common(10)),
        'frameworks': dict(frameworks.most_common(10)),
        'libraries': dict(libraries.most_common(10)),
    }


def classify_task_types(session: Dict[str, Any]) -> List[str]:
    """세션의 작업 유형 분류 (복수 카테고리 반환)"""
    combined_text = ' '.join(session.get('user_messages', [])).lower()
    if not combined_text:
        return ['General']

    matched = []
    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        if any(kw.lower() in combined_text for kw in keywords):
            matched.append(task_type)

    return matched if matched else ['General']


def analyze_tool_usage(sessions: List[Dict[str, Any]]) -> Dict[str, int]:
    """도구 사용 빈도 분석"""
    counter = Counter()
    for session in sessions:
        for tu in session.get('tool_uses', []):
            name = tu.get('name')
            if name:
                counter[name] += 1
    return dict(counter.most_common(15))


def extract_thinking_insights(sessions: List[Dict[str, Any]], max_per_session: int = 5) -> List[str]:
    """Thinking 블록에서 인사이트 추출"""
    decision_kw = ['결정', '선택', '판단', 'decide', 'choose', 'select', 'option']
    problem_kw = ['문제', '해결', '방법', '접근', 'problem', 'solve', 'approach', 'solution']
    insights = []

    for session in sessions:
        session_insights = []
        for thinking in session.get('thinking_blocks', [])[:max_per_session]:
            sentences = re.split(r'[.!?]\s+', thinking)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence or len(sentence) < 10:
                    continue
                if any(kw in sentence.lower() for kw in decision_kw):
                    session_insights.append(f"[결정] {sentence[:150]}")
                elif any(kw in sentence.lower() for kw in problem_kw):
                    session_insights.append(f"[해결] {sentence[:150]}")
        insights.extend(session_insights[:max_per_session])

    return insights[:20]


def analyze_workflow_patterns(sessions: List[Dict[str, Any]]) -> List[str]:
    """워크플로우 패턴 분석 (3-gram)"""
    patterns = Counter()
    for session in sessions:
        seq = session.get('tool_sequence', [])
        for i in range(len(seq) - 2):
            pattern = ' → '.join(seq[i:i + 3])
            patterns[pattern] += 1

    return [f"{p} ({c}회)" for p, c in patterns.most_common(5)]


def compute_statistics(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """전체 통계 계산"""
    total_msgs = sum(s.get('total_messages', 0) for s in sessions)
    total_tools = sum(len(s.get('tool_uses', [])) for s in sessions)
    n = len(sessions) or 1
    return {
        'total_sessions': len(sessions),
        'total_messages': total_msgs,
        'total_tool_calls': total_tools,
        'avg_messages_per_session': round(total_msgs / n, 1),
        'avg_tool_calls_per_session': round(total_tools / n, 1),
    }


# ============================================================================
# Section 4: Score Calculation
# ============================================================================

def classify_complexity(sessions: List[Dict]) -> str:
    """전체 세션의 작업 복잡도 분류"""
    n = len(sessions) or 1
    avg_files = sum(len(s['edit_write_files']) for s in sessions) / n
    avg_tools = sum(len(s['tool_uses']) for s in sessions) / n
    avg_msgs = sum(s['total_user_messages'] for s in sessions) / n

    if avg_files > 10 or avg_tools > 50 or avg_msgs > 30:
        return '중량급'
    elif avg_files >= 3 or avg_tools >= 15 or avg_msgs >= 10:
        return '중량'
    else:
        return '경량'


def calc_intent_score(sessions: List[Dict]) -> Tuple[int, Dict]:
    """의도 전달력 (25점)"""
    details = {}

    total_user_msgs = 0
    correction_msgs = 0
    for s in sessions:
        for msg in s['user_messages']:
            total_user_msgs += 1
            if any(kw in msg.lower() for kw in CORRECTION_KEYWORDS):
                correction_msgs += 1

    ratio = correction_msgs / total_user_msgs if total_user_msgs > 0 else 0
    if ratio <= 0.10:
        correction_score = 15
    elif ratio <= 0.25:
        correction_score = 10
    else:
        correction_score = 5

    details['correction_ratio'] = round(ratio * 100, 1)
    details['correction_score'] = correction_score

    context_scores = []
    for s in sessions:
        if s['user_messages']:
            first_msg = s['user_messages'][0]
            length = len(first_msg)
            has_specifics = any(re.search(p, first_msg, re.IGNORECASE) for p in SPECIFICS_PATTERNS)
            if length >= 50 and has_specifics:
                context_scores.append(5)
            elif length >= 30 or has_specifics:
                context_scores.append(3)
            else:
                context_scores.append(1)

    context_score = round(sum(context_scores) / len(context_scores)) if context_scores else 3
    details['context_score'] = context_score

    topic_switches = 0
    for s in sessions:
        msgs = s['user_messages']
        for i in range(1, len(msgs)):
            prev_words = set(msgs[i - 1].lower().split())
            curr_words = set(msgs[i].lower().split())
            if prev_words and curr_words:
                overlap = len(prev_words & curr_words) / max(len(prev_words), len(curr_words))
                if overlap < 0.08 and len(prev_words) > 3 and len(curr_words) > 3:
                    topic_switches += 1

    if topic_switches <= 1:
        consistency_score = 5
    elif topic_switches <= 3:
        consistency_score = 3
    else:
        consistency_score = 1

    details['topic_switches'] = topic_switches
    details['consistency_score'] = consistency_score

    return correction_score + context_score + consistency_score, details


def calc_efficiency_score(sessions: List[Dict]) -> Tuple[int, Dict]:
    """작업 효율성 (30점)"""
    details = {}

    all_files = Counter()
    for s in sessions:
        for fp, count in s['edit_write_files'].items():
            all_files[fp] += count

    total_files = len(all_files)
    rework_files = sum(1 for count in all_files.values() if count >= 3)

    if total_files == 0:
        rework_score = 10
        rework_ratio = 0
    else:
        rework_ratio = rework_files / total_files
        if rework_ratio <= 0.10:
            rework_score = 10
        elif rework_ratio <= 0.30:
            rework_score = 7
        else:
            rework_score = 4

    details['rework_ratio'] = round(rework_ratio * 100, 1)
    details['rework_score'] = rework_score

    total_results = 0
    error_results = 0
    for s in sessions:
        for tr in s['tool_results']:
            total_results += 1
            if tr['is_error']:
                error_results += 1

    success_rate = (total_results - error_results) / total_results if total_results > 0 else 1.0
    if success_rate >= 0.90:
        success_score = 10
    elif success_rate >= 0.70:
        success_score = 7
    else:
        success_score = 4

    details['success_rate'] = round(success_rate * 100, 1)
    details['success_score'] = success_score

    completion_found = False
    for s in sessions:
        msgs = s['user_messages']
        if msgs:
            tail_start = max(0, len(msgs) - max(1, len(msgs) * 30 // 100))
            for msg in msgs[tail_start:]:
                if any(kw in msg.lower() for kw in COMPLETION_KEYWORDS):
                    completion_found = True
                    break
        if completion_found:
            break

    completion_score = 10 if completion_found else 7
    details['completion_score'] = completion_score
    details['completion_found'] = completion_found

    return rework_score + success_score + completion_score, details


def calc_tool_fitness_score(sessions: List[Dict], complexity: str) -> Tuple[int, Dict]:
    """도구 적합성 (25점)"""
    details = {}

    antipattern_count = 0
    for s in sessions:
        for cmd in s['bash_commands']:
            is_anti = any(re.search(p, cmd) for p in BASH_ANTIPATTERNS)
            if is_anti:
                is_exception = any(re.search(ep, cmd) for ep in BASH_ANTIPATTERN_EXCEPTIONS)
                if not is_exception:
                    antipattern_count += 1

    if antipattern_count == 0:
        tool_pref_score = 10
    elif antipattern_count <= 3:
        tool_pref_score = 7
    else:
        tool_pref_score = 3

    details['bash_antipatterns'] = antipattern_count
    details['tool_pref_score'] = tool_pref_score

    has_agents = any(len(s['has_task_calls']) > 0 for s in sessions)
    agent_types = set()
    for s in sessions:
        for tc in s['has_task_calls']:
            agent_types.add(tc['subagent_type'])

    if complexity == '경량':
        delegation_score = 10 if not has_agents else 7
    elif complexity == '중량':
        delegation_score = 10 if has_agents else 7
    else:
        delegation_score = 10 if has_agents else 5

    details['has_agents'] = has_agents
    details['agent_types'] = list(agent_types)
    details['delegation_score'] = delegation_score

    edit_count = sum(1 for s in sessions for t in s['tool_uses'] if t['name'] in ('Edit', 'Write'))
    has_verification = False
    for s in sessions:
        seq = s['tool_sequence']
        for i, name in enumerate(seq):
            if name in ('Edit', 'Write'):
                if 'Bash' in seq[i + 1:i + 5]:
                    has_verification = True
                    break
        if has_verification:
            break

    if edit_count >= 5:
        verify_score = 5 if has_verification else 2
    else:
        verify_score = 5

    details['edit_count'] = edit_count
    details['has_verification'] = has_verification
    details['verify_score'] = verify_score

    return tool_pref_score + delegation_score + verify_score, details


def calc_workflow_score(sessions: List[Dict], complexity: str) -> Tuple[int, Dict]:
    """워크플로우 성숙도 (20점)"""
    details = {}

    has_git_commit = any(s['has_git_commit_bash'] for s in sessions)
    has_commit_skill = any(
        tc['skill'] in ('commit', 'granular-commit')
        for s in sessions for tc in s['has_skill_calls']
    )
    if not has_commit_skill:
        for s in sessions:
            for msg in s['user_messages']:
                if re.search(r'(?:^|[\s])/(commit|granular-commit)\b', msg):
                    has_commit_skill = True
                    break
            if has_commit_skill:
                break

    has_other_skills = any(len(s['has_skill_calls']) > 0 for s in sessions)
    if not has_other_skills:
        skill_commands = ['/session-analyzer', '/retrospective', '/sequence-diagram',
                          '/code-review', '/feature']
        for s in sessions:
            for msg in s['user_messages']:
                if any(cmd in msg for cmd in skill_commands):
                    has_other_skills = True
                    break
            if has_other_skills:
                break

    if has_git_commit and not has_commit_skill:
        auto_score = 4
    elif has_commit_skill or has_other_skills:
        auto_score = 7
    else:
        auto_score = 7

    details['has_git_commit'] = has_git_commit
    details['has_commit_skill'] = has_commit_skill
    details['auto_score'] = auto_score

    same_error_retries = 0
    for s in sessions:
        failed_ids = {tr['tool_use_id'] for tr in s['tool_results'] if tr['is_error']}
        consecutive_fails = 0
        prev_failed_name = None
        for tu in s['tool_uses']:
            if tu['id'] in failed_ids:
                if prev_failed_name == tu['name']:
                    consecutive_fails += 1
                prev_failed_name = tu['name']
            else:
                if consecutive_fails >= 2:
                    same_error_retries += 1
                consecutive_fails = 0
                prev_failed_name = None
        if consecutive_fails >= 2:
            same_error_retries += 1

    if same_error_retries == 0:
        error_adapt_score = 7
    elif same_error_retries == 1:
        error_adapt_score = 5
    else:
        error_adapt_score = 3

    details['same_error_retries'] = same_error_retries
    details['error_adapt_score'] = error_adapt_score

    has_compact = any(s['has_compact'] for s in sessions)
    if complexity in ('경량', '중량'):
        context_score = 6
    else:
        context_score = 6 if has_compact else 3

    details['has_compact'] = has_compact
    details['context_score'] = context_score

    return auto_score + error_adapt_score + context_score, details


def get_grade(score: int) -> Tuple[str, str]:
    if score >= 90:
        return 'S', 'Claude Code 마스터'
    elif score >= 75:
        return 'A', '숙련된 사용자'
    elif score >= 60:
        return 'B', '중급 사용자'
    elif score >= 40:
        return 'C', '초급 사용자'
    else:
        return 'D', '입문자'


def get_evaluation_text(score: int, max_score: int) -> str:
    ratio = score / max_score if max_score > 0 else 0
    if ratio >= 0.8:
        return '우수'
    elif ratio >= 0.6:
        return '양호'
    elif ratio >= 0.4:
        return '보통'
    else:
        return '미흡'


def generate_feedback(intent_d, efficiency_d, fitness_d, workflow_d, complexity):
    """잘한 점 / 개선 포인트 생성"""
    good, improve = [], []

    if intent_d['correction_score'] >= 13:
        good.append("명확한 의도 전달로 수정 지시가 거의 없었습니다")
    elif intent_d['correction_score'] <= 5:
        improve.append(f"수정 지시 비율이 {intent_d['correction_ratio']}%입니다. 초기 지시를 더 구체적으로 작성하면 재작업이 줄어듭니다")

    if intent_d['context_score'] >= 4:
        good.append("첫 메시지에서 충분한 컨텍스트를 제공했습니다")

    if efficiency_d['rework_score'] >= 8 and efficiency_d['rework_ratio'] > 0:
        good.append("파일 수정을 한번에 정확하게 수행하여 재작업이 적었습니다")
    elif efficiency_d['rework_score'] <= 5:
        improve.append(f"재작업 비율이 {efficiency_d['rework_ratio']}%입니다. 수정 전 파일을 먼저 Read로 확인하면 재작업을 줄일 수 있습니다")

    if efficiency_d['success_score'] >= 8:
        good.append(f"도구 호출 성공률이 {efficiency_d['success_rate']}%로 높습니다")
    elif efficiency_d['success_score'] <= 5:
        improve.append(f"도구 호출 성공률이 {efficiency_d['success_rate']}%입니다. 호출 전 입력을 더 정확하게 준비하면 효율이 높아집니다")

    if fitness_d['tool_pref_score'] >= 8:
        good.append("전용 도구를 적절히 사용하여 Bash 의존도가 낮았습니다")
    elif fitness_d['tool_pref_score'] <= 4:
        improve.append(f"Bash에서 grep/cat/find 등을 {fitness_d['bash_antipatterns']}회 사용했습니다. Grep/Read/Glob 전용 도구를 사용하면 더 효율적입니다")

    if complexity == '경량' and not fitness_d['has_agents']:
        good.append("소규모 작업을 Sub Agent 없이 빠르게 직접 처리했습니다")
    elif complexity == '중량급' and fitness_d['delegation_score'] >= 8:
        good.append("대규모 작업에서 Sub Agent를 적절히 활용하여 효율적으로 위임했습니다")
    elif complexity == '중량급' and fitness_d['delegation_score'] <= 5:
        improve.append("대규모 작업에서 Explore/Plan 에이전트를 활용하면 더 효율적으로 탐색/설계할 수 있습니다")

    if workflow_d['has_commit_skill']:
        good.append("커밋 자동화 스킬을 활용하여 반복 작업을 줄였습니다")
    elif workflow_d['has_git_commit'] and not workflow_d['has_commit_skill']:
        improve.append("/commit 또는 /granular-commit 스킬을 활용하면 커밋 작업을 자동화할 수 있습니다")

    if workflow_d['error_adapt_score'] >= 6:
        good.append("에러 발생 시 적응적으로 접근법을 변경했습니다")
    elif workflow_d['error_adapt_score'] <= 3:
        improve.append("같은 도구로 연속 실패한 경우가 있습니다. 다른 접근법을 시도하면 더 빠르게 해결할 수 있습니다")

    if not good:
        good.append("도구를 활용하여 작업을 수행했습니다")
    if not improve:
        improve.append("현재 활용도가 높습니다. 새로운 스킬이나 기능을 탐색해보세요")

    return good[:4], improve[:3]


# ============================================================================
# Section 5: Main Orchestration
# ============================================================================

def analyze_date(target_date: str, projects_dir: str) -> Dict:
    """특정 날짜의 JSONL 로그를 통합 분석"""
    date = datetime.strptime(target_date, '%Y-%m-%d')
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

    files = find_session_files(Path(projects_dir), start, end)

    if not files:
        return {'date': target_date, 'error': '세션 없음', 'sessions_found': 0}

    sessions = []
    for f in files:
        parsed = parse_session_enhanced(f)
        if parsed['total_user_messages'] >= 1 and len(parsed['tool_uses']) >= 1:
            sessions.append(parsed)

    if not sessions:
        return {'date': target_date, 'error': '유효 세션 없음', 'sessions_found': len(files)}

    # Analysis
    stats = compute_statistics(sessions)
    tech_stack = analyze_tech_stack(sessions)
    tool_usage = analyze_tool_usage(sessions)
    thinking_insights = extract_thinking_insights(sessions)
    workflow_patterns = analyze_workflow_patterns(sessions)

    task_type_counter = Counter()
    session_details = []
    for s in sessions:
        types = classify_task_types(s)
        for t in types:
            task_type_counter[t] += 1

        first_msg = s['user_messages'][0] if s['user_messages'] else ''
        summary = first_msg[:100] + '...' if len(first_msg) > 100 else first_msg

        session_details.append({
            'task_types': types,
            'summary': summary,
            'message_count': s['total_messages'],
            'tool_call_count': len(s['tool_uses']),
            'skill_calls': s['has_skill_calls'],
            'task_calls': s['has_task_calls'],
            'commands_used': s['commands_used'],
        })

    # Scoring
    complexity = classify_complexity(sessions)
    intent_score, intent_details = calc_intent_score(sessions)
    efficiency_score, efficiency_details = calc_efficiency_score(sessions)
    fitness_score, fitness_details = calc_tool_fitness_score(sessions, complexity)
    workflow_score, workflow_details = calc_workflow_score(sessions, complexity)
    total_score = intent_score + efficiency_score + fitness_score + workflow_score
    grade, grade_desc = get_grade(total_score)
    good_points, improve_points = generate_feedback(
        intent_details, efficiency_details, fitness_details, workflow_details, complexity
    )

    return {
        'date_range': {
            'start': start.isoformat(),
            'end': end.isoformat(),
        },
        'sessions_found': len(files),
        'sessions_analyzed': len(sessions),
        'statistics': stats,
        'tech_stack': tech_stack,
        'task_types': dict(task_type_counter.most_common()),
        'tool_usage': tool_usage,
        'thinking_insights': thinking_insights,
        'workflow_patterns': workflow_patterns,
        'session_details': session_details,
        'scoring': {
            'complexity': complexity,
            'total_score': total_score,
            'grade': grade,
            'grade_desc': grade_desc,
            'categories': {
                'intent': {
                    'score': intent_score,
                    'max': 25,
                    'eval': get_evaluation_text(intent_score, 25),
                    'details': intent_details,
                },
                'efficiency': {
                    'score': efficiency_score,
                    'max': 30,
                    'eval': get_evaluation_text(efficiency_score, 30),
                    'details': efficiency_details,
                },
                'fitness': {
                    'score': fitness_score,
                    'max': 25,
                    'eval': get_evaluation_text(fitness_score, 25),
                    'details': fitness_details,
                },
                'workflow': {
                    'score': workflow_score,
                    'max': 20,
                    'eval': get_evaluation_text(workflow_score, 20),
                    'details': workflow_details,
                },
            },
            'good_points': good_points,
            'improve_points': improve_points,
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Session Analyzer - JSONL 세션 로그 통합 분석')
    parser.add_argument('--date', type=str, help='분석할 날짜 (YYYY-MM-DD)')
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'),
                        help='날짜 범위 (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--projects-dir', type=str,
                        default=os.path.expanduser('~/.claude/projects'),
                        help='프로젝트 디렉토리 (기본: ~/.claude/projects)')

    args = parser.parse_args()

    if args.date:
        result = analyze_date(args.date, args.projects_dir)
        if 'error' in result:
            print(f"{result['error']}: {result['date']}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.date_range:
        start = datetime.strptime(args.date_range[0], '%Y-%m-%d')
        end = datetime.strptime(args.date_range[1], '%Y-%m-%d')

        all_sessions_data = []
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            result = analyze_date(date_str, args.projects_dir)
            if 'error' not in result:
                all_sessions_data.append(result)
            else:
                print(f"  {date_str}: {result.get('error', '?')}", file=sys.stderr)
            current += timedelta(days=1)

        if not all_sessions_data:
            print("선택한 기간에 유효한 세션이 없습니다.", file=sys.stderr)
            sys.exit(1)

        print(json.dumps(all_sessions_data, ensure_ascii=False, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
