#!/usr/bin/env python3
"""
JSONL 세션 로그 파싱 유틸리티

사용법:
    python parse_jsonl.py --date 2026-02-11
    python parse_jsonl.py --date-range 2026-02-01 2026-02-11
    python parse_jsonl.py --file /path/to/session.jsonl
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os


def parse_timestamp(timestamp_str: str) -> datetime:
    """ISO 8601 타임스탬프를 datetime으로 변환"""
    try:
        # 다양한 형식 지원
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
        # fromisoformat 시도
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except Exception as e:
        print(f"타임스탬프 파싱 실패: {timestamp_str} - {e}", file=sys.stderr)
        return datetime.now()


def find_session_files(projects_dir: Path, start_date: datetime, end_date: datetime) -> List[Path]:
    """날짜 범위에 해당하는 JSONL 파일 찾기"""
    session_files = []

    # 모든 프로젝트 디렉토리 탐색
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # JSONL 파일 찾기
        for jsonl_file in project_dir.glob("*.jsonl"):
            # 첫 줄에서 타임스탬프 추출
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if not first_line.strip():
                        continue

                    first_obj = json.loads(first_line)
                    timestamp = first_obj.get('timestamp')
                    if not timestamp:
                        continue

                    session_date = parse_timestamp(timestamp)

                    # 날짜 범위 확인
                    if start_date <= session_date <= end_date:
                        session_files.append(jsonl_file)
            except Exception as e:
                print(f"파일 스캔 실패: {jsonl_file} - {e}", file=sys.stderr)
                continue

    return sorted(session_files)


def parse_session_file(file_path: Path) -> Dict[str, Any]:
    """JSONL 파일 파싱하여 구조화된 데이터 반환"""
    session_data = {
        'file_path': str(file_path),
        'metadata': {},
        'messages': [],
        'tool_calls': [],
        'thinking_blocks': [],
        'raw_lines': [],
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                    session_data['raw_lines'].append(obj)

                    # 메타데이터 추출 (첫 줄)
                    if line_num == 1:
                        session_data['metadata'] = {
                            'timestamp': obj.get('timestamp'),
                            'sessionId': obj.get('sessionId'),
                        }

                    # 메시지 추출
                    if obj.get('type') in ['user', 'assistant']:
                        session_data['messages'].append({
                            'type': obj['type'],
                            'content': obj.get('content', ''),
                            'timestamp': obj.get('timestamp'),
                        })

                    # 도구 호출 추출
                    if obj.get('type') == 'tool_use':
                        session_data['tool_calls'].append({
                            'name': obj.get('name'),
                            'input': obj.get('input', {}),
                        })

                    # Thinking 블록 추출
                    content = obj.get('content', [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get('type') == 'thinking':
                                session_data['thinking_blocks'].append(item.get('text', ''))

                except json.JSONDecodeError as e:
                    print(f"JSON 파싱 실패: {file_path}:{line_num} - {e}", file=sys.stderr)
                    continue

    except Exception as e:
        print(f"파일 읽기 실패: {file_path} - {e}", file=sys.stderr)

    return session_data


def main():
    parser = argparse.ArgumentParser(description='JSONL 세션 로그 파싱 유틸리티')
    parser.add_argument('--date', type=str, help='분석할 날짜 (YYYY-MM-DD)')
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'),
                        help='날짜 범위 (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--file', type=str, help='특정 파일 파싱')
    parser.add_argument('--projects-dir', type=str,
                        default=os.path.expanduser('~/.claude/projects'),
                        help='프로젝트 디렉토리 (기본: ~/.claude/projects)')
    parser.add_argument('--output', type=str, choices=['json', 'summary'],
                        default='json', help='출력 형식')

    args = parser.parse_args()

    # 특정 파일 파싱
    if args.file:
        session_data = parse_session_file(Path(args.file))
        print(json.dumps(session_data, ensure_ascii=False, indent=2))
        return

    # 날짜 범위 설정
    if args.date:
        date = datetime.strptime(args.date, '%Y-%m-%d')
        start_date = date.replace(hour=0, minute=0, second=0)
        end_date = date.replace(hour=23, minute=59, second=59)
    elif args.date_range:
        start_date = datetime.strptime(args.date_range[0], '%Y-%m-%d')
        end_date = datetime.strptime(args.date_range[1], '%Y-%m-%d').replace(
            hour=23, minute=59, second=59)
    else:
        # 기본: 오늘
        today = datetime.now()
        start_date = today.replace(hour=0, minute=0, second=0)
        end_date = today.replace(hour=23, minute=59, second=59)

    # 세션 파일 찾기
    projects_dir = Path(args.projects_dir)
    session_files = find_session_files(projects_dir, start_date, end_date)

    if not session_files:
        print(f"선택한 기간에 세션이 없습니다: {start_date.date()} ~ {end_date.date()}",
              file=sys.stderr)
        sys.exit(1)

    # 모든 세션 파싱
    all_sessions = []
    for file_path in session_files:
        session_data = parse_session_file(file_path)
        all_sessions.append(session_data)

    # 출력
    if args.output == 'json':
        print(json.dumps({
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            },
            'total_sessions': len(all_sessions),
            'sessions': all_sessions,
        }, ensure_ascii=False, indent=2))
    elif args.output == 'summary':
        print(f"총 세션 수: {len(all_sessions)}")
        print(f"날짜 범위: {start_date.date()} ~ {end_date.date()}")
        for i, session in enumerate(all_sessions, 1):
            print(f"\n세션 {i}:")
            print(f"  메시지 수: {len(session['messages'])}")
            print(f"  도구 호출 수: {len(session['tool_calls'])}")
            print(f"  Thinking 블록 수: {len(session['thinking_blocks'])}")


if __name__ == '__main__':
    main()
