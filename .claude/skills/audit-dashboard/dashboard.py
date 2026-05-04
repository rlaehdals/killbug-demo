#!/usr/bin/env python3
"""감사 로그 → HTML 대시보드 생성."""

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def load_entries(audit_dir, days=None):
    entries = []
    blocked = []
    cutoff = None
    if days:
        cutoff = datetime.now() - timedelta(days=days)

    for f in sorted(Path(audit_dir).glob("*.jsonl")):
        is_blocked = f.name == "blocked.jsonl"
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if cutoff:
                    ts = entry.get("ts", "")
                    try:
                        if datetime.fromisoformat(ts) < cutoff:
                            continue
                    except ValueError:
                        pass
                if is_blocked:
                    blocked.append(entry)
                else:
                    entries.append(entry)
    return entries, blocked


def analyze(entries, blocked):
    stats = {}

    # 기본 통계
    stats["total_calls"] = len(entries)
    stats["total_blocked"] = len(blocked)
    stats["sessions"] = len(set(e.get("session", "") for e in entries))

    # 일별 호출 수
    daily = Counter()
    for e in entries:
        ts = e.get("ts", "")[:10]
        if ts:
            daily[ts] += 1
    stats["daily"] = dict(sorted(daily.items()))

    # 도구별 호출 수
    tool_counts = Counter(e.get("tool", "unknown") for e in entries)
    stats["tools"] = dict(tool_counts.most_common(15))

    # 세션별 호출 수
    session_counts = Counter(e.get("session", "unknown") for e in entries)
    stats["sessions_detail"] = dict(session_counts.most_common(10))

    # 차단 사유
    block_reasons = Counter()
    block_hooks = Counter()
    for b in blocked:
        reason = b.get("reason", "unknown")
        if len(reason) > 80:
            reason = reason[:80] + "..."
        block_reasons[reason] += 1
        block_hooks[b.get("hook", "unknown")] += 1
    stats["block_reasons"] = dict(block_reasons.most_common(10))
    stats["block_hooks"] = dict(block_hooks.most_common())

    # 시간대별 활동 (0-23시)
    hourly = Counter()
    for e in entries:
        ts = e.get("ts", "")
        try:
            hour = datetime.fromisoformat(ts).hour
            hourly[hour] += 1
        except (ValueError, IndexError):
            pass
    stats["hourly"] = {str(h): hourly.get(h, 0) for h in range(24)}

    # 차단된 도구
    blocked_tools = Counter(b.get("tool", "unknown") for b in blocked)
    stats["blocked_tools"] = dict(blocked_tools.most_common())

    return stats


def bar(value, max_value, width=200):
    if max_value == 0:
        return ""
    pct = value / max_value * 100
    return f'<div style="background:#3b82f6;height:18px;width:{pct / 100 * width}px;border-radius:3px;display:inline-block"></div>'


def bar_red(value, max_value, width=200):
    if max_value == 0:
        return ""
    pct = value / max_value * 100
    return f'<div style="background:#ef4444;height:18px;width:{pct / 100 * width}px;border-radius:3px;display:inline-block"></div>'


def summarize_input(raw_input):
    """입력 JSON에서 표시용 요약 문자열을 추출한다."""
    try:
        obj = json.loads(raw_input)
    except (json.JSONDecodeError, TypeError):
        s = str(raw_input)
        return s[:120] + "..." if len(s) > 120 else s

    # Bash: command or description
    if "command" in obj:
        cmd = obj["command"]
        desc = obj.get("description", "")
        label = desc if desc else cmd
        return label[:120] + "..." if len(label) > 120 else label
    # Read: file_path
    if "file_path" in obj:
        return obj["file_path"].split("/")[-1]
    # Edit: file_path
    if "old_string" in obj:
        fp = obj.get("file_path", "")
        return f"edit {fp.split('/')[-1]}"
    # Write
    if "content" in obj and "file_path" in obj:
        return f"write {obj['file_path'].split('/')[-1]}"
    # Grep
    if "pattern" in obj:
        return f"grep '{obj['pattern']}'"
    # Glob
    if "pattern" in obj:
        return f"glob '{obj['pattern']}'"
    # Agent
    if "prompt" in obj:
        desc = obj.get("description", obj["prompt"][:60])
        return desc[:120] + "..." if len(desc) > 120 else desc

    s = str(obj)
    return s[:120] + "..." if len(s) > 120 else s


