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
from difflib import SequenceMatcher
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

BUILTIN_COMMANDS = {
    'clear', 'compact', 'exit', 'mcp', 'context', 'doctor', 'agents',
    'memory', 'skills', 'model', 'help', 'fast', 'config', 'init',
    'status', 'terminal-setup', 'vim', 'tasks', 'permissions',
    'cost', 'login', 'logout', 'review', 'bug', 'pr-comments',
}


def get_skill_and_command_names() -> Tuple[set, set]:
    """~/.claude/skills/와 ~/.claude/commands/를 스캔하여 이름 세트 반환"""
    home = Path.home()
    skill_names = set()
    command_names = set()
    try:
        skills_dir = home / '.claude' / 'skills'
        if skills_dir.is_dir():
            for d in skills_dir.iterdir():
                if d.is_dir() and (d / 'SKILL.md').exists():
                    skill_names.add(d.name)
    except Exception:
        pass
    try:
        commands_dir = home / '.claude' / 'commands'
        if commands_dir.is_dir():
            for p in commands_dir.glob('*.md'):
                command_names.add(p.stem)
    except Exception:
        pass
    return skill_names, command_names


def get_skill_descriptions() -> dict:
    """~/.claude/skills/*/SKILL.md frontmatter에서 description 첫 줄 추출"""
    home = Path.home()
    descriptions = {}
    skills_dir = home / '.claude' / 'skills'
    if not skills_dir.is_dir():
        return descriptions
    for d in skills_dir.iterdir():
        if not d.is_dir() or not (d / 'SKILL.md').exists():
            continue
        try:
            content = (d / 'SKILL.md').read_text(encoding='utf-8')
            if not content.startswith('---'):
                continue
            end = content.find('---', 3)
            if end <= 0:
                continue
            frontmatter = content[3:end]
            for line in frontmatter.split('\n'):
                if line.strip().startswith('description:'):
                    desc = line.split('description:', 1)[1].strip()
                    if desc in ('|', '>'):
                        next_lines = [l.strip() for l in frontmatter.split('description:')[1].split('\n')[1:] if l.strip()]
                        desc = next_lines[0] if next_lines else ''
                    # 첫 문장 추출: "다." "요." "다!" 또는 ". " 뒤 대문자 기준
                    import re
                    m = re.search(r'[다요니습]\.|\.\s+[A-Z가-힣]', desc)
                    if m:
                        desc = desc[:m.start() + 2].rstrip()
                    descriptions[f'/{d.name}'] = desc
                    break
        except Exception:
            pass
    return descriptions


