#!/usr/bin/env python3
"""
새로운 활용도 평가 점수 계산기

JSONL 세션 로그를 분석하여 4개 카테고리(의도 전달력, 작업 효율성, 도구 적합성, 워크플로우 성숙도)
점수를 계산합니다.

사용법:
    python score_calculator.py --date 2026-02-11
    python score_calculator.py --date-range 2026-01-15 2026-02-11
"""

import json
import argparse
import sys
import re
import os
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any, Tuple

# 수정 지시 키워드
CORRECTION_KEYWORDS = [
    '다시', '아니', '그게 아니라', '원래대로', '취소', '되돌려',
    '아닌데', '아니야', '틀렸', '잘못', '이전 거', '롤백',
    '아까', '아니요', '그거 말고', '그게 아니고', '다른 거',
    '수정해', '고쳐', '바꿔', '변경해',
]

# 완료 키워드
COMPLETION_KEYWORDS = [
    '완료', 'done', '커밋', '확인', '잘 됩니다', '감사',
    '좋아', '됐어', '끝', 'commit', 'push', '고마워',
    'ㅇㅋ', 'ok', '잘 돼', '잘 동작',
]

# 구체적 컨텍스트 키워드 (에러, 파일 참조 등)
SPECIFICS_PATTERNS = [
    r'error', r'에러', r'오류',
    r'\.tsx?', r'\.jsx?', r'\.py', r'\.md', r'\.json',  # 파일 확장자
    r'src/', r'app/', r'pages/', r'components/',  # 경로
    r'```',  # 코드 블록
    r'http', r'localhost',  # URL
    r'\d{3,}',  # 3자리 이상 숫자 (에러 코드 등)
]

# Bash 안티패턴 (전용 도구가 있는데 Bash로 실행)
# 정규식: 단독 명령어로 사용된 경우만 탐지 (파이프 앞, 명령 시작)
BASH_ANTIPATTERNS = [
    r'(?<!\w)grep\s',       # grep (git grep은 별도 처리로 제외)
    r'(?<!\w)cat\s+[^<]',   # cat file (cat <<EOF 제외)
    r'(?<!\w)find\s+\.',    # find . (find 명령)
    r'(?<!\w)head\s+-',     # head -n
    r'(?<!\w)tail\s+-',     # tail -n
    r'(?<!\w)sed\s+',       # sed
    r'(?<!\w)awk\s+',       # awk
]
# 안티패턴 제외 (오탐 방지)
BASH_ANTIPATTERN_EXCEPTIONS = [
    r'git\s+grep',          # git grep은 정상 사용
    r'npm\s+run',           # npm 스크립트
    r'cat\s*<<',            # heredoc
    r'grep.*node_modules',  # node_modules 검색은 Bash가 적절
]


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
            # subagents 디렉토리 제외
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
                            # timestamp가 없으면 다음 줄 시도
                            continue
                        session_date = parse_timestamp(timestamp)
                        if start_date <= session_date <= end_date:
                            session_files.append(jsonl_file)
                        break
            except Exception:
                continue

    return sorted(session_files)