def prepare_embed_data(entries, blocked):
    """HTML에 임베드할 경량 데이터를 준비한다."""
    compact_entries = []
    for e in entries:
        compact_entries.append({
            "ts": e.get("ts", "")[:19],
            "session": e.get("session", ""),
            "tool": e.get("tool", ""),
            "summary": summarize_input(e.get("input", "")),
        })
    compact_blocked = []
    for b in blocked:
        compact_blocked.append({
            "ts": b.get("ts", "")[:19],
            "hook": b.get("hook", ""),
            "tool": b.get("tool", ""),
            "reason": b.get("reason", ""),
            "summary": summarize_input(b.get("input", "")),
        })
    return compact_entries, compact_blocked


def generate_html(stats, output_path, entries, blocked):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    compact_entries, compact_blocked = prepare_embed_data(entries, blocked)

    # JSON 데이터 임베드
    entries_json = json.dumps(compact_entries, ensure_ascii=False)
    blocked_json = json.dumps(compact_blocked, ensure_ascii=False)

    # 도구별 테이블
    tool_max = max(stats["tools"].values()) if stats["tools"] else 1
    tool_rows = ""
    for tool, count in stats["tools"].items():
        tool_rows += f'<tr class="clickable" onclick="drilldown(\'tool\',\'{tool}\')" title="클릭하여 상세 보기"><td>{tool}</td><td>{count}</td><td>{bar(count, tool_max)}</td></tr>\n'

    # 일별 테이블
    daily_max = max(stats["daily"].values()) if stats["daily"] else 1
    daily_rows = ""
    for date, count in stats["daily"].items():
        daily_rows += f'<tr class="clickable" onclick="drilldown(\'date\',\'{date}\')" title="클릭하여 상세 보기"><td>{date}</td><td>{count}</td><td>{bar(count, daily_max)}</td></tr>\n'

    # 시간대별 테이블
    hourly_max = max(int(v) for v in stats["hourly"].values()) if stats["hourly"] else 1
    hourly_rows = ""
    for h in range(24):
        count = stats["hourly"].get(str(h), 0)
        hourly_rows += f'<tr class="clickable" onclick="drilldown(\'hour\',\'{h}\')" title="클릭하여 상세 보기"><td>{h:02d}:00</td><td>{count}</td><td>{bar(count, hourly_max)}</td></tr>\n'

    # 차단 사유 테이블
    block_max = max(stats["block_reasons"].values()) if stats["block_reasons"] else 1
    block_rows = ""
    for idx, (reason, count) in enumerate(stats["block_reasons"].items()):
        block_rows += f'<tr class="clickable" onclick="drilldownBlocked(\'reason\',{idx})" title="클릭하여 상세 보기"><td style="max-width:400px;overflow:hidden;text-overflow:ellipsis">{reason}</td><td>{count}</td><td>{bar_red(count, block_max)}</td></tr>\n'

    # 차단 훅 테이블
    hook_max = max(stats["block_hooks"].values()) if stats["block_hooks"] else 1
    hook_rows = ""
    for hook, count in stats["block_hooks"].items():
        hook_rows += f'<tr class="clickable" onclick="drilldownBlocked(\'hook\',\'{hook}\')" title="클릭하여 상세 보기"><td>{hook}</td><td>{count}</td><td>{bar_red(count, hook_max)}</td></tr>\n'

    # 차단된 도구 테이블
    bt_max = max(stats["blocked_tools"].values()) if stats["blocked_tools"] else 1
    bt_rows = ""
    for tool, count in stats["blocked_tools"].items():
        bt_rows += f'<tr class="clickable" onclick="drilldownBlocked(\'tool\',\'{tool}\')" title="클릭하여 상세 보기"><td>{tool}</td><td>{count}</td><td>{bar_red(count, bt_max)}</td></tr>\n'

    # 세션별 테이블
    session_max = max(stats["sessions_detail"].values()) if stats["sessions_detail"] else 1
    session_rows = ""
    for sid, count in stats["sessions_detail"].items():
        session_rows += f'<tr class="clickable" onclick="drilldown(\'session\',\'{sid}\')" title="클릭하여 상세 보기"><td>{sid}</td><td>{count}</td><td>{bar(count, session_max)}</td></tr>\n'

    # 차단 사유 목록 (JS에서 인덱스로 접근)
    block_reason_keys = json.dumps(list(stats["block_reasons"].keys()), ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>KillBug Harness Audit Dashboard</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; padding: 24px; }}
  h1 {{ font-size: 24px; margin-bottom: 8px; color: #f8fafc; }}
  .meta {{ color: #94a3b8; margin-bottom: 24px; font-size: 14px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
  .card {{ background: #1e293b; border-radius: 8px; padding: 20px; }}
  .card .label {{ color: #94a3b8; font-size: 13px; margin-bottom: 4px; }}
  .card .value {{ font-size: 28px; font-weight: 700; color: #f8fafc; }}
  .card .value.red {{ color: #ef4444; }}
  .section {{ background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 16px; }}
  .section h2 {{ font-size: 16px; margin-bottom: 12px; color: #f8fafc; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; color: #94a3b8; font-size: 12px; font-weight: 600; padding: 6px 8px; border-bottom: 1px solid #334155; }}
  td {{ padding: 6px 8px; font-size: 13px; border-bottom: 1px solid #1e293b; vertical-align: middle; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .clickable {{ cursor: pointer; transition: background 0.15s; }}
  .clickable:hover {{ background: #334155; }}

  /* 드릴다운 패널 */
  .panel-overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 100; }}
  .panel-overlay.open {{ display: flex; justify-content: center; align-items: start; padding-top: 60px; }}
  .panel {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; width: 800px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 25px 50px rgba(0,0,0,0.5); }}
  .panel-header {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #334155; }}
  .panel-header h3 {{ font-size: 15px; color: #f8fafc; }}
  .panel-close {{ background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer; padding: 4px 8px; border-radius: 4px; }}
  .panel-close:hover {{ background: #334155; color: #f8fafc; }}
  .panel-body {{ overflow-y: auto; padding: 12px 20px 20px; }}
  .panel-body table {{ font-size: 12px; }}
  .panel-body th {{ position: sticky; top: 0; background: #1e293b; }}
  .panel-body td {{ padding: 5px 8px; white-space: nowrap; }}
  .panel-body td.wrap {{ white-space: normal; word-break: break-all; max-width: 400px; }}
  .panel-summary {{ display: flex; gap: 16px; padding: 12px 20px; border-bottom: 1px solid #334155; }}
  .panel-stat {{ font-size: 12px; color: #94a3b8; }}
  .panel-stat strong {{ color: #f8fafc; font-size: 14px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .badge-blue {{ background: #1e3a5f; color: #60a5fa; }}
  .badge-red {{ background: #3b1420; color: #f87171; }}
</style>
</head>
<body>
<h1>Harness Audit Dashboard</h1>
<p class="meta">Generated: {now} | KillBug &mdash; 행을 클릭하면 상세 내역을 볼 수 있습니다</p>

<div class="grid">
  <div class="card"><div class="label">Total Calls</div><div class="value">{stats['total_calls']}</div></div>
  <div class="card"><div class="label">Blocked</div><div class="value red">{stats['total_blocked']}</div></div>
  <div class="card"><div class="label">Sessions</div><div class="value">{stats['sessions']}</div></div>
  <div class="card"><div class="label">Block Rate</div><div class="value red">{stats['total_blocked'] / max(stats['total_calls'], 1) * 100:.1f}%</div></div>
</div>

<div class="two-col">
  <div class="section">
    <h2>Tool Usage</h2>
    <table><tr><th>Tool</th><th>Count</th><th></th></tr>{tool_rows}</table>
  </div>
  <div class="section">
    <h2>Daily Activity</h2>
    <table><tr><th>Date</th><th>Count</th><th></th></tr>{daily_rows}</table>
  </div>
</div>

<div class="section">
  <h2>Hourly Activity</h2>
  <table><tr><th>Hour</th><th>Count</th><th></th></tr>{hourly_rows}</table>
</div>

<div class="two-col">
  <div class="section">
    <h2>Blocked &mdash; By Hook</h2>
    <table><tr><th>Hook</th><th>Count</th><th></th></tr>{hook_rows}</table>
  </div>
  <div class="section">
    <h2>Blocked &mdash; By Tool</h2>
    <table><tr><th>Tool</th><th>Count</th><th></th></tr>{bt_rows}</table>
  </div>
</div>

<div class="section">
  <h2>Block Reasons</h2>
  <table><tr><th>Reason</th><th>Count</th><th></th></tr>{block_rows}</table>
</div>

<div class="section">
  <h2>Sessions (Top 10)</h2>
  <table><tr><th>Session</th><th>Calls</th><th></th></tr>{session_rows}</table>
</div>

<!-- 드릴다운 패널 -->
<div class="panel-overlay" id="panelOverlay" onclick="if(event.target===this)closePanel()">
  <div class="panel">
    <div class="panel-header">
      <h3 id="panelTitle"></h3>
      <button class="panel-close" onclick="closePanel()">&times;</button>
    </div>
    <div class="panel-summary" id="panelSummary"></div>
    <div class="panel-body" id="panelBody"></div>
  </div>
</div>

<script>
const ENTRIES = {entries_json};
const BLOCKED = {blocked_json};
const BLOCK_REASON_KEYS = {block_reason_keys};

function closePanel() {{
  document.getElementById('panelOverlay').classList.remove('open');
}}
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closePanel(); }});

function renderEntryTable(items, maxRows) {{
  if (!items.length) return '<p style="color:#64748b;padding:12px 0">데이터 없음</p>';
  const limited = items.slice(0, maxRows || 100);
  let html = '<table><tr><th>Time</th><th>Session</th><th>Tool</th><th>Summary</th></tr>';
  for (const e of limited) {{
    html += `<tr>
      <td>${{e.ts.substring(11)}}</td>
      <td>${{e.session}}</td>
      <td><span class="badge badge-blue">${{e.tool}}</span></td>
      <td class="wrap">${{escHtml(e.summary)}}</td>
    </tr>`;
  }}
  html += '</table>';
  if (items.length > limited.length) {{
    html += `<p style="color:#64748b;font-size:12px;padding:8px 0">+ ${{items.length - limited.length}}건 더...</p>`;
  }}
  return html;
}}

function renderBlockedTable(items) {{
  if (!items.length) return '<p style="color:#64748b;padding:12px 0">데이터 없음</p>';
  let html = '<table><tr><th>Time</th><th>Hook</th><th>Tool</th><th>Reason</th><th>Input</th></tr>';
  for (const b of items) {{
    html += `<tr>
      <td>${{b.ts.substring(11)}}</td>
      <td><span class="badge badge-red">${{b.hook}}</span></td>
      <td>${{b.tool}}</td>
      <td class="wrap">${{escHtml(b.reason)}}</td>
      <td class="wrap">${{escHtml(b.summary)}}</td>
    </tr>`;
  }}
  html += '</table>';
  return html;
}}

function toolBreakdown(items) {{
  const counts = {{}};
  items.forEach(e => {{ counts[e.tool] = (counts[e.tool] || 0) + 1; }});
  return Object.entries(counts).sort((a,b) => b[1]-a[1]);
}}

function drilldown(filterType, filterValue) {{
  let filtered = [];
  let title = '';

  if (filterType === 'tool') {{
    filtered = ENTRIES.filter(e => e.tool === filterValue);
    title = `Tool: ${{filterValue}}`;
  }} else if (filterType === 'date') {{
    filtered = ENTRIES.filter(e => e.ts.startsWith(filterValue));
    title = `Date: ${{filterValue}}`;
  }} else if (filterType === 'hour') {{
    const h = parseInt(filterValue);
    filtered = ENTRIES.filter(e => {{
      const parts = e.ts.split('T');
      if (parts.length < 2) return false;
      const hour = parseInt(parts[1].split(':')[0]);
      return hour === h;
    }});
    title = `Hour: ${{String(h).padStart(2,'0')}}:00 ~ ${{String(h).padStart(2,'0')}}:59`;
  }} else if (filterType === 'session') {{
    filtered = ENTRIES.filter(e => e.session === filterValue);
    title = `Session: ${{filterValue}}`;
  }}

  // 요약 통계
  const breakdown = toolBreakdown(filtered);
  let summaryHtml = `<div class="panel-stat"><strong>${{filtered.length}}</strong> calls</div>`;
  const top3 = breakdown.slice(0, 3).map(([t,c]) => `${{t}} ${{c}}`).join(', ');
  if (top3) summaryHtml += `<div class="panel-stat">Top: <strong>${{top3}}</strong></div>`;

  document.getElementById('panelTitle').textContent = title;
  document.getElementById('panelSummary').innerHTML = summaryHtml;
  document.getElementById('panelBody').innerHTML = renderEntryTable(filtered, 100);
  document.getElementById('panelOverlay').classList.add('open');
}}

function drilldownBlocked(filterType, filterValue) {{
  let filtered = [];
  let title = '';

  if (filterType === 'hook') {{
    filtered = BLOCKED.filter(b => b.hook === filterValue);
    title = `Blocked by Hook: ${{filterValue}}`;
  }} else if (filterType === 'tool') {{
    filtered = BLOCKED.filter(b => b.tool === filterValue);
    title = `Blocked Tool: ${{filterValue}}`;
  }} else if (filterType === 'reason') {{
    const reasonKey = BLOCK_REASON_KEYS[filterValue];
    filtered = BLOCKED.filter(b => {{
      const r = b.reason.length > 80 ? b.reason.substring(0,80) + '...' : b.reason;
      return r === reasonKey || b.reason.startsWith(reasonKey.replace('...',''));
    }});
    title = `Block Reason`;
  }}

  const summaryHtml = `<div class="panel-stat"><strong>${{filtered.length}}</strong> blocked</div>`;

  document.getElementById('panelTitle').textContent = title;
  document.getElementById('panelSummary').innerHTML = summaryHtml;
  document.getElementById('panelBody').innerHTML = renderBlockedTable(filtered);
  document.getElementById('panelOverlay').classList.add('open');
}}

function escHtml(s) {{
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}}
</script>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Audit log dashboard generator")
    parser.add_argument("--days", type=int, default=None, help="Analyze last N days only")
    args = parser.parse_args()

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    audit_dir = os.path.join(project_dir, ".private", "audit")

    if not os.path.exists(audit_dir):
        print("감사 로그 디렉토리가 없습니다: .private/audit/")
        return

    entries, blocked = load_entries(audit_dir, args.days)
    if not entries and not blocked:
        print("감사 로그가 비어있습니다.")
        return

    stats = analyze(entries, blocked)
    output = os.path.join(audit_dir, "dashboard.html")
    generate_html(stats, output, entries, blocked)

    period = f"최근 {args.days}일" if args.days else "전체 기간"
    print(f"대시보드 생성 완료 ({period})")
    print(f"  호출: {stats['total_calls']}건 | 차단: {stats['total_blocked']}건 | 세션: {stats['sessions']}개")
    print(f"  파일: {output}")


if __name__ == "__main__":
    main()