BUILTIN_COMMAND_DESCRIPTIONS = {
    '/compact': '대화 컨텍스트 압축',
    '/clear': '대화 기록 초기화',
    '/model': '사용 모델 변경',
    '/help': '도움말 표시',
    '/doctor': '설정 상태 진단',
    '/agents': '에이전트 목록 조회',
    '/memory': '메모리 관리',
    '/skills': '스킬 목록 조회',
    '/fast': '빠른 출력 모드 토글',
    '/login': '계정 로그인',
    '/sync-context': '프로젝트 컨텍스트 동기화',
    '/daily': '일일 요약 조회',
    '/private': '비공개 모드',
    '/admin': '관리자 모드',
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

# Prompt style patterns
COMMAND_STYLE_PATTERNS = [
    r'^\/\w+',                    # /commit, /review 등 슬래시 커맨드
    r'^.{1,20}해줘$',             # "XX 해줘" 형식
    r'^.{1,20}해$',               # "XX 해" 형식
    r'^.{1,15}$',                 # 15자 이하 짧은 명령
]

PLAN_BASED_PATTERNS = [
    r'```',                       # 코드 블록 포함
    r'^#+\s',                     # 마크다운 헤딩
    r'^\d+\.\s',                  # 번호 매기기
    r'^[-*]\s',                   # 불릿 리스트
    r'##\s.*계획',                # 계획 관련 헤딩
]

# Error type patterns
ERROR_TYPE_PATTERNS = {
    'command_not_found': [r'command not found', r'not recognized', r'명령어.*찾을 수 없'],
    'file_not_found': [r'no such file', r'ENOENT', r'파일.*찾을 수 없', r'does not exist'],
    'syntax_error': [r'syntax error', r'SyntaxError', r'parse error', r'문법.*오류'],
    'permission_denied': [r'permission denied', r'EACCES', r'권한'],
    'timeout': [r'timeout', r'timed out', r'ETIMEDOUT'],
    'module_not_found': [r'module not found', r'cannot find module', r'ModuleNotFoundError'],
    'type_error': [r'TypeError', r'type error', r'타입.*오류'],
}

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


def _detect_config_change(file_path: str, tool_name: str, tool_input: dict = None) -> Dict[str, str]:
    """Edit/Write 대상 파일이 스킬/커맨드/프로젝트 설정 파일인지 감지"""
    result = {}

    # 스킬 파일: ~/.claude/skills/<skill_name>/...
    skill_match = re.search(r'/\.claude/skills/([^/]+)/', file_path)
    if skill_match:
        result = {
            'category': 'skill',
            'name': skill_match.group(1),
            'action': 'modified' if tool_name == 'Edit' else 'created/modified',
        }

    # 커스텀 커맨드 파일: ~/.claude/commands/<command_name>.md
    if not result:
        cmd_match = re.search(r'/\.claude/commands/([^/]+?)(?:\.\w+)?$', file_path)
        if cmd_match:
            result = {
                'category': 'command',
                'name': cmd_match.group(1),
                'action': 'modified' if tool_name == 'Edit' else 'created/modified',
            }

    # CLAUDE.md (프로젝트 설정)
    if not result and file_path.endswith('CLAUDE.md'):
        result = {
            'category': 'project_config',
            'name': 'CLAUDE.md',
            'action': 'modified' if tool_name == 'Edit' else 'created/modified',
        }

    # settings.json
    if not result and file_path.endswith('.claude/settings.json'):
        result = {
            'category': 'settings',
            'name': 'settings.json',
            'action': 'modified' if tool_name == 'Edit' else 'created/modified',
        }

    if result:
        result['detail'] = _extract_change_detail(file_path, tool_name, tool_input or {})

    return result


def _strip_code_blocks(text: str) -> str:
    """마크다운 텍스트에서 코드 블록(``` ... ```)을 제거"""
    return re.sub(r'```[\s\S]*?```', '', text)


def _extract_prose_lines(text: str) -> list:
    """마크다운에서 자연어 줄만 추출 (코드/테이블/구조/경로/명령어 제외)"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    result = []
    for line in lines:
        # 구조적 요소 스킵: 헤더, 테이블, 구분선, HTML, 인라인코드만 있는 줄
        if re.match(r'^[|#{}`<>]', line):
            continue
        if re.match(r'^[-=*]{3,}$|^---\s*$', line):
            continue
        # 리스트 마커 제거
        cleaned = re.sub(r'^[-*]\s+', '', line)
        cleaned = re.sub(r'^\d+\.\s+', '', cleaned)
        # 화살표 접두사 제거 (예: "→ 자동 저장: ...")
        cleaned = re.sub(r'^[→>]\s*', '', cleaned)
        # 마크다운 포맷팅 제거
        cleaned = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', cleaned)
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
        # 코드처럼 보이는 줄 스킵 (괄호, 중괄호, 세미콜론, import 등)
        if re.search(r'[{}();=]|^import |^from |^def |^class |^if |^for |^return ', cleaned):
            continue
        # 파일 경로 패턴 스킵 (~/..., /..., ../...)
        if re.search(r'(?:^|[\s])(?:~/|/[\w.]|\.\./)[\w./-]+', cleaned):
            continue
        # 트리 구조 문자 스킵 (├── └── │ 등)
        if re.search(r'[├└│──]+', cleaned):
            continue
        # CLI 명령어 패턴 스킵
        if re.search(r'^(?:npm |pip |git |python3?\s|node |yarn |cargo |make\s|brew )', cleaned):
            continue
        # 콜론으로 끝나는 불완전 문장 스킵
        if re.match(r'.+:$', cleaned):
            continue
        # 함수명 괄호 패턴 포함 줄 스킵 (예: "변환(parse_timestamp)")
        if re.search(r'\(\w+(?:_\w+)+\)', cleaned):
            continue
        # 짧은 주석/메타 표기 스킵 (# comment 형태, 30자 미만)
        if re.search(r'#\s+\w+', cleaned) and len(cleaned) < 30:
            continue
        # Template/placeholder 패턴 스킵 ([N], [작업 유형] 등 2개 이상 포함)
        if len(re.findall(r'\[[^\]]*\]', cleaned)) >= 2:
            continue
        if len(cleaned) > 5:
            result.append(cleaned[:80])
    return result


def _sanitize_detail(detail: str) -> str:
    """detail 문자열의 품질 보정: 경로/코드 제거, 불완전 문장 감지, 보안 필터링"""
    if not detail:
        return ''

    # 1. 파일 경로 제거 (~/..., /Users/..., /home/..., ./..., ../...)
    detail = re.sub(r'(?:~/|/(?:Users|home)/)[^\s,)]+', '', detail)
    detail = re.sub(r'(?:^|[\s])(?:\./|\.\./)[\w./-]+', '', detail)

    # 2. 괄호 패턴 제거: 함수명 "(func_name)", 코드 옵션 "(--flag", 불완전 괄호 "(xxx"
    detail = re.sub(r'\(\w+(?:_\w+)+\)', '', detail)  # (snake_case)
    detail = re.sub(r'\([^)]{0,30}$', '', detail)  # 닫히지 않은 괄호 제거
    detail = re.sub(r'\(-[^\)]*\)', '', detail)  # (--flag) 스타일

    # 3. 중복 쉼표/공백 정리 (괄호 제거 후 잔여물)
    detail = re.sub(r',\s*,', ',', detail)
    detail = re.sub(r'\s+', ' ', detail).strip()
    detail = detail.strip(',').strip()

    # 4. 콜론으로 끝나는 불완전 문장 → 빈 문자열
    if detail.endswith(':'):
        return ''

    # 5. ISO 타임스탬프 제거
    detail = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\w.:+-]*', '', detail)

    # 6. 말 끊김 감지: 종결 표현 없이 끝나는 문장 → 빈 문자열
    detail = detail.strip()
    if len(detail) > 10:
        endings = ('추가', '수정', '생성', '작성', '개선', '변경', '삭제', '제거', '적용',
                   '포함', '반영', '구현', '설정', '처리', '완료', '업데이트', '강화', '정리',
                   '.', '!', '?', '다', '요', '음', '함', '임', '됨')
        if not any(detail.endswith(e) for e in endings):
            return ''

    # 7. 정리 후 너무 짧으면 빈 문자열
    detail = re.sub(r'\s+', ' ', detail).strip()
    if len(detail) < 5:
        return ''

    # 8. Template/placeholder 패턴 ([N], [작업 유형] 등 2개 이상)
    if len(re.findall(r'\[[^\]]*\]', detail)) >= 2:
        return ''

    # 9. Private 함수/메서드명 참조 (_로 시작하는 식별자)
    if re.search(r'\b_[a-z]\w{2,}\b', detail):
        return ''

    return detail


def _deduplicate_details(details: list, threshold: float = 0.75) -> list:
    """의미적으로 유사한 detail을 제거. threshold 이상 유사도면 중복으로 판단."""
    if len(details) <= 1:
        return details

    result = []
    for detail in details:
        norm_detail = re.sub(r'[\s.,;:]+', ' ', detail).strip().rstrip('.')
        is_dup = False
        for i, existing in enumerate(result):
            norm_existing = re.sub(r'[\s.,;:]+', ' ', existing).strip().rstrip('.')
            ratio = SequenceMatcher(None, norm_detail, norm_existing).ratio()
            if ratio >= threshold:
                is_dup = True
                # 더 긴(구체적인) 쪽을 유지
                if len(detail) > len(existing):
                    result[i] = detail
                break
        if not is_dup:
            result.append(detail)
    return result


def _extract_change_detail(file_path: str, tool_name: str, tool_input: dict) -> str:
    """Edit/Write 내용에서 사람이 읽을 수 있는 변경 설명을 추출"""
    ext = file_path.rsplit('.', 1)[-1] if '.' in file_path else ''

    if tool_name == 'Edit':
        new_str = tool_input.get('new_string', '')
        old_str = tool_input.get('old_string', '')

        # .py 파일: 함수/클래스명 + docstring 기반 설명
        if ext == 'py':
            new_defs = re.findall(r'^\s*(?:def|class)\s+(\w+)', new_str, re.MULTILINE)
            old_defs = re.findall(r'^\s*(?:def|class)\s+(\w+)', old_str, re.MULTILINE)
            added = [d for d in new_defs if d not in old_defs and not d.startswith('_')]
            if added:
                descriptions = []
                for name in added[:3]:
                    pat = rf'(?:def|class)\s+{re.escape(name)}\s*\([^)]*\)[^:]*:\s*\n\s*(?:\"\"\"|\'\'\')([^\n\"\']+)'
                    doc_match = re.search(pat, new_str)
                    if doc_match:
                        descriptions.append(doc_match.group(1).strip()[:60])
                    else:
                        descriptions.append(name)
                result = ', '.join(descriptions) + ' 추가'
                return _sanitize_detail(result) or result
            # 기존 함수가 수정된 경우
            modified_defs = [d for d in new_defs if d in old_defs and not d.startswith('_')]
            if modified_defs:
                return ', '.join(modified_defs[:2]) + ' 로직 수정'
            return ''

        # .md 파일: 코드 블록 제거 후 헤더 또는 자연어 추출
        if ext == 'md':
            new_clean = _strip_code_blocks(new_str)
            old_clean = _strip_code_blocks(old_str)

            # 새로 추가된 섹션 헤더
            new_headers = re.findall(r'^#{2,4}\s+(.+)', new_clean, re.MULTILINE)
            old_headers = re.findall(r'^#{2,4}\s+(.+)', old_clean, re.MULTILINE)
            added_headers = [h for h in new_headers if h not in old_headers]
            if added_headers:
                result = ', '.join(h[:30] for h in added_headers[:2]) + ' 섹션 추가'
                sanitized = _sanitize_detail(result)
                if sanitized:
                    return sanitized

            # 새로 추가된 자연어 줄
            old_prose = set(_extract_prose_lines(old_clean))
            new_prose = _extract_prose_lines(new_clean)
            added_prose = [l for l in new_prose if l not in old_prose]
            for line in added_prose[:3]:
                candidate = _sanitize_detail(line)
                if candidate:
                    return candidate

            return ''

        # .json 파일
        if ext == 'json':
            return '설정 값 수정'

        return ''

    elif tool_name == 'Write':
        content = tool_input.get('content', '')

        if ext == 'md':
            clean = _strip_code_blocks(content)
            headers = re.findall(r'^#{1,3}\s+(.+)', clean, re.MULTILINE)
            if headers:
                result = ', '.join(h[:30] for h in headers[:3]) + ' 포함 문서 작성'
                sanitized = _sanitize_detail(result)
                if sanitized:
                    return sanitized
            # 헤더 없는 경우 첫 의미 있는 줄 추출
            prose = _extract_prose_lines(clean)
            for line in prose[:3]:
                candidate = _sanitize_detail(line)
                if candidate:
                    return candidate
            return '문서 파일 생성'

        if ext == 'py':
            defs = re.findall(r'^\s*(?:def|class)\s+(\w+)', content, re.MULTILINE)
            if defs:
                descriptions = []
                for name in defs[:3]:
                    pat = rf'(?:def|class)\s+{re.escape(name)}\s*\([^)]*\)[^:]*:\s*\n\s*(?:\"\"\"|\'\'\')([^\n\"\']+)'
                    doc_match = re.search(pat, content)
                    if doc_match:
                        descriptions.append(doc_match.group(1).strip()[:60])
                    else:
                        descriptions.append(name)
                result = ', '.join(descriptions) + ' 포함 파일 생성'
                return _sanitize_detail(result) or result
            return '코드 파일 생성'

        if ext == 'json':
            return '설정 파일 생성'

        return '파일 생성'

    return '내용 변경'


def parse_session_enhanced(file_path: Path, skill_names: set = None, command_names: set = None) -> Dict[str, Any]:
    """세션 파일을 분석에 필요한 모든 데이터로 파싱"""
    if skill_names is None:
        skill_names = set()
    if command_names is None:
        command_names = set()
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
        'has_custom_command_calls': [],
        'has_compact': False,
        'has_git_commit_bash': False,
        'tool_sequence': [],
        'commands_used': [],
        'config_changes': [],
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
                            # <command-name> 태그에서 스킬/커스텀 커맨드/빌트인 3단계 분류
                            tag_match = re.findall(r'<command-name>\/([a-z][\w-]*)<\/command-name>', content)
                            for name in tag_match:
                                if name in skill_names:
                                    data['has_skill_calls'].append({'skill': name})
                                elif name in command_names:
                                    data['has_custom_command_calls'].append({'command': name})
                                elif name not in BUILTIN_COMMANDS:
                                    data['has_skill_calls'].append({'skill': name})
                            # 슬래시 커맨드 탐지 (파일 경로 제외)
                            cmd_match = re.findall(r'(?:^|[\s])(\/[a-z][\w-]*)', content)
                            for cmd in cmd_match:
                                if not re.match(r'^/(Users|var|tmp|etc|home|opt|usr|bin|lib|path|로)', cmd):
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
                                    # <command-name> 태그에서 스킬 감지
                                    skill_match = re.findall(r'<command-name>\/([a-z][\w-]*)<\/command-name>', text)
                                    for skill_name in skill_match:
                                        data['has_skill_calls'].append({'skill': skill_name})
                                    cmd_match = re.findall(r'(?:^|[\s])(\/[a-z][\w-]*)', text)
                                    for cmd in cmd_match:
                                        # 파일 경로 패턴 제외
                                        if not re.match(r'^/(Users|var|tmp|etc|home|opt|usr|bin|lib|path|로)', cmd):
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
                                        # 설정 파일 변경 감지
                                        config_change = _detect_config_change(fp, tool_name, tool_input)
                                        if config_change:
                                            data['config_changes'].append(config_change)

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


def analyze_tool_usage(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """도구 사용 빈도 분석 (Top 5)"""
    counter = Counter()
    for session in sessions:
        for tu in session.get('tool_uses', []):
            name = tu.get('name')
            if name:
                counter[name] += 1
    return [{'name': name, 'count': count} for name, count in counter.most_common(5)]


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


def analyze_workflow_patterns(sessions: List[Dict[str, Any]]) -> str:
    """워크플로우 패턴 분석 (3-gram) - 가장 빈번한 패턴 1개 반환"""
    patterns = Counter()
    for session in sessions:
        seq = session.get('tool_sequence', [])
        for i in range(len(seq) - 2):
            pattern = ' → '.join(seq[i:i + 3])
            patterns[pattern] += 1

    if patterns:
        top_pattern, count = patterns.most_common(1)[0]
        return top_pattern
    return ""


# ============================================================================
# Section 3.5: New Analysis Functions (Prompt, Error, Usage Style)
# ============================================================================

def classify_prompt_length(length: int) -> str:
    """프롬프트 길이 분류"""
    if length < 100:
        return 'short'
    elif length <= 500:
        return 'medium'
    else:
        return 'long'


def analyze_prompt_style(message: str) -> str:
    """프롬프트 스타일 분석"""
    # 계획 기반 스타일 (마크다운 계획서 형식)
    for pattern in PLAN_BASED_PATTERNS:
        if re.search(pattern, message, re.MULTILINE):
            return 'plan_based_style'

    # 명령형 스타일 (짧은 지시)
    for pattern in COMMAND_STYLE_PATTERNS:
        if re.search(pattern, message):
            return 'command_style'

    # 나머지는 설명형
    return 'descriptive_style'


def analyze_prompt_statistics(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """프롬프트 길이 및 스타일 통계 분석"""
    all_messages = []
    for session in sessions:
        all_messages.extend(session.get('user_messages', []))

    if not all_messages:
        return {
            'total_prompts': 0,
            'avg_length': 0,
            'max_length': 0,
            'min_length': 0,
            'length_distribution': {
                'short': {'count': 0, 'percent': 0, 'range': '< 100자'},
                'medium': {'count': 0, 'percent': 0, 'range': '100-500자'},
                'long': {'count': 0, 'percent': 0, 'range': '> 500자'},
            },
            'style_analysis': {
                'command_style': 0,
                'descriptive_style': 0,
                'plan_based_style': 0,
            }
        }

    lengths = [len(msg) for msg in all_messages]
    total = len(all_messages)

    # 길이 분포
    length_dist = Counter(classify_prompt_length(l) for l in lengths)

    # 스타일 분석
    style_dist = Counter(analyze_prompt_style(msg) for msg in all_messages)

    return {
        'total_prompts': total,
        'avg_length': round(sum(lengths) / total, 1),
        'max_length': max(lengths),
        'min_length': min(lengths),
        'length_distribution': {
            'short': {
                'count': length_dist.get('short', 0),
                'percent': round(length_dist.get('short', 0) / total * 100, 1),
                'range': '< 100자'
            },
            'medium': {
                'count': length_dist.get('medium', 0),
                'percent': round(length_dist.get('medium', 0) / total * 100, 1),
                'range': '100-500자'
            },
            'long': {
                'count': length_dist.get('long', 0),
                'percent': round(length_dist.get('long', 0) / total * 100, 1),
                'range': '> 500자'
            },
        },
        'style_analysis': {
            'command_style': style_dist.get('command_style', 0),
            'descriptive_style': style_dist.get('descriptive_style', 0),
            'plan_based_style': style_dist.get('plan_based_style', 0),
        }
    }


def classify_error_type(error_content: str) -> str:
    """에러 유형 분류"""
    error_lower = error_content.lower()
    for error_type, patterns in ERROR_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, error_lower, re.IGNORECASE):
                return error_type
    return 'other'


def analyze_error_patterns(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """에러 패턴 분석"""
    all_tool_results = []
    all_errors = []

    for session in sessions:
        results = session.get('tool_results', [])
        all_tool_results.extend(results)
        errors = [r for r in results if r.get('is_error')]
        all_errors.extend(errors)

    total_results = len(all_tool_results)
    total_errors = len(all_errors)

    if total_results == 0:
        return {
            'total_errors': 0,
            'error_rate': 0,
            'error_types': {},
            'recovery_patterns': {
                'immediate_fix': 0,
                'retry_same': 0,
                'alternative_approach': 0,
            },
            'frequent_errors': []
        }

    # 에러 유형 분류
    error_types = Counter()
    error_messages = []
    for error in all_errors:
        content = error.get('content', '')
        error_type = classify_error_type(content)
        error_types[error_type] += 1
        if content:
            error_messages.append(content[:100])

    # 에러 복구 패턴 분석
    recovery_patterns = {'immediate_fix': 0, 'retry_same': 0, 'alternative_approach': 0}

    for session in sessions:
        tool_uses = session.get('tool_uses', [])
        tool_results = session.get('tool_results', [])
        failed_ids = {tr['tool_use_id'] for tr in tool_results if tr.get('is_error')}

        for i, tu in enumerate(tool_uses):
            if tu.get('id') in failed_ids:
                # 다음 도구 호출 확인
                if i + 1 < len(tool_uses):
                    next_tu = tool_uses[i + 1]
                    if next_tu.get('name') == tu.get('name'):
                        # 같은 도구 재시도
                        recovery_patterns['retry_same'] += 1
                    else:
                        # 다른 도구로 전환
                        recovery_patterns['alternative_approach'] += 1
                else:
                    # 즉시 수정 (세션 끝에서 에러 후 종료)
                    recovery_patterns['immediate_fix'] += 1

    # 자주 발생하는 에러 패턴 추출
    error_pattern_counter = Counter()
    for content in error_messages:
        # 에러 메시지에서 패턴 추출
        if 'not found' in content.lower():
            error_pattern_counter['Not found error'] += 1
        elif 'error' in content.lower():
            error_pattern_counter['General error'] += 1
        elif 'failed' in content.lower():
            error_pattern_counter['Operation failed'] += 1

    frequent_errors = [
        {'pattern': p, 'count': c}
        for p, c in error_pattern_counter.most_common(5)
    ]

    return {
        'total_errors': total_errors,
        'error_rate': round(total_errors / total_results * 100, 1) if total_results > 0 else 0,
        'error_types': dict(error_types),
        'recovery_patterns': recovery_patterns,
        'frequent_errors': frequent_errors
    }


def classify_session_scale(session: Dict[str, Any]) -> str:
    """세션 규모 분류"""
    turn_count = session.get('total_user_messages', 0)
    if turn_count >= 70:
        return 'large'
    elif turn_count >= 40:
        return 'medium'
    else:
        return 'small'


def analyze_usage_style(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """사용 스타일 종합 분석"""
    if not sessions:
        return {
            'session_scale': {},
            'correction_frequency': {'initial_requests': 0, 'follow_up_corrections': 0, 'ratio': 0},
            'strengths': [],
            'improvements': [],
            'context_management_tips': []
        }

    # 세션 규모 분포
    scale_counter = Counter(classify_session_scale(s) for s in sessions)
    scale_stats = {}

    for scale in ['large', 'medium', 'small']:
        matching_sessions = [s for s in sessions if classify_session_scale(s) == scale]
        if matching_sessions:
            avg_turns = sum(s.get('total_user_messages', 0) for s in matching_sessions) / len(matching_sessions)
            descriptions = {'large': '70-150턴', 'medium': '40-70턴', 'small': '5-15턴'}
            scale_stats[scale] = {
                'count': len(matching_sessions),
                'avg_turns': round(avg_turns, 1),
                'description': descriptions.get(scale, '')
            }

    # 수정 요청 빈도 분석
    initial_requests = 0
    follow_up_corrections = 0

    for session in sessions:
        msgs = session.get('user_messages', [])
        if msgs:
            initial_requests += 1  # 첫 요청
            for msg in msgs[1:]:  # 이후 메시지
                if any(kw in msg.lower() for kw in CORRECTION_KEYWORDS):
                    follow_up_corrections += 1

    correction_ratio = round(follow_up_corrections / initial_requests, 2) if initial_requests > 0 else 0

    # 강점 분석
    strengths = []

    # 1. 계획 기반 요청 비율이 높은지
    plan_based_count = sum(
        1 for s in sessions
        for msg in s.get('user_messages', [])
        if analyze_prompt_style(msg) == 'plan_based_style'
    )
    total_msgs = sum(len(s.get('user_messages', [])) for s in sessions)
    if total_msgs > 0 and plan_based_count / total_msgs > 0.3:
        strengths.append("사전 계획 제공으로 명확한 기대치 설정")

    # 2. Sub Agent 활용 여부
    has_task_agents = any(len(s.get('has_task_calls', [])) > 0 for s in sessions)
    if has_task_agents:
        agent_types = set()
        for s in sessions:
            for tc in s.get('has_task_calls', []):
                agent_types.add(tc.get('subagent_type', ''))
        if len(agent_types) >= 2:
            strengths.append(f"{len(agent_types)}개 병렬 에이전트 활용 (품질 중심)")

    # 3. 검증 패턴
    has_verification = False
    for s in sessions:
        seq = s.get('tool_sequence', [])
        for i, name in enumerate(seq):
            if name in ('Edit', 'Write'):
                if 'Bash' in seq[i + 1:i + 5]:
                    has_verification = True
                    break
        if has_verification:
            break

    if has_verification:
        strengths.append("구현 후 빌드/린트 검증 필수 수행")

    # 4. 스킬 활용
    has_skills = any(len(s.get('has_skill_calls', [])) > 0 for s in sessions)
    if has_skills:
        strengths.append("자동화 스킬을 활용하여 반복 작업 감소")

    if not strengths:
        strengths.append("도구를 활용하여 작업 수행")

    # 개선점 분석
    improvements = []

    # 1. 세션당 턴 수가 많은 경우
    avg_turns = sum(s.get('total_user_messages', 0) for s in sessions) / len(sessions)
    if avg_turns > 50:
        improvements.append(f"세션당 평균 {round(avg_turns)}턴 - 컨텍스트 관리 필요")

    # 2. 후속 수정 요청이 많은 경우
    if correction_ratio > 1.5:
        improvements.append(f"후속 수정 요청이 많음 ({correction_ratio}배)")

    # 3. 긴 프롬프트 비율이 높은 경우
    long_prompt_count = sum(
        1 for s in sessions
        for msg in s.get('user_messages', [])
        if len(msg) > 500
    )
    if total_msgs > 0 and long_prompt_count / total_msgs > 0.4:
        improvements.append("긴 계획서 제공 시 토큰 소모가 클 수 있음")

    if not improvements:
        improvements.append("현재 활용도가 높습니다")

    # 컨텍스트 관리 팁
    context_tips = []

    if avg_turns > 40:
        context_tips.append("세션 분리: 50턴 기준으로 작업 단위 분할")

    context_tips.append("CLAUDE.md 강화: 코드 패턴, 체크리스트, 자주 하는 실수 추가")
    context_tips.append("auto-memory 활성화: 세션 간 학습 축적")

    if correction_ratio > 1.0:
        context_tips.append("점진적 요청: 한 번에 전체 계획 대신 단계별 진행")

    return {
        'session_scale': scale_stats,
        'correction_frequency': {
            'initial_requests': initial_requests,
            'follow_up_corrections': follow_up_corrections,
            'ratio': correction_ratio
        },
        'strengths': strengths[:4],
        'improvements': improvements[:3],
        'context_management_tips': context_tips[:4]
    }


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

def _build_analysis_result(sessions: List[Dict[str, Any]], start: datetime, end: datetime) -> Dict:
    """파싱된 세션 리스트로부터 분석 결과 dict를 생성하는 헬퍼"""
    skill_names, command_names = get_skill_and_command_names()
    skill_descriptions = get_skill_descriptions()

    # Basic statistics
    stats = compute_statistics(sessions)
    top_tools = analyze_tool_usage(sessions)
    main_workflow = analyze_workflow_patterns(sessions)

    # Task types - Top 3
    task_type_counter = Counter()
    for s in sessions:
        types = classify_task_types(s)
        for t in types:
            task_type_counter[t] += 1
    main_tasks = [t for t, _ in task_type_counter.most_common(3)]

    # Skills, Custom Commands, Agents, Built-in Commands 수집
    skills_counter = Counter()
    custom_commands_counter = Counter()
    agents_counter = Counter()
    agent_descriptions = {}
    commands_counter = Counter()

    for s in sessions:
        for sc in s.get('has_skill_calls', []):
            skill_name = sc.get('skill', '')
            if skill_name:
                skills_counter[f"/{skill_name}"] += 1
        for cc in s.get('has_custom_command_calls', []):
            cmd_name = cc.get('command', '')
            if cmd_name:
                custom_commands_counter[f"/{cmd_name}"] += 1
        for tc in s.get('has_task_calls', []):
            agent_type = tc.get('subagent_type', '')
            desc = tc.get('description', '')
            if agent_type:
                agents_counter[agent_type] += 1
                if agent_type == 'Explore':
                    agent_descriptions[agent_type] = '프로젝트 구조 및 설정 탐색'
                elif agent_type not in agent_descriptions and desc:
                    agent_descriptions[agent_type] = desc
        # commands_used에서 스킬/커스텀 커맨드 이름을 제외하고 빌트인만 추가
        known_names = {f"/{n}" for n in skill_names} | {f"/{n}" for n in command_names}
        for cmd in s.get('commands_used', []):
            if cmd not in known_names:
                commands_counter[cmd] += 1

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

    # Prompt statistics
    prompt_stats = analyze_prompt_statistics(sessions)
    error_analysis = analyze_error_patterns(sessions)
    usage_style = analyze_usage_style(sessions)

    # Calculate average words
    all_messages = []
    for session in sessions:
        all_messages.extend(session.get('user_messages', []))
    avg_words = 0
    if all_messages:
        total_words = sum(len(msg.split()) for msg in all_messages)
        avg_words = round(total_words / len(all_messages))

    # Config changes 집계 (스킬/커맨드/설정 변경 이력)
    config_changes_by_key = {}  # (category, name) → {'actions': set(), 'count': int, 'details': list}
    for session in sessions:
        for change in session.get('config_changes', []):
            key = (change['category'], change['name'])
            if key not in config_changes_by_key:
                config_changes_by_key[key] = {'actions': set(), 'count': 0, 'details': []}
            config_changes_by_key[key]['actions'].add(change['action'])
            config_changes_by_key[key]['count'] += 1
            detail = change.get('detail', '')
            if detail and detail not in config_changes_by_key[key]['details']:
                config_changes_by_key[key]['details'].append(detail)

    config_changes_result = []
    for (category, name), info in sorted(config_changes_by_key.items()):
        deduped = _deduplicate_details(info['details'])
        config_changes_result.append({
            'category': category,
            'name': name,
            'action': 'modified' if 'modified' in info['actions'] else 'created/modified',
            'changes': info['count'],
            'details': deduped[:10],
        })

    # Build simplified result
    return {
        'date_range': {
            'start': start.isoformat(),
            'end': end.isoformat(),
        },
        'summary': {
            'sessions': stats['total_sessions'],
            'avg_messages': stats['avg_messages_per_session'],
            'avg_tool_calls': stats['avg_tool_calls_per_session'],
            'main_tasks': main_tasks,
        },
        'usage_style': {
            'prompt_stats': {
                'avg_length': prompt_stats.get('avg_length', 0),
                'avg_words': avg_words,
                'distribution': {
                    'command': prompt_stats.get('style_analysis', {}).get('command_style', 0),
                    'descriptive': prompt_stats.get('style_analysis', {}).get('descriptive_style', 0),
                    'plan_based': prompt_stats.get('style_analysis', {}).get('plan_based_style', 0),
                },
            },
            'session_scale': {
                scale: {
                    'count': data.get('count', 0),
                    'avg_turns': data.get('avg_turns', 0),
                }
                for scale, data in usage_style.get('session_scale', {}).items()
            },
            'correction_ratio': {
                'initial': usage_style.get('correction_frequency', {}).get('initial_requests', 0),
                'followup': usage_style.get('correction_frequency', {}).get('follow_up_corrections', 0),
                'ratio': usage_style.get('correction_frequency', {}).get('ratio', 0),
            },
        },
        'tool_usage': {
            'skills': [{'name': name, 'count': count, 'description': skill_descriptions.get(name, '')} for name, count in skills_counter.most_common()],
            'custom_commands': [{'name': name, 'count': count, 'description': ''} for name, count in custom_commands_counter.most_common()],
            'agents': [{'type': agent_type, 'count': count, 'description': agent_descriptions.get(agent_type, '')} for agent_type, count in agents_counter.most_common()],
            'commands': [{'name': name, 'count': count, 'description': BUILTIN_COMMAND_DESCRIPTIONS.get(name, '')} for name, count in commands_counter.most_common()],
            'top_tools': top_tools,
        },
        'scoring': {
            'total': total_score,
            'grade': grade,
            'categories': {
                'intent': {'score': intent_score, 'max': 25},
                'efficiency': {'score': efficiency_score, 'max': 30},
                'fitness': {'score': fitness_score, 'max': 25},
                'workflow': {'score': workflow_score, 'max': 20},
            },
        },
        'feedback': {
            'strengths': good_points,
            'improvements': improve_points,
            'context_tips': usage_style.get('context_management_tips', []),
        },
        'error_summary': {
            'rate': error_analysis.get('error_rate', 0),
            'total': error_analysis.get('total_errors', 0),
            'main_types': list(error_analysis.get('error_types', {}).keys())[:2],
            'recovery': {
                'immediate_fix': error_analysis.get('recovery_patterns', {}).get('immediate_fix', 0),
                'alternative': error_analysis.get('recovery_patterns', {}).get('alternative_approach', 0),
            },
        },
        'main_workflow': main_workflow,
        'config_changes': config_changes_result,
    }


def analyze_date(target_date: str, projects_dir: str) -> Dict:
    """특정 날짜의 JSONL 로그를 통합 분석 (간소화된 스키마)"""
    date = datetime.strptime(target_date, '%Y-%m-%d')
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

    files = find_session_files(Path(projects_dir), start, end)

    if not files:
        return {'date': target_date, 'error': '세션 없음', 'sessions_found': 0}

    skill_names, command_names = get_skill_and_command_names()

    sessions = []
    for f in files:
        parsed = parse_session_enhanced(f, skill_names, command_names)
        if parsed['total_user_messages'] >= 1 and len(parsed['tool_uses']) >= 1:
            sessions.append(parsed)

    if not sessions:
        return {'date': target_date, 'error': '유효 세션 없음', 'sessions_found': len(files)}

    return _build_analysis_result(sessions, start, end)


def analyze_date_range(start_str: str, end_str: str, projects_dir: str) -> Dict:
    """날짜 범위의 모든 세션을 합산하여 단일 분석 결과 반환 (--weekly 모드용)"""
    start_dt = datetime.strptime(start_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)

    files = find_session_files(Path(projects_dir), start_dt, end_dt)

    if not files:
        return {'date_range': {'start': start_str, 'end': end_str}, 'error': '세션 없음', 'sessions_found': 0}

    skill_names, command_names = get_skill_and_command_names()

    sessions = []
    for f in files:
        parsed = parse_session_enhanced(f, skill_names, command_names)
        if parsed['total_user_messages'] >= 1 and len(parsed['tool_uses']) >= 1:
            sessions.append(parsed)

    if not sessions:
        return {'date_range': {'start': start_str, 'end': end_str}, 'error': '유효 세션 없음', 'sessions_found': len(files)}

    return _build_analysis_result(sessions, start_dt, end_dt)


def get_json_output_path(output_option: str, date_str: str, end_date_str: str = None, weekly: bool = False) -> str:
    """JSON 출력 경로 결정"""
    base_dir = os.path.expanduser('~/.claude/summaries')

    if output_option == 'auto':
        if weekly and date_str:
            # 주간 분석: weekly/YYYY-MM-WN.json
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            week_num = (dt.day - 1) // 7 + 1
            sub_dir = os.path.join(base_dir, 'weekly')
            filename = f"{dt.strftime('%Y-%m')}-W{week_num}.json"
        elif end_date_str and date_str != end_date_str:
            # 기간 분석
            sub_dir = os.path.join(base_dir, 'range')
            filename = f"{date_str}_to_{end_date_str}.json"
        else:
            # 단일 날짜
            sub_dir = os.path.join(base_dir, 'daily')
            filename = f"{date_str}.json"
        return os.path.join(sub_dir, filename)
    else:
        # 사용자 지정 경로
        return output_option


def save_json_output(result: Any, json_path: str) -> None:
    """JSON 결과를 파일로 저장"""
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"JSON 저장: {json_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Session Analyzer - JSONL 세션 로그 통합 분석')
    parser.add_argument('--date', type=str, help='분석할 날짜 (YYYY-MM-DD)')
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'),
                        help='날짜 범위 (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--projects-dir', type=str,
                        default=os.path.expanduser('~/.claude/projects'),
                        help='프로젝트 디렉토리 (기본: ~/.claude/projects)')
    parser.add_argument('--output-json', type=str, default='auto',
                        help='JSON 저장 경로 (기본: "auto", 경로 직접 지정 가능)')
    parser.add_argument('--weekly', action='store_true',
                        help='주간 분석 모드: weekly/ 폴더에 YYYY-MM-WN.json 형식으로 저장')
    parser.add_argument('--no-save', action='store_true',
                        help='JSON 파일 저장 생략 (stdout 출력만)')

    args = parser.parse_args()

    if args.date:
        result = analyze_date(args.date, args.projects_dir)
        if 'error' in result:
            print(f"{result['error']}: {result['date']}", file=sys.stderr)
            sys.exit(1)

        # JSON 저장 (기본: auto, --no-save로 생략 가능)
        if args.output_json and not args.no_save:
            json_path = get_json_output_path(args.output_json, args.date)
            save_json_output(result, json_path)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.date_range:
        if args.weekly:
            # --weekly: 전체 기간을 하나로 합산한 단일 결과
            result = analyze_date_range(args.date_range[0], args.date_range[1], args.projects_dir)

            if 'error' in result:
                print(f"{result['error']}: {args.date_range[0]} ~ {args.date_range[1]}", file=sys.stderr)
                sys.exit(1)

            if args.output_json and not args.no_save:
                json_path = get_json_output_path(
                    args.output_json,
                    args.date_range[0],
                    args.date_range[1],
                    weekly=True
                )
                save_json_output(result, json_path)

            print(json.dumps(result, ensure_ascii=False, indent=2))

        else:
            # 기본: 일자별 개별 결과 배열
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

            if args.output_json and not args.no_save:
                json_path = get_json_output_path(
                    args.output_json,
                    args.date_range[0],
                    args.date_range[1],
                    weekly=False
                )
                save_json_output(all_sessions_data, json_path)

            print(json.dumps(all_sessions_data, ensure_ascii=False, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