def parse_session_enhanced(file_path: Path) -> Dict[str, Any]:
    """세션 파일을 점수 계산에 필요한 형태로 파싱"""
    data = {
        'user_messages': [],       # 사용자 텍스트 메시지
        'tool_uses': [],           # tool_use (assistant가 호출)
        'tool_results': [],        # tool_result (결과)
        'total_messages': 0,
        'total_user_messages': 0,
        'total_assistant_messages': 0,
        'edit_write_files': Counter(),  # file_path → 수정 횟수
        'bash_commands': [],       # Bash 명령어 목록
        'has_task_calls': [],      # Task(sub agent) 호출 목록
        'has_skill_calls': [],     # Skill 호출 목록
        'has_compact': False,
        'has_git_commit_bash': False,
        'tool_sequence': [],       # 도구 호출 순서
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
                        # 순수 사용자 텍스트 메시지
                        if content.strip():
                            data['user_messages'].append(content.strip())
                            data['total_user_messages'] += 1
                            # /compact 탐지
                            if '/compact' in content:
                                data['has_compact'] = True
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
                                    has_text = True
                                    if '/compact' in text:
                                        data['has_compact'] = True

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

                            if item_type == 'tool_use':
                                tool_name = item.get('name', '')
                                tool_input = item.get('input', {})
                                data['tool_uses'].append({
                                    'name': tool_name,
                                    'input': tool_input,
                                    'id': item.get('id', ''),
                                })
                                data['tool_sequence'].append(tool_name)

                                # Edit/Write 파일 추적
                                if tool_name in ('Edit', 'Write'):
                                    fp = tool_input.get('file_path', '')
                                    if fp:
                                        data['edit_write_files'][fp] += 1

                                # Bash 명령어 추적
                                if tool_name == 'Bash':
                                    cmd = tool_input.get('command', '')
                                    if cmd:
                                        data['bash_commands'].append(cmd)
                                        if 'git commit' in cmd:
                                            data['has_git_commit_bash'] = True

                                # Task (Sub Agent) 추적
                                if tool_name == 'Task':
                                    data['has_task_calls'].append({
                                        'subagent_type': tool_input.get('subagent_type', ''),
                                        'description': tool_input.get('description', ''),
                                    })

                                    # Skill 추적
                                if tool_name == 'Skill':
                                    data['has_skill_calls'].append({
                                        'skill': tool_input.get('skill', ''),
                                    })

                                # TodoWrite는 무시 (도구 시퀀스에만 포함)

    except Exception as e:
        print(f"파싱 실패: {file_path} - {e}", file=sys.stderr)

    return data


def classify_complexity(sessions: List[Dict]) -> str:
    """전체 세션의 작업 복잡도 분류"""
    total_files = 0
    total_tools = 0
    total_messages = 0

    for s in sessions:
        total_files += len(s['edit_write_files'])
        total_tools += len(s['tool_uses'])
        total_messages += s['total_user_messages']

    avg_files = total_files / len(sessions) if sessions else 0
    avg_tools = total_tools / len(sessions) if sessions else 0
    avg_msgs = total_messages / len(sessions) if sessions else 0

    # 세션 평균 기준으로 판단
    if avg_files > 10 or avg_tools > 50 or avg_msgs > 30:
        return '중량급'
    elif avg_files >= 3 or avg_tools >= 15 or avg_msgs >= 10:
        return '중량'
    else:
        return '경량'


def calc_intent_score(sessions: List[Dict]) -> Tuple[int, Dict]:
    """의도 전달력 (25점)"""
    details = {}

    # 1. 수정 지시 비율 (15점)
    total_user_msgs = 0
    correction_msgs = 0
    for s in sessions:
        for msg in s['user_messages']:
            total_user_msgs += 1
            msg_lower = msg.lower()
            if any(kw in msg_lower for kw in CORRECTION_KEYWORDS):
                correction_msgs += 1

    if total_user_msgs > 0:
        ratio = correction_msgs / total_user_msgs
    else:
        ratio = 0

    if ratio <= 0.10:
        correction_score = 15
    elif ratio <= 0.25:
        correction_score = 10
    else:
        correction_score = 5

    details['correction_ratio'] = round(ratio * 100, 1)
    details['correction_score'] = correction_score

    # 2. 초기 컨텍스트 (5점)
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

    # 3. 방향 일관성 (5점)
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

    total = correction_score + context_score + consistency_score
    return total, details


def calc_efficiency_score(sessions: List[Dict]) -> Tuple[int, Dict]:
    """작업 효율성 (30점)"""
    details = {}

    # 1. 재작업 비율 (10점)
    all_files = Counter()
    for s in sessions:
        for fp, count in s['edit_write_files'].items():
            all_files[fp] += count

    total_files = len(all_files)
    rework_files = sum(1 for count in all_files.values() if count >= 3)

    if total_files == 0:
        rework_score = 10  # 해당 없음 → 만점
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

    # 2. 도구 성공률 (10점)
    total_results = 0
    error_results = 0
    for s in sessions:
        for tr in s['tool_results']:
            total_results += 1
            if tr['is_error']:
                error_results += 1

    if total_results > 0:
        success_rate = (total_results - error_results) / total_results
    else:
        success_rate = 1.0

    if success_rate >= 0.90:
        success_score = 10
    elif success_rate >= 0.70:
        success_score = 7
    else:
        success_score = 4

    details['success_rate'] = round(success_rate * 100, 1)
    details['success_score'] = success_score

    # 3. 작업 완결 (10점)
    completion_found = False
    for s in sessions:
        msgs = s['user_messages']
        if msgs:
            # 후반 30% 메시지 확인
            tail_start = max(0, len(msgs) - max(1, len(msgs) * 30 // 100))
            tail_msgs = msgs[tail_start:]
            for msg in tail_msgs:
                if any(kw in msg.lower() for kw in COMPLETION_KEYWORDS):
                    completion_found = True
                    break
        if completion_found:
            break

    completion_score = 10 if completion_found else 7
    details['completion_score'] = completion_score
    details['completion_found'] = completion_found

    total = rework_score + success_score + completion_score
    return total, details


def calc_tool_fitness_score(sessions: List[Dict], complexity: str) -> Tuple[int, Dict]:
    """도구 적합성 (25점)"""
    details = {}

    # 1. 전용 도구 우선 사용 (10점)
    antipattern_count = 0
    for s in sessions:
        for cmd in s['bash_commands']:
            is_antipattern = False
            for pattern in BASH_ANTIPATTERNS:
                if re.search(pattern, cmd):
                    is_antipattern = True
                    break
            if is_antipattern:
                # 예외 패턴 확인 (오탐 제거)
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

    # 2. 규모 대비 위임 적절성 (10점)
    has_agents = any(len(s['has_task_calls']) > 0 for s in sessions)
    agent_types = set()
    for s in sessions:
        for tc in s['has_task_calls']:
            agent_types.add(tc['subagent_type'])

    if complexity == '경량':
        delegation_score = 10 if not has_agents else 7
    elif complexity == '중량':
        delegation_score = 10 if has_agents else 7
    else:  # 중량급
        if has_agents:
            delegation_score = 10
        else:
            delegation_score = 5

    details['has_agents'] = has_agents
    details['agent_types'] = list(agent_types)
    details['delegation_score'] = delegation_score

    # 3. 변경 후 검증 (5점)
    total_edits = sum(len(s['tool_uses']) for s in sessions
                      if any(t['name'] in ('Edit', 'Write') for t in s['tool_uses']))
    edit_count = sum(1 for s in sessions for t in s['tool_uses'] if t['name'] in ('Edit', 'Write'))

    has_verification = False
    for s in sessions:
        seq = s['tool_sequence']
        for i, name in enumerate(seq):
            if name in ('Edit', 'Write'):
                # 이후에 Bash가 나오는지 확인
                remaining = seq[i + 1:i + 5]
                if 'Bash' in remaining:
                    has_verification = True
                    break
        if has_verification:
            break

    if edit_count >= 5:
        verify_score = 5 if has_verification else 2
    else:
        verify_score = 5  # 소규모 수정은 자동 만점

    details['edit_count'] = edit_count
    details['has_verification'] = has_verification
    details['verify_score'] = verify_score

    total = tool_pref_score + delegation_score + verify_score
    return total, details


def calc_workflow_score(sessions: List[Dict], complexity: str) -> Tuple[int, Dict]:
    """워크플로우 성숙도 (20점)"""
    details = {}

    # 1. 반복 작업 자동화 (7점)
    has_git_commit = any(s['has_git_commit_bash'] for s in sessions)
    # Skill tool_use 또는 사용자 메시지에서 /commit, /granular-commit 탐지
    has_commit_skill = any(
        tc['skill'] in ('commit', 'granular-commit')
        for s in sessions for tc in s['has_skill_calls']
    )
    # 사용자 메시지에서 슬래시 커맨드 탐지 (Skill tool이 아닌 경우에도)
    if not has_commit_skill:
        for s in sessions:
            for msg in s['user_messages']:
                if re.search(r'(?:^|[\s])/(commit|granular-commit)\b', msg):
                    has_commit_skill = True
                    break
            if has_commit_skill:
                break

    has_other_skills = any(len(s['has_skill_calls']) > 0 for s in sessions)
    # 사용자 메시지에서 기타 스킬 커맨드 탐지
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
        auto_score = 7  # 해당 없음 → 만점

    details['has_git_commit'] = has_git_commit
    details['has_commit_skill'] = has_commit_skill
    details['auto_score'] = auto_score

    # 2. 에러 적응력 (7점)
    same_error_retries = 0
    for s in sessions:
        tool_uses = s['tool_uses']
        results = s['tool_results']

        # tool_use id와 tool_result tool_use_id를 매칭하여 실패 탐지
        failed_ids = {tr['tool_use_id'] for tr in results if tr['is_error']}

        consecutive_fails = 0
        prev_failed_name = None
        for tu in tool_uses:
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

    # 3. 컨텍스트 관리 (6점)
    has_compact = any(s['has_compact'] for s in sessions)

    if complexity in ('경량', '중량'):
        context_score = 6  # 자동 만점
    else:  # 중량급
        context_score = 6 if has_compact else 3

    details['has_compact'] = has_compact
    details['context_score'] = context_score

    total = auto_score + error_adapt_score + context_score
    return total, details


def get_grade(score: int) -> Tuple[str, str]:
    """점수 → 등급"""
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
    """점수 비율 → 평가 텍스트"""
    ratio = score / max_score if max_score > 0 else 0
    if ratio >= 0.8:
        return '우수'
    elif ratio >= 0.6:
        return '양호'
    elif ratio >= 0.4:
        return '보통'
    else:
        return '미흡'


def generate_feedback(intent_details, efficiency_details, fitness_details, workflow_details, complexity):
    """잘한 점 / 개선 포인트 생성"""
    good_points = []
    improve_points = []

    # 의도 전달력
    if intent_details['correction_score'] >= 13:
        good_points.append("명확한 의도 전달로 수정 지시가 거의 없었습니다")
    elif intent_details['correction_score'] <= 5:
        improve_points.append(f"수정 지시 비율이 {intent_details['correction_ratio']}%입니다. 초기 지시를 더 구체적으로 작성하면 재작업이 줄어듭니다")

    if intent_details['context_score'] >= 4:
        good_points.append("첫 메시지에서 충분한 컨텍스트를 제공했습니다")

    # 작업 효율성
    if efficiency_details['rework_score'] >= 8:
        if efficiency_details['rework_ratio'] == 0 and sum(1 for s in [] for _ in []) == 0:
            pass  # 파일 수정 없으면 언급 안 함
        else:
            good_points.append("파일 수정을 한번에 정확하게 수행하여 재작업이 적었습니다")
    elif efficiency_details['rework_score'] <= 5:
        improve_points.append(f"재작업 비율이 {efficiency_details['rework_ratio']}%입니다. 수정 전 파일을 먼저 Read로 확인하면 재작업을 줄일 수 있습니다")

    if efficiency_details['success_score'] >= 8:
        good_points.append(f"도구 호출 성공률이 {efficiency_details['success_rate']}%로 높습니다")
    elif efficiency_details['success_score'] <= 5:
        improve_points.append(f"도구 호출 성공률이 {efficiency_details['success_rate']}%입니다. 호출 전 입력을 더 정확하게 준비하면 효율이 높아집니다")

    # 도구 적합성
    if fitness_details['tool_pref_score'] >= 8:
        good_points.append("전용 도구를 적절히 사용하여 Bash 의존도가 낮았습니다")
    elif fitness_details['tool_pref_score'] <= 4:
        improve_points.append(f"Bash에서 grep/cat/find 등을 {fitness_details['bash_antipatterns']}회 사용했습니다. Grep/Read/Glob 전용 도구를 사용하면 더 효율적입니다")

    if complexity == '경량' and not fitness_details['has_agents']:
        good_points.append("소규모 작업을 Sub Agent 없이 빠르게 직접 처리했습니다")
    elif complexity == '중량급' and fitness_details['delegation_score'] >= 8:
        good_points.append("대규모 작업에서 Sub Agent를 적절히 활용하여 효율적으로 위임했습니다")
    elif complexity == '중량급' and fitness_details['delegation_score'] <= 5:
        improve_points.append("대규모 작업에서 Explore/Plan 에이전트를 활용하면 더 효율적으로 탐색/설계할 수 있습니다")

    # 워크플로우 성숙도
    if workflow_details['has_commit_skill']:
        good_points.append("커밋 자동화 스킬을 활용하여 반복 작업을 줄였습니다")
    elif workflow_details['has_git_commit'] and not workflow_details['has_commit_skill']:
        improve_points.append("/commit 또는 /granular-commit 스킬을 활용하면 커밋 작업을 자동화할 수 있습니다")

    if workflow_details['error_adapt_score'] >= 6:
        good_points.append("에러 발생 시 적응적으로 접근법을 변경했습니다")
    elif workflow_details['error_adapt_score'] <= 3:
        improve_points.append("같은 도구로 연속 실패한 경우가 있습니다. 다른 접근법을 시도하면 더 빠르게 해결할 수 있습니다")

    # 최소 1개씩 보장
    if not good_points:
        good_points.append("도구를 활용하여 작업을 수행했습니다")
    if not improve_points:
        improve_points.append("현재 활용도가 높습니다. 새로운 스킬이나 기능을 탐색해보세요")

    return good_points[:4], improve_points[:3]


def analyze_date(target_date: str, projects_dir: str) -> Dict:
    """특정 날짜의 JSONL 로그를 분석하여 점수 계산"""
    date = datetime.strptime(target_date, '%Y-%m-%d')
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

    files = find_session_files(Path(projects_dir), start, end)

    if not files:
        return {'date': target_date, 'error': '세션 없음', 'sessions': 0}

    sessions = []
    for f in files:
        parsed = parse_session_enhanced(f)
        # 최소 필터: 메시지 3개 이상, 도구 1개 이상
        if parsed['total_user_messages'] >= 1 and len(parsed['tool_uses']) >= 1:
            sessions.append(parsed)

    if not sessions:
        return {'date': target_date, 'error': '유효 세션 없음', 'sessions': 0}

    complexity = classify_complexity(sessions)

    intent_score, intent_details = calc_intent_score(sessions)
    efficiency_score, efficiency_details = calc_efficiency_score(sessions)
    fitness_score, fitness_details = calc_tool_fitness_score(sessions, complexity)
    workflow_score, workflow_details = calc_workflow_score(sessions, complexity)

    total = intent_score + efficiency_score + fitness_score + workflow_score
    grade, grade_desc = get_grade(total)

    good_points, improve_points = generate_feedback(
        intent_details, efficiency_details, fitness_details, workflow_details, complexity
    )

    return {
        'date': target_date,
        'sessions': len(sessions),
        'total_files_found': len(files),
        'complexity': complexity,
        'total_score': total,
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
    }


def main():
    parser = argparse.ArgumentParser(description='활용도 평가 점수 계산기')
    parser.add_argument('--date', type=str, help='분석할 날짜 (YYYY-MM-DD)')
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'))
    parser.add_argument('--projects-dir', type=str,
                        default=os.path.expanduser('~/.claude/projects'))

    args = parser.parse_args()

    if args.date:
        result = analyze_date(args.date, args.projects_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.date_range:
        start = datetime.strptime(args.date_range[0], '%Y-%m-%d')
        end = datetime.strptime(args.date_range[1], '%Y-%m-%d')

        results = []
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            result = analyze_date(date_str, args.projects_dir)
            if 'error' not in result:
                results.append(result)
            else:
                print(f"  {date_str}: {result.get('error', '?')}", file=sys.stderr)
            current += __import__('datetime').timedelta(days=1)

        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
