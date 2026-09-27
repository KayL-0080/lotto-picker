import io
import json
import os
import sys
import webbrowser
from datetime import datetime

# Windows 콘솔 인코딩 대응
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from crawler import HISTORY_JSON, sync_lotto_data
from analyzer import LottoAnalyzer


def get_ball_class(num: int) -> str:
    if 1 <= num <= 10:
        return "yellow"
    elif 11 <= num <= 20:
        return "blue"
    elif 21 <= num <= 30:
        return "red"
    elif 31 <= num <= 40:
        return "gray"
    else:
        return "green"


def print_cli_report(analyzer: LottoAnalyzer, types_data: list):
    """콘솔 터미널에 5가지 유형 추천 결과를 보기 좋게 출력합니다."""
    stats = analyzer.get_summary_statistics()
    next_round = analyzer.next_round
    latest_round = analyzer.latest_round

    print("\n" + "=" * 76)
    print(f"       [LOTTO 6/45] 제 {next_round}회차 대비 정밀 통계 분석 & 5대 추천 유형")
    print("=" * 76)
    print(f" • 분석 데이터: 1회 ~ {latest_round}회 (총 {stats['total_rounds']}회차 전수 분석 완료)")
    print(f" • 역대 평균 총합: {stats['avg_sum']}  |  역대 평균 AC값(산포도): {stats['avg_ac']}")
    
    top_5_hot = ", ".join(f"{item['number']}번({item['count']}회)" for item in stats['top_10_hot'][:5])
    top_5_cold = ", ".join(f"{item['number']}번({item['omission']}주 미출)" for item in stats['top_10_cold'][:5])
    print(f" • 역대 최다 빈출 TOP 5: {top_5_hot}")
    print(f" • 최장기 미출현 TOP 5: {top_5_cold}")
    print("-" * 76)

    type_icons = ["[Type 1]", "[Type 2]", "[Type 3]", "[Type 4]", "[Type 5]"]

    for idx, t in enumerate(types_data):
        icon = type_icons[idx] if idx < len(type_icons) else f"[Type {t['type_id']}]"
        nums_str = "  ".join(f"{n:02d}" for n in t["numbers"])
        m = t["metrics"]
        print(f"\n{icon} {t['name']}")
        print(f"   부제: {t['subtitle']}")
        print(f"   개념: {t['concept']}")
        print(f"   >> 추천 번호: [ {nums_str} ] + 보너스 [{t['bonus']:02d}]")
        print(f"   * 지표: 총합={m['sum']} | 홀짝={m['odd_even']} | 저고={m['high_low']} | AC={m['ac_value']} | 연번={m['consecutive']}쌍")
        print("   * 주요 선정 사유:")
        for r in t["reasons"][:3]:
            print(f"      - {r}")

    print("\n" + "=" * 76)
    print(" (i) 본 분석은 1회부터 최신 회차까지의 실제 당첨 통계/확률 모델에 기초한 결과입니다.")
    print("=" * 76 + "\n")


def generate_html_dashboard(analyzer: LottoAnalyzer, initial_types: list) -> str:
    stats = analyzer.get_summary_statistics()
    next_round = analyzer.next_round
    latest_round = analyzer.latest_round
    last_item = analyzer.history[-1]

    # JSON 데이터 직렬화
    types_json = json.dumps(initial_types, ensure_ascii=False)
    stats_json = json.dumps(stats, ensure_ascii=False)
    last_item_json = json.dumps(last_item, ensure_ascii=False)

    all_freq_json = json.dumps(dict(analyzer.all_freq), ensure_ascii=False)
    recent_30_json = json.dumps(dict(analyzer.recent_30_freq), ensure_ascii=False)
    omission_json = json.dumps(dict(analyzer.current_omission), ensure_ascii=False)
    avg_interval_json = json.dumps(dict(analyzer.avg_interval), ensure_ascii=False)

    max_hot_count = max(item["count"] for item in stats["top_10_hot"])
    max_cold_omission = max(item["omission"] for item in stats["top_10_cold"])

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
  <meta name="mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="로또 5대유형" />
  <meta name="theme-color" content="#0b1120" />
  <title>로또 6/45 제 {next_round}회 5대 유형 추천기 (모바일 최적화)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-color: #0b1120;
      --card-bg: #1e293b;
      --card-border: rgba(255, 255, 255, 0.08);
      --card-inner: rgba(15, 23, 42, 0.6);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.25);
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      
      --ball-size: clamp(38px, 10.5vw, 48px);
      --ball-font: clamp(1rem, 3vw, 1.25rem);
      --mini-ball-size: 28px;
    }}
    
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
      -webkit-tap-highlight-color: transparent;
    }}

    body {{
      background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0b1120 100%);
      color: var(--text-main);
      min-height: 100vh;
      padding: 16px 12px 100px 12px;
      line-height: 1.45;
      overflow-x: hidden;
    }}

    .container {{
      max-width: 680px;
      margin: 0 auto;
    }}

    /* 상단 헤더 */
    header {{
      text-align: center;
      padding: 12px 4px 18px 4px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 5px 12px;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid var(--accent);
      color: var(--accent);
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      margin-bottom: 10px;
    }}
    h1 {{
      font-size: clamp(1.5rem, 5.2vw, 2.1rem);
      font-weight: 900;
      letter-spacing: -0.6px;
      margin-bottom: 6px;
      line-height: 1.25;
      background: linear-gradient(135deg, #ffffff 40%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .subhead {{
      color: var(--text-muted);
      font-size: clamp(0.82rem, 2.6vw, 0.95rem);
      word-break: keep-all;
    }}

    /* 상단 요약 그리드 (모바일 2x2 반응형) */
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin-bottom: 18px;
    }}
    .summary-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 12px 14px;
      box-shadow: 0 4px 14px rgba(0,0,0,0.2);
    }}
    .summary-card.full-width {{
      grid-column: span 2;
    }}
    .summary-card .label {{
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-bottom: 4px;
    }}
    .summary-card .value {{
      font-size: 1.2rem;
      font-weight: 800;
      color: #fff;
    }}
    .summary-card .sub-value {{
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    /* 상단 액션 버튼 (모바일 최적화 그리드) */
    .action-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 18px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 12px 14px;
      border-radius: 12px;
      font-weight: 700;
      font-size: 0.88rem;
      cursor: pointer;
      border: none;
      transition: all 0.15s ease;
      touch-action: manipulation;
    }}
    .btn:active {{
      transform: scale(0.97);
    }}
    .btn-primary {{
      grid-column: span 2;
      background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
      color: #ffffff;
      padding: 14px;
      font-size: 0.98rem;
      box-shadow: 0 4px 16px rgba(56, 189, 248, 0.35);
    }}
    .btn-secondary {{
      background: #1e293b;
      border: 1px solid rgba(255,255,255,0.1);
      color: #f1f5f9;
      font-size: 0.82rem;
      padding: 10px;
    }}

    /* ======================================================== */
    /* 🔥 [핵심] 유형 1, 2, 3, 4, 5 가로 한 줄 뱃지 네비게이션 바 */
    /* ======================================================== */
    .type-pill-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 4px;
      margin: 10px 0 18px 0;
      padding: 4px 2px;
      overflow-x: auto;
      white-space: nowrap;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
    }}
    .type-pill-bar::-webkit-scrollbar {{
      display: none;
    }}
    .pill-btn {{
      flex: 1 1 0px;
      padding: 9px 4px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: var(--text-muted);
      font-size: clamp(0.72rem, 2.4vw, 0.84rem);
      font-weight: 700;
      cursor: pointer;
      text-align: center;
      transition: all 0.2s ease;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }}
    .pill-btn:active {{
      transform: scale(0.95);
    }}
    .pill-btn.active {{
      background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
      color: #0b1120;
      font-weight: 900;
      border-color: #38bdf8;
      box-shadow: 0 2px 10px rgba(56, 189, 248, 0.4);
    }}

    /* 섹션 타이틀 */
    .section-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin: 20px 4px 10px 4px;
    }}
    .section-title {{
      font-size: 1.15rem;
      font-weight: 800;
      display: flex;
      align-items: center;
      gap: 6px;
      color: #fff;
    }}
    .section-tag {{
      font-size: 0.72rem;
      padding: 3px 8px;
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border-radius: 6px;
      font-weight: 700;
    }}

    /* 번호 볼 공통 (모바일 1줄 밀착 배치) */
    .ball-wrap {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: clamp(4px, 1.4vw, 8px);
      padding: 14px 6px;
      margin: 10px 0;
      background: var(--card-inner);
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.04);
    }}
    .ball {{
      width: var(--ball-size);
      height: var(--ball-size);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
      font-size: var(--ball-font);
      color: #ffffff;
      text-shadow: 0 1px 2px rgba(0,0,0,0.6);
      box-shadow: inset 0 -3px 5px rgba(0,0,0,0.35), 0 3px 8px rgba(0,0,0,0.3);
      position: relative;
      flex-shrink: 0;
    }}
    .ball::after {{
      content: '';
      position: absolute;
      top: 4px;
      left: 8px;
      width: 10px;
      height: 6px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.45);
      transform: rotate(-20deg);
    }}
    .ball-yellow {{ background: radial-gradient(circle at 35% 35%, #fbbf24, #b45309); }}
    .ball-blue   {{ background: radial-gradient(circle at 35% 35%, #60a5fa, #1d4ed8); }}
    .ball-red    {{ background: radial-gradient(circle at 35% 35%, #f87171, #b91c1c); }}
    .ball-gray   {{ background: radial-gradient(circle at 35% 35%, #94a3b8, #334155); }}
    .ball-green  {{ background: radial-gradient(circle at 35% 35%, #34d399, #047857); }}
    .ball-bonus  {{
      outline: 2px dashed #f59e0b;
      outline-offset: 2px;
    }}
    .mini-ball {{
      width: var(--mini-ball-size);
      height: var(--mini-ball-size);
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: 800;
      color: #fff;
      box-shadow: 0 2px 5px rgba(0,0,0,0.3);
      flex-shrink: 0;
    }}
    .plus-divider {{
      font-size: 1rem;
      font-weight: 900;
      color: var(--text-muted);
      opacity: 0.7;
    }}

    /* 5대 유형 카드 (모바일 최적화) */
    .type-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 16px 14px;
      margin-bottom: 16px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
      position: relative;
      scroll-margin-top: 20px;
    }}
    
    /* 카드 상단: [유형 1] 뱃지와 제목을 한 줄(Row)로 밀착 배치 */
    .type-card-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }}
    .type-header-left {{
      display: flex;
      align-items: center;
      gap: 7px;
      flex-wrap: nowrap;
      min-width: 0;
    }}
    .type-chip {{
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.74rem;
      font-weight: 800;
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.35);
      color: var(--accent);
      white-space: nowrap;
      flex-shrink: 0;
    }}
    .type-title {{
      font-size: clamp(0.98rem, 3.5vw, 1.15rem);
      font-weight: 800;
      color: #fff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .btn-copy {{
      background: #334155;
      border: 1px solid rgba(255,255,255,0.1);
      color: #f1f5f9;
      padding: 6px 11px;
      border-radius: 8px;
      font-size: 0.75rem;
      font-weight: 700;
      cursor: pointer;
      flex-shrink: 0;
      white-space: nowrap;
      transition: background 0.15s;
    }}
    .btn-copy:active {{
      background: var(--accent);
      color: #0b1120;
    }}
    .type-desc-sub {{
      font-size: 0.76rem;
      color: var(--text-muted);
      margin: 2px 0 8px 0;
      word-break: keep-all;
    }}
    .type-concept-box {{
      font-size: 0.8rem;
      color: #cbd5e1;
      line-height: 1.5;
      margin: 8px 0 10px 0;
      padding: 9px 12px;
      border-radius: 10px;
      background: rgba(0,0,0,0.25);
      border-left: 3px solid var(--accent);
      word-break: keep-all;
    }}

    /* 지표 칩 리스트 (한 줄 밀착 레이아웃) */
    .metrics-grid {{
      display: flex;
      flex-wrap: nowrap;
      gap: 4px;
      margin-top: 10px;
      overflow-x: auto;
      scrollbar-width: none;
    }}
    .metrics-grid::-webkit-scrollbar {{
      display: none;
    }}
    .metric-tag {{
      flex: 1 1 0px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.06);
      padding: 5px 4px;
      border-radius: 6px;
      font-size: clamp(0.68rem, 2vw, 0.74rem);
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 3px;
      white-space: nowrap;
    }}
    .metric-tag strong {{
      color: #f8fafc;
      font-weight: 700;
    }}

    /* 상세 사유 아코디언 */
    .reasons-details {{
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid rgba(255,255,255,0.05);
    }}
    .reasons-details summary {{
      font-size: 0.75rem;
      color: var(--accent);
      cursor: pointer;
      font-weight: 600;
      user-select: none;
      outline: none;
    }}
    .reasons-ul {{
      margin-top: 6px;
      padding-left: 16px;
      font-size: 0.75rem;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    /* 통계 랭킹 섹션 (모바일 바 그래프 디자인) */
    .stats-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 16px 14px;
      margin-bottom: 14px;
    }}
    .stats-card h3 {{
      font-size: 0.95rem;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .rank-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }}
    .rank-bar-bg {{
      flex: 1;
      height: 8px;
      background: rgba(255,255,255,0.07);
      border-radius: 999px;
      overflow: hidden;
    }}
    .rank-bar-fill {{
      height: 100%;
      border-radius: 999px;
      transition: width 0.5s ease;
    }}
    .rank-count {{
      font-size: 0.75rem;
      font-weight: 700;
      min-width: 45px;
      text-align: right;
    }}

    /* 하단 모바일 고정 빠른 바 (스마트폰 엄지 터치 최적화) */
    .bottom-bar {{
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: rgba(15, 23, 42, 0.92);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-top: 1px solid rgba(255,255,255,0.1);
      padding: 10px 16px;
      display: flex;
      gap: 10px;
      z-index: 100;
      max-width: 680px;
      margin: 0 auto;
    }}
    .bottom-bar .btn {{
      flex: 1;
      padding: 12px;
      font-size: 0.9rem;
    }}

    /* 모바일 토스트 */
    .toast {{
      position: fixed;
      top: 24px;
      left: 50%;
      transform: translate(-50%, -100px);
      background: #10b981;
      color: #ffffff;
      padding: 10px 20px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 0.85rem;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
      opacity: 0;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 999;
      white-space: nowrap;
    }}
    .toast.show {{
      transform: translate(-50%, 0);
      opacity: 1;
    }}

    footer {{
      text-align: center;
      margin-top: 24px;
      padding-top: 16px;
      color: var(--text-muted);
      font-size: 0.72rem;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="badge">동행복권 1회~{latest_round}회 빅데이터 분석</div>
      <h1>로또 제 {next_round}회 5대 유형</h1>
      <p class="subhead">빅데이터 수리 통계 모델 기반 당첨 확률 최적화 번호</p>
    </header>

    <!-- 요약 통계 2x2 카드 -->
    <div class="summary-grid">
      <div class="summary-card full-width">
        <div class="label">최근 당첨 결과 (제 {latest_round}회)</div>
        <div style="display: flex; align-items: center; justify-content: flex-start; gap: 5px; margin-top: 4px;">
          {''.join(f'<div class="mini-ball ball-{get_ball_class(n)}">{n}</div>' for n in last_item['numbers'])}
          <span style="font-size: 0.8rem; color: var(--text-muted); margin: 0 1px;">+</span>
          <div class="mini-ball ball-{get_ball_class(last_item['bonus'])} ball-bonus">{last_item['bonus']}</div>
        </div>
      </div>
      <div class="summary-card">
        <div class="label">역대 평균 총합</div>
        <div class="value">{stats['avg_sum']}</div>
        <div class="sub-value">최빈구간 120~160</div>
      </div>
      <div class="summary-card">
        <div class="label">역대 평균 AC값</div>
        <div class="value">{stats['avg_ac']}</div>
        <div class="sub-value">산포도 7 이상 (90%)</div>
      </div>
    </div>

    <!-- 모바일 컨트롤 액션 버튼 -->
    <div class="action-grid">
      <button class="btn btn-primary" onclick="reGenerateAll()">
        <span>🔄 5가지 유형 다시 추첨하기</span>
      </button>
      <button class="btn btn-secondary" onclick="copyAllSets()">
        <span>📋 전체 복사</span>
      </button>
      <button class="btn btn-secondary" onclick="syncWithServer()">
        <span>🌐 최신 동기화</span>
      </button>
    </div>

    <!-- 5대 추천 유형 섹션 헤더 -->
    <div class="section-header">
      <div class="section-title">
        <span>🎯 5대 핵심 추천 유형</span>
      </div>
      <span class="section-tag">제 {next_round}회차 대비</span>
    </div>

    <!-- 🔥 [유형 1, 2, 3, 4, 5 한 줄 뱃지 네비게이션 바] -->
    <div class="type-pill-bar">
      <button class="pill-btn active" id="pill-all" onclick="filterType('all', this)">전체보기</button>
      <button class="pill-btn" id="pill-1" onclick="filterType(1, this)">🔥 유형 1</button>
      <button class="pill-btn" id="pill-2" onclick="filterType(2, this)">❄️ 유형 2</button>
      <button class="pill-btn" id="pill-3" onclick="filterType(3, this)">⚖️ 유형 3</button>
      <button class="pill-btn" id="pill-4" onclick="filterType(4, this)">🔗 유형 4</button>
      <button class="pill-btn" id="pill-5" onclick="filterType(5, this)">🤖 유형 5</button>
    </div>

    <!-- 유형별 카드 컨테이너 -->
    <div id="types-container"></div>

    <!-- 핵심 통계 순위표 -->
    <div class="section-header">
      <div class="section-title">
        <span>📊 1회~{latest_round}회 통계 순위</span>
      </div>
    </div>

    <div class="stats-card">
      <h3>🔥 역대 최다 빈출 TOP 10</h3>
      <div id="hot-ranks"></div>
    </div>

    <div class="stats-card">
      <h3>❄️ 최장기 미출현 TOP 10</h3>
      <div id="cold-ranks"></div>
    </div>

    <footer>
      <p>동행복권(dhlottery.co.kr) 실제 1회부터 {latest_round}회까지의 공식 당첨 통계 기준</p>
      <p style="margin-top: 4px;">행운을 빕니다! 🍀</p>
    </footer>
  </div>

  <!-- 하단 고정 퀵 액션 바 -->
  <div class="bottom-bar">
    <button class="btn btn-primary" onclick="reGenerateAll()">
      <span>🔄 원클릭 재추첨</span>
    </button>
    <button class="btn btn-secondary" style="flex: 0 0 auto; padding: 12px 18px;" onclick="copyAllSets()">
      <span>📋 전체복사</span>
    </button>
  </div>

  <div id="toast" class="toast">알림</div>

  <script>
    const INITIAL_TYPES = {types_json};
    const STATS = {stats_json};
    const LAST_ITEM = {last_item_json};
    const ALL_FREQ = {all_freq_json};
    const RECENT_30 = {recent_30_json};
    const OMISSION = {omission_json};
    const AVG_INTERVAL = {avg_interval_json};
    const MAX_HOT = {max_hot_count};
    const MAX_COLD = {max_cold_omission};

    let currentTypes = [...INITIAL_TYPES];
    let selectedFilter = 'all';

    function getBallClass(num) {{
      if (num >= 1 && num <= 10) return 'yellow';
      if (num >= 11 && num <= 20) return 'blue';
      if (num >= 21 && num <= 30) return 'red';
      if (num >= 31 && num <= 40) return 'gray';
      return 'green';
    }}

    function showToast(msg) {{
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2000);
    }}

    function copyText(text, msg = '복사 완료! ✓') {{
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(text).then(() => showToast(msg));
      }} else {{
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast(msg);
      }}
    }}

    function copyAllSets() {{
      const text = currentTypes.map(t => 
        `[유형 ${{t.type_id}}: ${{t.name}}] ${{t.numbers.map(n => String(n).padStart(2, '0')).join(' ')}} (보너스: ${{t.bonus}})`
      ).join('\\n');
      copyText(text, '5개 세트 전체 복사 완료! 📋');
    }}

    function filterType(typeId, btnEl) {{
      selectedFilter = typeId;
      document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
      btnEl.classList.add('active');

      if (typeId === 'all') {{
        renderTypes();
      }} else {{
        renderTypes();
        const targetCard = document.getElementById(`type-card-${{typeId}}`);
        if (targetCard) {{
          targetCard.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
        }}
      }}
    }}

    function renderTypes() {{
      const container = document.getElementById('types-container');
      const filtered = selectedFilter === 'all' 
        ? currentTypes 
        : currentTypes.filter(t => t.type_id === Number(selectedFilter));

      container.innerHTML = filtered.map(t => {{
        const m = t.metrics;
        const balls = t.numbers.map(n => `<div class="ball ball-${{getBallClass(n)}}">${{n}}</div>`).join('');
        const bonus = `<span class="plus-divider">+</span><div class="ball ball-${{getBallClass(t.bonus)}} ball-bonus" title="보너스">${{t.bonus}}</div>`;
        const copyVal = t.numbers.join(', ');
        const reasons = t.reasons.map(r => `<li>${{r}}</li>`).join('');

        return `
          <div class="type-card" id="type-card-${{t.type_id}}">
            <div class="type-card-top">
              <div class="type-header-left">
                <span class="type-chip">유형 ${{t.type_id}}</span>
                <span class="type-title">${{t.name}}</span>
              </div>
              <button class="btn-copy" onclick="copyText('${{copyVal}}', '유형 ${{t.type_id}} 번호 복사 완료! ✓')">복사 📋</button>
            </div>
            
            <div class="type-desc-sub">${{t.subtitle}}</div>
            <div class="type-concept-box">${{t.concept}}</div>

            <div class="ball-wrap">
              ${{balls}}
              ${{bonus}}
            </div>

            <div class="metrics-grid">
              <div class="metric-tag">총합 <strong>${{m.sum}}</strong></div>
              <div class="metric-tag">홀:짝 <strong>${{m.odd_even}}</strong></div>
              <div class="metric-tag">저:고 <strong>${{m.high_low}}</strong></div>
              <div class="metric-tag">AC <strong>${{m.ac_value}}</strong></div>
              <div class="metric-tag">연번 <strong>${{m.consecutive}}쌍</strong></div>
            </div>

            <details class="reasons-details">
              <summary>선정 사유 및 통계 보기 ▸</summary>
              <ul class="reasons-ul">
                ${{reasons}}
              </ul>
            </details>
          </div>
        `;
      }}).join('');
    }}

    function renderStatsRanks() {{
      const hotBox = document.getElementById('hot-ranks');
      hotBox.innerHTML = STATS.top_10_hot.map(item => {{
        const pct = Math.round((item.count / MAX_HOT) * 100);
        return `
          <div class="rank-item">
            <span class="mini-ball ball-${{getBallClass(item.number)}}">${{item.number}}</span>
            <div class="rank-bar-bg">
              <div class="rank-bar-fill" style="width: ${{pct}}%; background: linear-gradient(90deg, #38bdf8, #2563eb);"></div>
            </div>
            <span class="rank-count" style="color: #38bdf8;">${{item.count}}회</span>
          </div>
        `;
      }}).join('');

      const coldBox = document.getElementById('cold-ranks');
      coldBox.innerHTML = STATS.top_10_cold.map(item => {{
        const pct = Math.round((item.omission / MAX_COLD) * 100);
        return `
          <div class="rank-item">
            <span class="mini-ball ball-${{getBallClass(item.number)}}">${{item.number}}</span>
            <div class="rank-bar-bg">
              <div class="rank-bar-fill" style="width: ${{pct}}%; background: linear-gradient(90deg, #f87171, #ef4444);"></div>
            </div>
            <span class="rank-count" style="color: #f87171;">${{item.omission}}주</span>
          </div>
        `;
      }}).join('');
    }}

    async function reGenerateAll() {{
      showToast('새로운 확률 조합을 추출하는 중...');
      try {{
        const resp = await fetch('/api/generate', {{ cache: 'no-store' }});
        if (resp.ok) {{
          const data = await resp.json();
          if (data.types) {{
            currentTypes = data.types;
            renderTypes();
            showToast('5가지 유형이 새로 추첨되었습니다! 🎯');
            return;
          }}
        }}
      }} catch (e) {{}}

      clientSideReGenerate();
      renderTypes();
      showToast('5가지 유형이 새로 추첨되었습니다! 🎯');
    }}

    function sampleN(arr, n) {{
      const shuffled = [...arr].sort(() => 0.5 - Math.random());
      return shuffled.slice(0, n);
    }}

    function sampleCombo(pool) {{
      for (let i = 0; i < 200; i++) {{
        const c = sampleN(pool, 6).sort((a,b) => a - b);
        const sum = c.reduce((a,b) => a+b, 0);
        const odd = c.filter(x => x%2===1).length;
        if (sum >= 115 && sum <= 165 && (odd >= 2 && odd <= 4)) return c;
      }}
      return sampleN(pool, 6).sort((a,b) => a - b);
    }}

    function calcAC(nums) {{
      const diffs = new Set();
      for (let i = 0; i < nums.length; i++) {{
        for (let j = i + 1; j < nums.length; j++) {{
          diffs.add(Math.abs(nums[j] - nums[i]));
        }}
      }}
      return diffs.size - (nums.length - 1);
    }}

    function countConsec(nums) {{
      let c = 0;
      for (let i = 0; i < nums.length - 1; i++) {{
        if (nums[i+1] - nums[i] === 1) c++;
      }}
      return c;
    }}

    function updateMetrics(typeObj) {{
      const nums = typeObj.numbers;
      const sum = nums.reduce((a,b) => a+b, 0);
      const odd = nums.filter(x => x % 2 === 1).length;
      const low = nums.filter(x => x <= 22).length;
      typeObj.metrics = {{
        sum: sum,
        odd_even: `${{odd}}:${{6-odd}}`,
        high_low: `${{low}}:${{6-low}}`,
        ac_value: calcAC(nums),
        consecutive: countConsec(nums)
      }};
    }}

    function clientSideReGenerate() {{
      // Type 1: Hot
      const hotNums = Object.keys(RECENT_30).sort((a,b) => RECENT_30[b] - RECENT_30[a]).slice(0, 18).map(Number);
      currentTypes[0].numbers = sampleCombo(hotNums);
      updateMetrics(currentTypes[0]);

      // Type 2: Cold
      const lastNums = LAST_ITEM.numbers;
      const coldNums = Object.keys(OMISSION).sort((a,b) => (OMISSION[b]/AVG_INTERVAL[b]) - (OMISSION[a]/AVG_INTERVAL[a])).slice(0, 14).map(Number);
      const carry = [lastNums[Math.floor(Math.random() * lastNums.length)]];
      const otherColds = sampleN(coldNums.filter(n => !carry.includes(n)), 5);
      currentTypes[1].numbers = [...carry, ...otherColds].sort((a,b) => a - b);
      updateMetrics(currentTypes[1]);

      // Type 3: Golden
      const s1 = [1,2,3,4,5,6,7,8,9,10];
      const s2 = [11,12,13,14,15,16,17,18,19,20];
      const s3 = [21,22,23,24,25,26,27,28,29,30];
      const s4 = [31,32,33,34,35,36,37,38,39,40];
      const s5 = [41,42,43,44,45];
      for (let i = 0; i < 300; i++) {{
        const c = [
          s1[Math.floor(Math.random() * s1.length)],
          s2[Math.floor(Math.random() * s2.length)],
          s3[Math.floor(Math.random() * s3.length)],
          s4[Math.floor(Math.random() * s4.length)],
          s5[Math.floor(Math.random() * s5.length)],
          s2[Math.floor(Math.random() * s2.length)]
        ];
        const uniq = [...new Set(c)].sort((a,b) => a - b);
        if (uniq.length === 6) {{
          const sum = uniq.reduce((a,b) => a+b, 0);
          const odd = uniq.filter(x => x%2===1).length;
          if (sum >= 125 && sum <= 155 && odd === 3) {{
            currentTypes[2].numbers = uniq;
            break;
          }}
        }}
      }}
      updateMetrics(currentTypes[2]);

      // Type 4: Consecutive
      const consecStart = Math.floor(Math.random() * 40) + 1;
      const consec = [consecStart, consecStart + 1];
      const remain = sampleN(Array.from({{length:45}}, (_,i)=>i+1).filter(x => !consec.includes(x)), 4);
      currentTypes[3].numbers = [...consec, ...remain].sort((a,b) => a - b);
      updateMetrics(currentTypes[3]);

      // Type 5: Hybrid
      const pool = Object.keys(ALL_FREQ).sort((a,b) => ALL_FREQ[b] - ALL_FREQ[a]).slice(0, 22).map(Number);
      currentTypes[4].numbers = sampleCombo(pool);
      updateMetrics(currentTypes[4]);
    }}

    async function syncWithServer() {{
      try {{
        showToast('동행복권 최신 회차 동기화 중...');
        const resp = await fetch('/api/sync');
        if (resp.ok) {{
          const data = await resp.json();
          showToast(data.message || '동기화 완료!');
          setTimeout(() => location.reload(), 1200);
          return;
        }}
      }} catch (e) {{
        showToast('로컬 서버(web_server.py) 실행 중일 때 실시간 동기화가 지원됩니다.');
      }}
    }}

    renderTypes();
    renderStatsRanks();
  </script>
</body>
</html>
"""
    return html


def main():
    print("[1/3] 동행복권 사이트에서 로또 데이터 확인 및 동기화 중...")
    history = sync_lotto_data()
    if not history:
        print("[오류] 데이터를 가져올 수 없습니다.")
        sys.exit(1)

    print("[2/3] 1회부터 최신 회차까지 전수 통계 분석 및 5가지 유형 산출 중...")
    analyzer = LottoAnalyzer(history)
    types_data = analyzer.generate_all_5_types()

    # 터미널 리포트 출력
    print_cli_report(analyzer, types_data)

    print("[3/3] 모바일 최적화 브라우저용 대시보드(HTML) 생성 중...")
    html = generate_html_dashboard(analyzer, types_data)
    dashboard_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "index.html"
    )
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[완료] 모바일 최적화 대시보드 파일 생성됨: {dashboard_path}")


if __name__ == "__main__":
    main()
