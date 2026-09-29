import io
import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta

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


def calculate_fortune_timing(next_round: int) -> dict:
    """
    모든 운의 기운(기문둔갑 8문, 사주 명리 오행 길시, 수비학, 목성/금성 번영 시진)을
    종합하여 매 회차 최적의 [황금 추첨 일시]와 [로또 구매 최적 일시] 및 30분 전 알람 시간을 산출합니다.
    """
    day_options = ["수요일", "목요일", "금요일"]
    lucky_day = day_options[(next_round * 3) % len(day_options)]

    # 길시: 오시(午時 11~13), 신시(申時 15~17), 유시(酉時 17~19)
    time_presets = [
        (15, 7, 33, "신시(申時) 🌟 금수쌍청(金水雙淸) 재물왕성 길시 & 수비학 33초"),
        (16, 48, 55, "신시(申時) 🌟 생기복덕(生氣福德) 기문둔갑 대길시 & 엔젤넘버 55초"),
        (11, 28, 7, "오시(午時) 🌟 태양양기 극대화 천을귀인 길시 & 럭키 7초"),
        (17, 33, 11, "유시(酉時) 🌟 결실과 황금의 금기운 왕성 길시 & 마스터 11초"),
    ]
    h, m, s, energy_desc = time_presets[(next_round * 7) % len(time_presets)]

    # 추첨 30분 전 알람 시각
    draw_total_sec = h * 3600 + m * 60 + s
    draw_alarm_total_sec = max(0, draw_total_sec - 1800)
    dah = draw_alarm_total_sec // 3600
    dam = (draw_alarm_total_sec % 3600) // 60
    das = draw_alarm_total_sec % 60
    draw_alarm_time = f"{dah:02d}시 {dam:02d}분 {das:02d}초"

    # 로또 구매 최적 요일 및 시간
    buy_days = ["목요일", "금요일", "토요일 오전"]
    buy_day = buy_days[(next_round * 2) % len(buy_days)]
    
    buy_time_ranges = [
        ("오후 03시 15분 ~ 04시 45분", 15, 15, "신시(申時) 금전운 상승 구간"),
        ("오전 11시 30분 ~ 오후 01시 10분", 11, 30, "오시(午時) 양기 충만 귀인 구간"),
        ("오후 05시 20분 ~ 06시 50분", 17, 20, "유시(酉時) 결실과 수확 구간"),
        ("오전 10시 10분 ~ 11시 50분", 10, 10, "사시(巳時) 재물 태동 구간"),
    ]
    buy_time, bh, bm, buy_time_desc = buy_time_ranges[(next_round * 5) % len(buy_time_ranges)]

    # 구매 30분 전 알람 시각
    buy_total_min = bh * 60 + bm
    buy_alarm_total_min = max(0, buy_total_min - 30)
    bah = buy_alarm_total_min // 60
    bam = buy_alarm_total_min % 60
    buy_alarm_time = f"{bah:02d}시 {bam:02d}분"

    # 길한 구매 명당 방위
    directions = [
        "현재 계신 곳 기준 [동남쪽 (손방 巽方 - 재물과 번영의 방위)] 판매점",
        "현재 계신 곳 기준 [서북쪽 (건방 乾方 - 하늘의 큰 뜻과 대운 방위)] 판매점",
        "현재 계신 곳 기준 [남쪽 (오방 午方 - 광명과 당첨 불꽃의 방위)] 판매점",
        "현재 계신 곳 기준 [동북쪽 (간방 艮方 - 새로운 시작과 생기 방위)] 판매점",
    ]
    lucky_direction = directions[(next_round * 11) % len(directions)]

    return {
        "next_round": next_round,
        "draw_day": lucky_day,
        "draw_time": f"{h:02d}시 {m:02d}분 {s:02d}초",
        "draw_time_short": f"{h:02d}:{m:02d}:{s:02d}",
        "draw_hour": h,
        "draw_min": m,
        "draw_sec": s,
        "draw_energy": energy_desc,
        "draw_alarm_time": draw_alarm_time,
        "buy_day": buy_day,
        "buy_time": buy_time,
        "buy_hour": bh,
        "buy_min": bm,
        "buy_time_desc": buy_time_desc,
        "buy_alarm_time": buy_alarm_time,
        "buy_direction": lucky_direction,
        "mindset": "현금 5,000원을 준비하여 마음을 평온히 하고, '풍요와 감사가 내게 넘쳐흐른다'는 긍정의 확언과 함께 구입하세요.",
    }


def print_cli_report(analyzer: LottoAnalyzer, types_data: list):
    """콘솔 터미널에 5가지 유형 추천 결과를 보기 좋게 출력합니다."""
    stats = analyzer.get_summary_statistics()
    next_round = analyzer.next_round
    latest_round = analyzer.latest_round
    fortune = calculate_fortune_timing(next_round)

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
    print(f" 🔮 [모든 운의 기운이 충만한 황금 추첨 일시]: 매주 {fortune['draw_day']} {fortune['draw_time']}")
    print(f"    ⏰ 30분 전 알람 시각: {fortune['draw_day']} {fortune['draw_alarm_time']}")
    print(f" 🛒 [로또 구매 최적 일시]: {fortune['buy_day']} {fortune['buy_time']}")
    print(f"    ⏰ 30분 전 알람 시각: {fortune['buy_day']} {fortune['buy_alarm_time']}")
    print(f"    - 행운의 방위: {fortune['buy_direction']}")
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
    fortune = calculate_fortune_timing(next_round)

    types_json = json.dumps(initial_types, ensure_ascii=False)
    stats_json = json.dumps(stats, ensure_ascii=False)
    last_item_json = json.dumps(last_item, ensure_ascii=False)
    fortune_json = json.dumps(fortune, ensure_ascii=False)

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
  <title>로또 6/45 제 {next_round}회 5대 유형 추천기 & 30분 전 알람</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <!-- 🗺️ Leaflet.js (지도를 위한 오픈소스 라이브러리) -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
      --gold: #fbbf24;
      --gold-glow: rgba(251, 191, 36, 0.25);
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
      /* 아이폰 노치 및 다이내믹 아일랜드 대응 Safe Area */
      padding-top: calc(env(safe-area-inset-top, 34px) + 18px);
      padding-left: calc(env(safe-area-inset-left, 0px) + 14px);
      padding-right: calc(env(safe-area-inset-right, 0px) + 14px);
      padding-bottom: calc(env(safe-area-inset-bottom, 20px) + 100px);
      line-height: 1.45;
      overflow-x: hidden;
    }}

    .container {{
      max-width: 680px;
      margin: 0 auto;
    }}

    header {{
      text-align: center;
      padding: 10px 4px 16px 4px;
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
      margin-bottom: 8px;
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

    /* 🔮 [황금 천운 & 구매 일시 지정 카드] */
    .fortune-card {{
      background: linear-gradient(145deg, rgba(30, 41, 59, 0.95) 0%, rgba(20, 29, 47, 0.95) 100%);
      border: 1.5px solid rgba(251, 191, 36, 0.4);
      border-radius: 20px;
      padding: 18px 16px;
      margin-bottom: 20px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35), inset 0 0 20px rgba(251, 191, 36, 0.05);
      position: relative;
      overflow: hidden;
    }}
    .fortune-card::before {{
      content: '';
      position: absolute;
      top: -40px;
      right: -40px;
      width: 120px;
      height: 120px;
      background: radial-gradient(circle, rgba(251, 191, 36, 0.15) 0%, transparent 70%);
      border-radius: 50%;
      pointer-events: none;
    }}
    .fortune-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }}
    .fortune-title {{
      font-size: 1.05rem;
      font-weight: 900;
      color: var(--gold);
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .fortune-pill {{
      font-size: 0.72rem;
      padding: 3px 8px;
      background: rgba(251, 191, 36, 0.15);
      border: 1px solid rgba(251, 191, 36, 0.3);
      color: var(--gold);
      border-radius: 6px;
      font-weight: 700;
    }}
    
    .timing-box {{
      background: rgba(11, 17, 32, 0.6);
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 10px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .timing-label {{
      font-size: 0.76rem;
      color: var(--text-muted);
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .timing-value {{
      font-size: clamp(1.05rem, 3.8vw, 1.3rem);
      font-weight: 900;
      color: #fff;
    }}
    .timing-highlight {{
      color: var(--gold);
    }}
    .timing-desc {{
      font-size: 0.75rem;
      color: #94a3b8;
      margin-top: 4px;
      line-height: 1.4;
    }}

    /* ⏰ [추첨 & 구매 30분 전 알람 섹션] */
    .alarm-section {{
      background: rgba(15, 23, 42, 0.75);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 14px;
      padding: 14px;
      margin: 12px 0;
    }}
    .alarm-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }}
    .alarm-title {{
      font-weight: 800;
      color: #fff;
      font-size: 0.88rem;
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .alarm-badge {{
      font-size: 0.7rem;
      padding: 2px 8px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-muted);
    }}
    .alarm-badge.active {{
      background: rgba(16, 185, 129, 0.2);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.4);
      font-weight: 700;
    }}
    .alarm-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 12px;
    }}
    .alarm-item {{
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 10px;
      padding: 10px;
    }}
    .alarm-item-label {{
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-bottom: 3px;
    }}
    .alarm-item-time {{
      font-size: clamp(0.9rem, 2.9vw, 1.05rem);
      font-weight: 800;
      color: var(--accent);
    }}
    .alarm-item-desc {{
      font-size: 0.68rem;
      color: #94a3b8;
      margin-top: 3px;
      line-height: 1.3;
    }}
    .alarm-btn-wrap {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .btn-alarm {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 12px;
      border-radius: 10px;
      font-size: 0.85rem;
      font-weight: 700;
      cursor: pointer;
      border: none;
      transition: all 0.2s ease;
      touch-action: manipulation;
    }}
    .btn-alarm:active {{
      transform: scale(0.97);
    }}
    .btn-cal {{
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
    }}
    .btn-web {{
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.35);
      color: var(--accent);
    }}
    .btn-web:active {{
      background: rgba(56, 189, 248, 0.3);
    }}

    /* 주간 확정 잠금 버튼 */
    .btn-lock {{
      width: 100%;
      background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
      color: #0b1120;
      font-weight: 900;
      font-size: 0.95rem;
      padding: 13px 16px;
      border-radius: 12px;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      box-shadow: 0 4px 18px rgba(245, 158, 11, 0.35);
      transition: all 0.2s ease;
      margin-top: 10px;
      touch-action: manipulation;
    }}
    .btn-lock:active {{
      transform: scale(0.97);
    }}

    /* 확정 봉인 배너 */
    .lock-banner {{
      display: none;
      background: linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(217, 119, 6, 0.1) 100%);
      border: 1.5px solid var(--gold);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 18px;
      text-align: center;
      animation: pulseGlow 2.5s infinite;
    }}
    @keyframes pulseGlow {{
      0%, 100% {{ box-shadow: 0 0 15px rgba(251, 191, 36, 0.2); }}
      50% {{ box-shadow: 0 0 25px rgba(251, 191, 36, 0.4); }}
    }}
    .lock-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.82rem;
      font-weight: 900;
      color: var(--gold);
      padding: 4px 10px;
      background: rgba(0, 0, 0, 0.3);
      border-radius: 999px;
      margin-bottom: 6px;
    }}
    .lock-countdown {{
      font-size: 1.15rem;
      font-weight: 900;
      color: #fff;
      margin: 4px 0;
      letter-spacing: 0.5px;
    }}
    .lock-sub {{
      font-size: 0.74rem;
      color: #cbd5e1;
    }}
    .btn-unlock-secret {{
      background: none;
      border: none;
      color: #64748b;
      font-size: 0.68rem;
      text-decoration: underline;
      cursor: pointer;
      margin-top: 6px;
    }}

    /* 요약 그리드 */
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin-bottom: 16px;
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

    /* 모바일 액션 버튼 */
    .action-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 16px;
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

    /* 유형 1, 2, 3, 4, 5 가로 한 줄 뱃지 네비게이션 바 */
    .type-pill-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 4px;
      margin: 10px 0 16px 0;
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

    /* 번호 볼 공통 */
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

    /* 5대 유형 카드 */
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

    /* 통계 랭킹 섹션 */
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

    /* 하단 모바일 고정 바 */
    .bottom-bar {{
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-top: 1px solid rgba(255,255,255,0.1);
      padding: 10px 16px calc(env(safe-area-inset-bottom, 12px) + 10px) 16px;
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
      top: calc(env(safe-area-inset-top, 30px) + 14px);
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

    /* 쓸어내려 새로고침 인디케이터 */
    .pull-refresh-indicator {{
      position: fixed;
      top: calc(env(safe-area-inset-top, 30px) + 8px);
      left: 50%;
      transform: translate(-50%, -90px);
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 9px 18px;
      background: rgba(30, 41, 59, 0.95);
      border: 1.5px solid rgba(56, 189, 248, 0.4);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      border-radius: 999px;
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.5);
      z-index: 1000;
      pointer-events: none;
      transition: transform 0.15s ease-out, opacity 0.15s ease-out, border-color 0.2s;
      opacity: 0;
    }}
    .pull-refresh-indicator.refreshing {{
      transform: translate(-50%, 14px) !important;
      opacity: 1 !important;
    }}
    .pull-icon {{
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--accent);
      font-size: 1.15rem;
      font-weight: 900;
      transition: transform 0.2s ease;
    }}
    .pull-text {{
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--text-main);
    }}
    .spinner-spin {{
      display: inline-block;
      animation: pullSpin 0.75s linear infinite;
    }}
    @keyframes pullSpin {{
      100% {{ transform: rotate(360deg); }}
    }}

    /* 🗺️ 지도 & 판매점 추천 섹션 카드 */
    .map-card {{
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%);
      border: 1.5px solid rgba(56, 189, 248, 0.35);
      border-radius: 16px;
      padding: 16px;
      margin-bottom: 20px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
      position: relative;
    }}
    .map-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
    }}
    .map-title {{
      font-size: 1.05rem;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .map-pill {{
      font-size: 0.72rem;
      padding: 3px 8px;
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: 999px;
      font-weight: 700;
    }}
    .fortune-direction-alert {{
      background: rgba(251, 191, 36, 0.12);
      border: 1px dashed rgba(251, 191, 36, 0.4);
      border-radius: 10px;
      padding: 9px 12px;
      font-size: 0.82rem;
      color: #fef3c7;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
      line-height: 1.4;
    }}
    .direction-badge {{
      background: #f59e0b;
      color: #0b1120;
      font-weight: 900;
      font-size: 0.7rem;
      padding: 2px 7px;
      border-radius: 6px;
      flex-shrink: 0;
    }}
    .map-wrapper {{
      position: relative;
      width: 100%;
      height: 330px;
      border-radius: 14px;
      overflow: hidden;
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.4);
    }}
    #lottoMap {{
      width: 100%;
      height: 100%;
      z-index: 1;
    }}
    .map-overlay-compass {{
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(15, 23, 42, 0.88);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(251, 191, 36, 0.4);
      border-radius: 10px;
      padding: 6px 10px;
      z-index: 999;
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      color: #fbbf24;
      pointer-events: none;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }}
    .compass-arrow {{
      font-size: 1.05rem;
      color: #f59e0b;
      display: inline-block;
      animation: bounceArrow 1.5s infinite alternate;
    }}
    @keyframes bounceArrow {{
      from {{ transform: translate(0, 0); }}
      to {{ transform: translate(2px, 2px); }}
    }}
    .map-btn-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
      margin-bottom: 12px;
    }}
    .btn-map-action {{
      padding: 10px;
      border-radius: 10px;
      font-size: 0.82rem;
      font-weight: 700;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      transition: all 0.2s;
      touch-action: manipulation;
    }}
    .btn-map-action:active {{
      transform: scale(0.97);
    }}
    .btn-find-me {{
      background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
      color: #fff;
      box-shadow: 0 3px 12px rgba(2, 132, 199, 0.35);
    }}
    .btn-show-holy {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #e2e8f0;
    }}
    .location-result-box {{
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 12px;
    }}
    .loc-status {{
      font-size: 0.78rem;
      color: var(--text-muted);
      text-align: center;
      line-height: 1.4;
    }}
    .rec-store-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
    }}
    .rec-store-card {{
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .rec-store-card.highlight-card {{
      border: 1.5px solid var(--gold);
      background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    }}
    .rec-badge {{
      font-size: 0.68rem;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 4px;
      align-self: flex-start;
      margin-bottom: 4px;
    }}
    .rec-badge.red {{
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}
    .rec-badge.gold {{
      background: rgba(245, 158, 11, 0.25);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.5);
    }}
    .rec-store-name {{
      font-size: 0.88rem;
      font-weight: 800;
      color: #fff;
      margin-bottom: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .rec-store-meta {{
      font-size: 0.72rem;
      color: var(--text-muted);
      line-height: 1.3;
      margin-bottom: 8px;
    }}
    .rec-link-btn {{
      display: block;
      text-align: center;
      padding: 6px;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 700;
      text-decoration: none;
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.3);
      transition: background 0.2s;
    }}
    .rec-link-btn.gold-btn {{
      background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
      color: #0b1120;
      border: none;
      font-weight: 800;
    }}
    .direct-search-box {{
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px dashed rgba(255, 255, 255, 0.1);
    }}
    .direct-title {{
      font-size: 0.76rem;
      color: var(--text-muted);
      margin-bottom: 8px;
      font-weight: 600;
    }}
    .direct-btn-group {{
      display: flex;
      flex-direction: column;
      gap: 7px;
    }}
    .btn-direct {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: 10px;
      text-decoration: none;
      transition: all 0.2s;
      touch-action: manipulation;
    }}
    .btn-direct:active {{
      transform: scale(0.98);
    }}
    .btn-kakao {{
      background: #fee500;
      color: #191919;
    }}
    .btn-naver {{
      background: #03c75a;
      color: #ffffff;
    }}
    .direct-text-wrap {{
      flex: 1;
      text-align: left;
    }}
    .direct-main {{
      font-size: 0.85rem;
      font-weight: 800;
      line-height: 1.2;
    }}
    .direct-sub {{
      font-size: 0.68rem;
      opacity: 0.85;
      margin-top: 1px;
    }}
    .btn-arrow {{
      font-size: 1.2rem;
      font-weight: 800;
      opacity: 0.6;
    }}

    /* Leaflet 커스텀 다크 팝업 & 마커 */
    .leaflet-popup-content-wrapper {{
      background: rgba(15, 23, 42, 0.95) !important;
      backdrop-filter: blur(10px);
      color: #f8fafc !important;
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 12px !important;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
    }}
    .leaflet-popup-tip {{
      background: rgba(15, 23, 42, 0.95) !important;
    }}
    .popup-box {{
      font-family: 'Pretendard', sans-serif;
      padding: 4px;
      line-height: 1.4;
    }}
    .popup-title {{
      font-size: 0.95rem;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 5px;
      margin-bottom: 2px;
    }}
    .popup-badge {{
      font-size: 0.68rem;
      font-weight: 800;
      color: #fbbf24;
      background: rgba(251, 191, 36, 0.15);
      padding: 1px 6px;
      border-radius: 4px;
      display: inline-block;
      margin-bottom: 6px;
    }}
    .popup-addr {{
      font-size: 0.74rem;
      color: #94a3b8;
      margin-bottom: 8px;
    }}
    .popup-link {{
      display: inline-block;
      width: 100%;
      text-align: center;
      padding: 7px;
      background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
      color: #fff !important;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      text-decoration: none;
    }}

    /* 내 위치 펄스 마커 */
    .user-pulse-marker {{
      width: 22px;
      height: 22px;
      background: #0284c7;
      border: 3px solid #ffffff;
      border-radius: 50%;
      box-shadow: 0 0 15px rgba(2, 132, 199, 0.8);
      position: relative;
    }}
    .user-pulse-marker::after {{
      content: '';
      position: absolute;
      top: -9px;
      left: -9px;
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: rgba(56, 189, 248, 0.4);
      animation: markerPulse 1.8s infinite ease-out;
    }}
    @keyframes markerPulse {{
      0% {{ transform: scale(0.5); opacity: 1; }}
      100% {{ transform: scale(1.6); opacity: 0; }}
    }}

    /* 성지 마커 아이콘 */
    .holy-marker-pin {{
      width: 30px;
      height: 30px;
      background: radial-gradient(circle at 35% 35%, #fbbf24, #b45309);
      border: 2px solid #ffffff;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.4);
      cursor: pointer;
    }}
    .holy-marker-pin.southeast-pin {{
      background: radial-gradient(circle at 35% 35%, #f59e0b, #b45309);
      border: 2.5px solid #6ee7b7;
      box-shadow: 0 0 14px rgba(110, 231, 183, 0.8);
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
  <!-- 쓸어내려 새로고침 상단 플로팅 인디케이터 -->
  <div id="pullIndicator" class="pull-refresh-indicator">
    <div id="pullIcon" class="pull-icon">↓</div>
    <span id="pullText" class="pull-text">아래로 당겨서 새로운 번호 추첨</span>
  </div>

  <div class="container">
    <header>
      <div class="badge">동행복권 1회~{latest_round}회 빅데이터 분석</div>
      <h1>로또 제 {next_round}회 5대 유형</h1>
      <p class="subhead">빅데이터 수리 통계 모델 기반 당첨 확률 최적화 번호</p>
    </header>

    <!-- 🔮 [모든 운의 기운이 충만한 황금 추첨 & 구매 일시 지정 카드] -->
    <div class="fortune-card">
      <div class="fortune-header">
        <div class="fortune-title">
          <span>🔮 모든 운의 기운이 충만한 황금 길시</span>
        </div>
        <span class="fortune-pill">천운(天運) 스케줄</span>
      </div>

      <!-- 추천 1: 황금 추첨 일시 -->
      <div class="timing-box">
        <div class="timing-label">
          <span>🎯 제 {next_round}회 5대 유형 추천 추첨 일시</span>
        </div>
        <div class="timing-value">
          매주 <span class="timing-highlight">{fortune['draw_day']}</span> <span class="timing-highlight">{fortune['draw_time']}</span>
        </div>
        <div class="timing-desc">
          ✨ <strong>운의 기운:</strong> {fortune['draw_energy']}
        </div>
      </div>

      <!-- 추천 2: 로또 구매 최적 일시 (언제 사야 하는지 딱 정해줌) -->
      <div class="timing-box">
        <div class="timing-label">
          <span>🛒 로또 구매 최적 일시 (언제 사야 할까?)</span>
        </div>
        <div class="timing-value" style="color: #6ee7b7;">
          {fortune['buy_day']} {fortune['buy_time']}
        </div>
        <div class="timing-desc">
          📍 <strong>추천 명당 방위:</strong> {fortune['buy_direction']}
        </div>
        <div class="timing-desc" style="color: #94a3b8; margin-top:3px;">
          💡 <strong>구매 팁:</strong> {fortune['mindset']}
        </div>
      </div>

      <!-- ⏰ [추첨 & 구매 30분 전 알람 센터] -->
      <div class="alarm-section">
        <div class="alarm-header">
          <span class="alarm-title">
            ⏰ 30분 전 황금 타이밍 알람
          </span>
          <span class="alarm-badge" id="alarmStatusBadge">알람 미등록</span>
        </div>
        <div class="alarm-grid">
          <!-- 추첨 30분 전 -->
          <div class="alarm-item">
            <div class="alarm-item-label">🎯 추첨 30분 전</div>
            <div class="alarm-item-time">{fortune['draw_day']} {fortune['draw_alarm_time']}</div>
            <div class="alarm-item-desc">기운 집결 & 5대 유형 추첨 준비</div>
          </div>
          <!-- 구매 30분 전 -->
          <div class="alarm-item">
            <div class="alarm-item-label">🛒 구매 30분 전</div>
            <div class="alarm-item-time">{fortune['buy_day']} {fortune['buy_alarm_time']}</div>
            <div class="alarm-item-desc">현금 지참 & 명당 판매점 이동</div>
          </div>
        </div>

        <div class="alarm-btn-wrap">
          <button class="btn-alarm btn-cal" onclick="addToPhoneCalendar()">
            <span>📅 스마트폰 캘린더에 30분 전 알람 추가 (소리/진동)</span>
          </button>
          <button class="btn-alarm btn-web" onclick="enableWebNotification()">
            <span>🔔 브라우저 30분 전 실시간 알림 켜기</span>
          </button>
        </div>
      </div>

      <!-- 주간 확정 잠금 버튼 -->
      <button class="btn-lock" id="btnLock" onclick="lockWeeklyReservation()">
        <span>🔒 이번 회차({next_round}회) 황금 일시로 확정 & 주간 잠금</span>
      </button>
    </div>

    <!-- 🔒 [확정 잠금 시 등장하는 상단 봉인 배너] -->
    <div id="lockBanner" class="lock-banner">
      <div class="lock-badge">🔒 제 {next_round}회 5대 유형 최종 확정 완료</div>
      <div class="lock-sub">모든 운의 기운이 충만한 황금 일시에 맞추어 번호가 봉인되었습니다.</div>
      <div class="lock-countdown" id="lockCountdown">다음 회차 추첨 개방까지: 계산 중...</div>
      <div class="lock-sub">추가 추첨은 다음 주 황금 일시에 단 1번만 가능합니다. 🍀</div>
      <div>
        <button class="btn-unlock-secret" onclick="unlockReservationSecret()">[⚠️ 확정 봉인 해제 (초기화)]</button>
      </div>
    </div>

    <!-- 🗺️ [현재 위치 기반 로또 판매점 & 추천 명당 지도] -->
    <div class="map-card" id="mapSection">
      <div class="map-header">
        <div class="map-title">
          <span>🗺️ 내 주변 로또 판매점 & 추천 명당 지도</span>
        </div>
        <span class="map-pill">실시간 GPS 연동</span>
      </div>

      <!-- 추천 방위 안내 칩 -->
      <div class="fortune-direction-alert">
        <span class="direction-badge">🧭 금주 천운 추천 방위</span>
        <span>현재 계신 곳 기준 <strong>동남쪽 (손방 巽方 · 135°)</strong> 방위의 판매점을 추천합니다!</span>
      </div>

      <!-- 지도 뷰포트 -->
      <div class="map-wrapper">
        <div id="lottoMap"></div>
        <div class="map-overlay-compass">
          <span class="compass-arrow">↘</span>
          <span>손방(동남 135°) 레이더 작동</span>
        </div>
      </div>

      <!-- 지도 상호작용 버튼 -->
      <div class="map-btn-row">
        <button class="btn-map-action btn-find-me" onclick="locateUser(true)">
          <span>📍 내 현재 위치로 지도 맞추기</span>
        </button>
        <button class="btn-map-action btn-show-holy" onclick="showAllHolySpots()">
          <span>🏆 전국 1등 성지 TOP 16 보기</span>
        </button>
      </div>

      <!-- 내 위치 분석 결과 카드 -->
      <div class="location-result-box" id="locationResultBox">
        <div class="loc-status" id="locStatusText">
          <span class="spinner-spin">🔄</span> 현재 위치(GPS)를 확인하는 중입니다...
        </div>

        <div class="rec-store-grid" id="recStoreGrid" style="display: none;">
          <!-- 가장 가까운 성지 명당 -->
          <div class="rec-store-card">
            <div class="rec-badge red">🏃 가장 가까운 1등 성지</div>
            <div class="rec-store-name" id="nearestHolyName">-</div>
            <div class="rec-store-meta" id="nearestHolyMeta">-</div>
            <a class="rec-link-btn" id="nearestHolyLink" href="#" target="_blank">길찾기 (카카오맵) ↗</a>
          </div>
          <!-- 동남쪽 천운 명당 -->
          <div class="rec-store-card highlight-card">
            <div class="rec-badge gold">⭐ 동남쪽(손방) 천운 명당</div>
            <div class="rec-store-name" id="southeastHolyName">-</div>
            <div class="rec-store-meta" id="southeastHolyMeta">-</div>
            <a class="rec-link-btn gold-btn" id="southeastHolyLink" href="#" target="_blank">길찾기 (카카오맵) ↗</a>
          </div>
        </div>
      </div>

      <!-- ⚡ 원클릭 내 주변 실시간 로또 판매점 즉시 찾기 (카카오맵 & 네이버지도 앱 연동) -->
      <div class="direct-search-box">
        <div class="direct-title">⚡ 지금 바로 도보/차량으로 갈 수 있는 판매점 찾기</div>
        <div class="direct-btn-group">
          <a class="btn-direct btn-kakao" id="kakaoNearbyBtn" href="https://map.kakao.com/link/search/로또판매점" target="_blank">
            <span style="font-size: 1.3rem;">💛</span>
            <div class="direct-text-wrap">
              <div class="direct-main">카카오맵 내 주변 로또점 (거리순)</div>
              <div class="direct-sub">현재 위치 반경 100m~500m 실시간 영업점 & 도보 길안내</div>
            </div>
            <span class="btn-arrow">›</span>
          </a>
          <a class="btn-direct btn-naver" id="naverNearbyBtn" href="https://m.map.naver.com/search2/search.naver?query=로또판매점" target="_blank">
            <span style="font-size: 1.3rem;">💚</span>
            <div class="direct-text-wrap">
              <div class="direct-main">네이버 지도 내 주변 판매점</div>
              <div class="direct-sub">네이버 플레이스 후기 및 가장 가까운 판매점 찾기</div>
            </div>
            <span class="btn-arrow">›</span>
          </a>
        </div>
      </div>
    </div>

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
      <button class="btn btn-primary" id="btnReGen" onclick="reGenerateAll()">
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
      <p style="margin-top: 4px;">천운과 대박의 기운이 함께하시길 기원합니다! 🍀</p>
    </footer>
  </div>

  <!-- 하단 고정 퀵 액션 바 -->
  <div class="bottom-bar">
    <button class="btn btn-primary" id="btnBottomReGen" onclick="reGenerateAll()">
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
    const FORTUNE = {fortune_json};
    const ALL_FREQ = {all_freq_json};
    const RECENT_30 = {recent_30_json};
    const OMISSION = {omission_json};
    const AVG_INTERVAL = {avg_interval_json};
    const MAX_HOT = {max_hot_count};
    const MAX_COLD = {max_cold_omission};

    let currentTypes = [...INITIAL_TYPES];
    let selectedFilter = 'all';
    let isLocked = false;
    let lockTimerInterval = null;

    const STORAGE_KEY_LOCK = `lotto_lock_${{FORTUNE.next_round}}`;
    const STORAGE_KEY_DATA = `lotto_types_${{FORTUNE.next_round}}`;
    const STORAGE_KEY_ALARM = `lotto_alarm_registered_${{FORTUNE.next_round}}`;

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
      setTimeout(() => toast.classList.remove('show'), 2200);
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
      const lockStatusText = isLocked ? `[제 ${{FORTUNE.next_round}}회 최종 확정 번호]` : `[제 ${{FORTUNE.next_round}}회 추천 번호]`;
      const text = `${{lockStatusText}}\\n` + currentTypes.map(t => 
        `[유형 ${{t.type_id}}: ${{t.name}}] ${{t.numbers.map(n => String(n).padStart(2, '0')).join(' ')}} (보너스: ${{t.bonus}})`
      ).join('\\n');
      copyText(text, '5개 세트 전체 복사 완료! 📋');
    }}

    // ==========================================
    // ⏰ [추첨 & 구매 30분 전 알람 및 캘린더 등록]
    // ==========================================
    function checkAlarmStatus() {{
      const registered = localStorage.getItem(STORAGE_KEY_ALARM);
      const badge = document.getElementById('alarmStatusBadge');
      if (registered === 'true' && badge) {{
        badge.innerText = '알람 활성화됨 ✓';
        badge.classList.add('active');
      }}
    }}

    // 요일 이름 -> 이번 주 기준 날짜 계산
    function getNextDayOfWeek(dayName) {{
      const days = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일'];
      const targetDay = days.indexOf(dayName);
      const now = new Date();
      const result = new Date(now);
      const diff = (targetDay - now.getDay() + 7) % 7;
      result.setDate(now.getDate() + (diff === 0 ? 7 : diff));
      return result;
    }}

    function formatICSDate(date) {{
      return date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
    }}

    // 스마트폰 캘린더(.ics)에 30분 전 알람 포함 자동 등록
    function addToPhoneCalendar() {{
      const drawDate = getNextDayOfWeek(FORTUNE.draw_day);
      drawDate.setHours(FORTUNE.draw_hour, FORTUNE.draw_min, FORTUNE.draw_sec, 0);

      const buyDate = getNextDayOfWeek(FORTUNE.buy_day);
      buyDate.setHours(FORTUNE.buy_hour, FORTUNE.buy_min, 0, 0);

      const drawEnd = new Date(drawDate.getTime() + 15 * 60 * 1000);
      const buyEnd = new Date(buyDate.getTime() + 30 * 60 * 1000);

      const icsData = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Lotto 5-Type Recommender//KR',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',

        // 이벤트 1: 황금 추첨 30분 전 알람
        'BEGIN:VEVENT',
        `UID:lotto-draw-${{FORTUNE.next_round}}@lotto.local`,
        `DTSTAMP:${{formatICSDate(new Date())}}`,
        `DTSTART:${{formatICSDate(drawDate)}}`,
        `DTEND:${{formatICSDate(drawEnd)}}`,
        `SUMMARY:🎯 [로또 제${{FORTUNE.next_round}}회] 황금 추첨 시간 (30분 전 알람)`,
        `DESCRIPTION:모든 운의 기운이 충만한 황금 추첨 시간입니다!\\n운의 기운: ${{FORTUNE.draw_energy}}`,
        'STATUS:CONFIRMED',
        'BEGIN:VALARM',
        'TRIGGER:-PT30M',
        'ACTION:DISPLAY',
        'DESCRIPTION:⏰ 로또 5대유형 황금 추첨 30분 전입니다! 기운을 모아 번호를 확인하세요.',
        'END:VALARM',
        'END:VEVENT',

        // 이벤트 2: 로또 구매 30분 전 알람
        'BEGIN:VEVENT',
        `UID:lotto-buy-${{FORTUNE.next_round}}@lotto.local`,
        `DTSTAMP:${{formatICSDate(new Date())}}`,
        `DTSTART:${{formatICSDate(buyDate)}}`,
        `DTEND:${{formatICSDate(buyEnd)}}`,
        `SUMMARY:🛒 [로또 제${{FORTUNE.next_round}}회] 로또 구매 골든타임 (30분 전 알람)`,
        `DESCRIPTION:로또 구매 최적 길시입니다!\\n명당 방위: ${{FORTUNE.buy_direction}}\\n구매 팁: ${{FORTUNE.mindset}}`,
        'STATUS:CONFIRMED',
        'BEGIN:VALARM',
        'TRIGGER:-PT30M',
        'ACTION:DISPLAY',
        'DESCRIPTION:⏰ 로또 구매 골든타임 30분 전입니다! 현금 5,000원을 준비하여 명당 판매점으로 이동하세요.',
        'END:VALARM',
        'END:VEVENT',

        'END:VCALENDAR'
      ].join('\\r\\n');

      const blob = new Blob([icsData], {{ type: 'text/calendar;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `lotto_${{FORTUNE.next_round}}_alarm.ics`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      localStorage.setItem(STORAGE_KEY_ALARM, 'true');
      checkAlarmStatus();
      showToast('스마트폰 캘린더에 30분 전 알람이 등록되었습니다! 📅');
    }}

    // 브라우저 웹 알림(Web Notification) 권한 요청 및 활성화
    function enableWebNotification() {{
      if (!('Notification' in window)) {{
        showToast('이 브라우저는 웹 푸시를 지원하지 않습니다. 캘린더 알람을 이용해주세요.');
        return;
      }}

      Notification.requestPermission().then((permission) => {{
        if (permission === 'granted') {{
          localStorage.setItem(STORAGE_KEY_ALARM, 'true');
          checkAlarmStatus();
          new Notification('🎯 로또 5대유형 30분 전 알람 활성화 완료', {{
            body: `제 ${{FORTUNE.next_round}}회 추첨(${{FORTUNE.draw_alarm_time}}) 및 구매(${{FORTUNE.buy_alarm_time}}) 30분 전에 알람이 발송됩니다.`,
            icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="45" fill="%23f59e0b"/><text x="50" y="62" font-size="38" text-anchor="middle" fill="%23fff" font-weight="bold">77</text></svg>'
          }});
          showToast('브라우저 30분 전 알림이 활성화되었습니다! 🔔');
        }} else {{
          showToast('알림 권한이 허용되지 않았습니다. 브라우저 설정에서 허용해 주세요.');
        }}
      }});
    }}

    // ==========================================
    // 🔒 [주간 1회 확정 잠금 & 천운 예약 시스템]
    // ==========================================
    function checkLockStatus() {{
      const savedLock = localStorage.getItem(STORAGE_KEY_LOCK);
      const savedData = localStorage.getItem(STORAGE_KEY_DATA);

      if (savedLock && savedData) {{
        const lockInfo = JSON.parse(savedLock);
        const unlockTime = new Date(lockInfo.unlockTime).getTime();
        const now = new Date().getTime();

        if (now < unlockTime) {{
          isLocked = true;
          currentTypes = JSON.parse(savedData);
          applyLockedUI(unlockTime);
          return;
        }} else {{
          localStorage.removeItem(STORAGE_KEY_LOCK);
          localStorage.removeItem(STORAGE_KEY_DATA);
        }}
      }}
      isLocked = false;
      applyUnlockedUI();
    }}

    function lockWeeklyReservation() {{
      if (isLocked) {{
        showToast('이미 이번 회차 번호가 확정 봉인되어 있습니다! 🔒');
        return;
      }}

      const now = new Date();
      const unlockDate = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
      unlockDate.setHours(FORTUNE.draw_hour, FORTUNE.draw_min, FORTUNE.draw_sec, 0);

      const lockPayload = {{
        round: FORTUNE.next_round,
        lockedAt: now.toISOString(),
        unlockTime: unlockDate.toISOString()
      }};

      localStorage.setItem(STORAGE_KEY_LOCK, JSON.stringify(lockPayload));
      localStorage.setItem(STORAGE_KEY_DATA, JSON.stringify(currentTypes));

      isLocked = true;
      applyLockedUI(unlockDate.getTime());

      if (navigator.vibrate) {{
        try {{ navigator.vibrate([40, 60, 40]); }} catch(e) {{}}
      }}

      showToast(`제 ${{FORTUNE.next_round}}회 5대 유형이 최종 확정 봉인되었습니다! 🔒`);
    }}

    function applyLockedUI(unlockTime) {{
      const banner = document.getElementById('lockBanner');
      banner.style.display = 'block';

      const btnLock = document.getElementById('btnLock');
      btnLock.innerHTML = '<span>🔒 이번 회차 확정 봉인 완료됨</span>';
      btnLock.style.background = '#334155';
      btnLock.style.color = '#94a3b8';

      const reGenBtn = document.getElementById('btnReGen');
      if (reGenBtn) {{
        reGenBtn.innerHTML = '<span>🔒 이번 회차 번호 봉인됨</span>';
        reGenBtn.style.opacity = '0.7';
      }}
      const bottomBtn = document.getElementById('btnBottomReGen');
      if (bottomBtn) {{
        bottomBtn.innerHTML = '<span>🔒 번호 봉인됨</span>';
        bottomBtn.style.opacity = '0.7';
      }}

      if (lockTimerInterval) clearInterval(lockTimerInterval);
      updateCountdown(unlockTime);
      lockTimerInterval = setInterval(() => updateCountdown(unlockTime), 1000);
    }}

    function applyUnlockedUI() {{
      const banner = document.getElementById('lockBanner');
      banner.style.display = 'none';

      const btnLock = document.getElementById('btnLock');
      btnLock.innerHTML = '<span>🔒 이번 회차(' + FORTUNE.next_round + '회) 황금 일시로 확정 & 주간 잠금</span>';
      btnLock.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
      btnLock.style.color = '#0b1120';

      const reGenBtn = document.getElementById('btnReGen');
      if (reGenBtn) {{
        reGenBtn.innerHTML = '<span>🔄 5가지 유형 다시 추첨하기</span>';
        reGenBtn.style.opacity = '1';
      }}
      const bottomBtn = document.getElementById('btnBottomReGen');
      if (bottomBtn) {{
        bottomBtn.innerHTML = '<span>🔄 원클릭 재추첨</span>';
        bottomBtn.style.opacity = '1';
      }}

      if (lockTimerInterval) clearInterval(lockTimerInterval);
    }}

    function updateCountdown(targetTime) {{
      const now = new Date().getTime();
      const diff = targetTime - now;

      if (diff <= 0) {{
        clearInterval(lockTimerInterval);
        localStorage.removeItem(STORAGE_KEY_LOCK);
        isLocked = false;
        applyUnlockedUI();
        showToast('다음 회차 황금 추첨이 개방되었습니다! 🎯');
        return;
      }}

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      const el = document.getElementById('lockCountdown');
      if (el) {{
        el.innerText = `다음 추첨 개방: D-${{days}}일 ${{String(hours).padStart(2,'0')}}시간 ${{String(minutes).padStart(2,'0')}}분 ${{String(seconds).padStart(2,'0')}}초`;
      }}
    }}

    function unlockReservationSecret() {{
      if (confirm('정말로 확정 봉인을 해제하고 다시 번호를 추첨하시겠습니까?')) {{
        localStorage.removeItem(STORAGE_KEY_LOCK);
        localStorage.removeItem(STORAGE_KEY_DATA);
        isLocked = false;
        applyUnlockedUI();
        showToast('확정 봉인이 해제되었습니다. 자유롭게 재추첨할 수 있습니다.');
      }}
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
      if (isLocked) {{
        showToast('🔒 이번 회차 번호가 이미 확정되었습니다! (다음 주 황금 일시에 다시 추첨 가능)');
        return;
      }}

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
      const hotNums = Object.keys(RECENT_30).sort((a,b) => RECENT_30[b] - RECENT_30[a]).slice(0, 18).map(Number);
      currentTypes[0].numbers = sampleCombo(hotNums);
      updateMetrics(currentTypes[0]);

      const lastNums = LAST_ITEM.numbers;
      const coldNums = Object.keys(OMISSION).sort((a,b) => (OMISSION[b]/AVG_INTERVAL[b]) - (OMISSION[a]/AVG_INTERVAL[a])).slice(0, 14).map(Number);
      const carry = [lastNums[Math.floor(Math.random() * lastNums.length)]];
      const otherColds = sampleN(coldNums.filter(n => !carry.includes(n)), 5);
      currentTypes[1].numbers = [...carry, ...otherColds].sort((a,b) => a - b);
      updateMetrics(currentTypes[1]);

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

      const consecStart = Math.floor(Math.random() * 40) + 1;
      const consec = [consecStart, consecStart + 1];
      const remain = sampleN(Array.from({{length:45}}, (_,i)=>i+1).filter(x => !consec.includes(x)), 4);
      currentTypes[3].numbers = [...consec, ...remain].sort((a,b) => a - b);
      updateMetrics(currentTypes[3]);

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

    // ==========================================
    // 📱 모바일 화면 쓸어내려 새로고침 (Pull-to-Refresh)
    // ==========================================
    const pullIndicator = document.getElementById('pullIndicator');
    const pullIcon = document.getElementById('pullIcon');
    const pullText = document.getElementById('pullText');

    let touchStartY = 0;
    let isPulling = false;
    let isRefreshing = false;
    const PULL_THRESHOLD = 70;

    window.addEventListener('touchstart', (e) => {{
      if (window.scrollY <= 2 && !isRefreshing) {{
        touchStartY = e.touches[0].clientY;
        isPulling = true;
      }}
    }}, {{ passive: true }});

    window.addEventListener('touchmove', (e) => {{
      if (!isPulling || isRefreshing) return;
      const currentY = e.touches[0].clientY;
      const diffY = currentY - touchStartY;

      if (diffY > 8 && window.scrollY <= 2) {{
        const pullDistance = Math.min(Math.pow(diffY, 0.82) * 1.5, 95);
        pullIndicator.style.opacity = String(Math.min(pullDistance / 45, 1));
        pullIndicator.style.transform = `translate(-50%, ${{pullDistance - 55}}px)`;

        if (isLocked) {{
          pullText.innerText = '🔒 이번 회차 번호가 이미 확정되었습니다';
          pullIndicator.style.borderColor = '#f59e0b';
        }} else if (pullDistance >= PULL_THRESHOLD) {{
          pullIcon.style.transform = 'rotate(180deg)';
          pullText.innerText = '손을 놓으면 새로운 번호 추첨! 🎯';
          pullIndicator.style.borderColor = '#10b981';
        }} else {{
          pullIcon.style.transform = 'rotate(0deg)';
          pullText.innerText = '아래로 당겨서 새로운 번호 추첨';
          pullIndicator.style.borderColor = 'rgba(56, 189, 248, 0.4)';
        }}
      }}
    }}, {{ passive: true }});

    window.addEventListener('touchend', async (e) => {{
      if (!isPulling || isRefreshing) return;
      isPulling = false;

      const endY = (e.changedTouches && e.changedTouches[0]) ? e.changedTouches[0].clientY : 0;
      const diffY = endY - touchStartY;
      const pullDistance = Math.min(Math.pow(Math.max(0, diffY), 0.82) * 1.5, 95);

      if (pullDistance >= PULL_THRESHOLD && window.scrollY <= 2) {{
        if (isLocked) {{
          pullIndicator.style.transform = 'translate(-50%, -90px)';
          pullIndicator.style.opacity = '0';
          showToast('🔒 이번 회차 번호가 이미 확정되었습니다!');
        }} else {{
          await triggerPullRefresh();
        }}
      }} else {{
        pullIndicator.style.transform = 'translate(-50%, -90px)';
        pullIndicator.style.opacity = '0';
      }}
    }});

    async function triggerPullRefresh() {{
      isRefreshing = true;
      if (navigator.vibrate) {{
        try {{ navigator.vibrate(30); }} catch (e) {{}}
      }}

      pullIndicator.classList.add('refreshing');
      pullIcon.innerText = '🔄';
      pullIcon.classList.add('spinner-spin');
      pullText.innerText = '5대 유형 새로 분석 & 추첨 중...';

      await reGenerateAll();

      pullIcon.classList.remove('spinner-spin');
      pullIcon.innerText = '✓';
      pullText.innerText = '추첨 완료! 새로운 번호 도출';
      pullIndicator.style.borderColor = '#10b981';

      setTimeout(() => {{
        pullIndicator.classList.remove('refreshing');
        pullIndicator.style.transform = 'translate(-50%, -90px)';
        pullIndicator.style.opacity = '0';
        pullIcon.innerText = '↓';
        pullIcon.style.transform = 'rotate(0deg)';
        isRefreshing = false;
      }}, 750);
    }}

    // ==========================================
    // 🗺️ [현재 위치 기반 지도 & 로또 명당 추천 시스템]
    // ==========================================
    const HOLY_STORES = [
      {{ name: '스파', region: '서울 노원구', count: '1등 52회+', addr: '서울 노원구 동일로 1493 상계주공10단지종합상가', lat: 37.6542, lng: 127.0601 }},
      {{ name: '부일카서비스', region: '부산 동구', count: '1등 45회+', addr: '부산 동구 자성로133번길 35', lat: 35.1384, lng: 129.0632 }},
      {{ name: '일등복권편의점', region: '대구 달서구', count: '1등 32회+', addr: '대구 달서구 대명천로 220', lat: 35.8452, lng: 128.5323 }},
      {{ name: '로또휴게실', region: '경기 용인시', count: '1등 26회+', addr: '경기 용인시 기흥구 용구대로 1885', lat: 37.2563, lng: 127.1084 }},
      {{ name: '로또명당인주점', region: '충남 아산시', count: '1등 22회+', addr: '충남 아산시 인주일로 85', lat: 36.9015, lng: 126.9082 }},
      {{ name: '잠실매점', region: '서울 송파구', count: '1등 20회+', addr: '서울 송파구 올림픽로 269 잠실역 8번출구 앞', lat: 37.5142, lng: 127.1002 }},
      {{ name: '알리바이', region: '광주 광산구', count: '1등 20회+', addr: '광주 광산구 수완로 11번길 3', lat: 35.1912, lng: 126.8223 }},
      {{ name: '세진전자통신', region: '대구 서구', count: '1등 19회+', addr: '대구 서구 서대구로 156', lat: 35.8672, lng: 128.5583 }},
      {{ name: '록앤락복권방', region: '전남 목포시', count: '1등 18회+', addr: '전남 목포시 영산로 525', lat: 34.8231, lng: 126.4172 }},
      {{ name: '행운복권방 보령점', region: '충남 보령시', count: '1등 17회+', addr: '충남 보령시 대천로 46', lat: 36.3312, lng: 126.6021 }},
      {{ name: '대박찬스', region: '충북 청주시', count: '1등 16회+', addr: '충북 청주시 흥덕구 가경로 161', lat: 36.6214, lng: 127.4332 }},
      {{ name: '제이복권방', region: '서울 종로구', count: '1등 15회+', addr: '서울 종로구 종로 225-1', lat: 37.5711, lng: 127.0102 }},
      {{ name: '행운을주는로또', region: '경기 안산시', count: '1등 15회+', addr: '경기 안산시 단원구 광덕4로 112', lat: 37.3092, lng: 126.8331 }},
      {{ name: '복권천국', region: '인천 부평구', count: '1등 14회+', addr: '인천 부평구 부평문화로 45', lat: 37.4931, lng: 126.7242 }},
      {{ name: '명당복권방', region: '강원 원주시', count: '1등 13회+', addr: '강원 원주시 남원로 608', lat: 37.3371, lng: 127.9472 }},
      {{ name: 'CU제주삼화점', region: '제주 제주시', count: '제주 1등 최다', addr: '제주 제주시 화삼로 15', lat: 33.5182, lng: 126.5771 }}
    ];

    let lottoMap = null;
    let userMarker = null;
    let userCircle = null;
    let radarPolygon = null;
    let holyMarkers = [];
    let currentCoords = null;

    function toRad(deg) {{ return (deg * Math.PI) / 180; }}
    function toDeg(rad) {{ return (rad * 180) / Math.PI; }}

    function getDistanceKm(lat1, lon1, lat2, lon2) {{
      const R = 6371; // km
      const dLat = toRad(lat2 - lat1);
      const dLon = toRad(lon2 - lon1);
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      return Math.round(R * c * 10) / 10;
    }}

    function getBearing(lat1, lon1, lat2, lon2) {{
      const dLon = toRad(lon2 - lon1);
      const y = Math.sin(dLon) * Math.cos(toRad(lat2));
      const x = Math.cos(toRad(lat1)) * Math.sin(toRad(lat2)) -
                Math.sin(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(dLon);
      let brng = toDeg(Math.atan2(y, x));
      return Math.round((brng + 360) % 360);
    }}

    function getBearingDirection(brng) {{
      if (brng >= 337.5 || brng < 22.5) return '북쪽';
      if (brng >= 22.5 && brng < 67.5) return '북동쪽';
      if (brng >= 67.5 && brng < 112.5) return '동쪽';
      if (brng >= 112.5 && brng < 157.5) return '동남쪽 (손방 巽方 ⭐)';
      if (brng >= 157.5 && brng < 202.5) return '남쪽';
      if (brng >= 202.5 && brng < 247.5) return '남서쪽';
      if (brng >= 247.5 && brng < 292.5) return '서쪽';
      return '서북쪽';
    }}

    function createRadarSector(lat, lng, radiusKm, startAngle, endAngle) {{
      const points = [[lat, lng]];
      const R = 6371;
      for (let a = startAngle; a <= endAngle; a += 2) {{
        const rad = toRad(a);
        const dByR = radiusKm / R;
        const latRad = toRad(lat);
        const lngRad = toRad(lng);
        const destLat = Math.asin(Math.sin(latRad) * Math.cos(dByR) + Math.cos(latRad) * Math.sin(dByR) * Math.cos(rad));
        const destLng = lngRad + Math.atan2(Math.sin(rad) * Math.sin(dByR) * Math.cos(latRad), Math.cos(dByR) - Math.sin(latRad) * Math.sin(destLat));
        points.push([toDeg(destLat), toDeg(destLng)]);
      }}
      points.push([lat, lng]);
      return points;
    }}

    function initLottoMap() {{
      if (!window.L) {{
        console.warn('Leaflet 라이브러리가 로드되지 않았습니다.');
        return;
      }}

      // 기본 지도 초기화 (서울 중심)
      lottoMap = L.map('lottoMap', {{
        scrollWheelZoom: false,
        touchZoom: true,
        tap: false
      }}).setView([37.5665, 126.9780], 12);

      L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 19,
        attribution: '© OpenStreetMap'
      }}).addTo(lottoMap);

      // 16대 전국 1등 성지 마커 추가
      HOLY_STORES.forEach((item) => {{
        const holyPin = L.divIcon({{
          className: 'custom-holy-pin',
          html: '<div class="holy-marker-pin" id="holy-pin-' + encodeURIComponent(item.name) + '">🏆</div>',
          iconSize: [30, 30],
          iconAnchor: [15, 15]
        }});

        const kakaoNaviUrl = 'https://map.kakao.com/link/to/' + encodeURIComponent(item.name + '(로또명당)') + ',' + item.lat + ',' + item.lng;
        const popupContent = `
          <div class="popup-box">
            <div class="popup-title">🏆 ${{item.name}}</div>
            <div class="popup-badge">${{item.count}} 배출 (${{item.region}})</div>
            <div class="popup-addr">${{item.addr}}</div>
            <a class="popup-link" href="${{kakaoNaviUrl}}" target="_blank">카카오맵 바로 길찾기 ↗</a>
          </div>
        `;

        const m = L.marker([item.lat, item.lng], {{ icon: holyPin }})
          .addTo(lottoMap)
          .bindPopup(popupContent);
        holyMarkers.push({{ store: item, marker: m }});
      }});

      // 자동으로 사용자 위치 측정 시작
      locateUser(false);
    }}

    function locateUser(isUserAction) {{
      const statusText = document.getElementById('locStatusText');
      if (statusText) {{
        statusText.innerHTML = '<span class="spinner-spin">🔄</span> GPS 위성 신호로 현재 위치를 확인 중입니다...';
      }}

      if (!navigator.geolocation) {{
        if (statusText) {{
          statusText.innerHTML = '📍 브라우저에서 위치 정보를 지원하지 않습니다. 아래 버튼으로 카카오맵을 확인하세요.';
        }}
        processStoresWithCenter(37.5665, 126.9780, false);
        return;
      }}

      navigator.geolocation.getCurrentPosition(
        (pos) => {{
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          const accuracy = Math.round(pos.coords.accuracy || 50);
          currentCoords = {{ lat, lng }};

          onLocationFound(lat, lng, accuracy, isUserAction);
        }},
        (err) => {{
          console.warn('Geolocation failed:', err);
          if (statusText) {{
            statusText.innerHTML = '📍 현재 위치(GPS) 권한을 허용하시면 가장 가까운 판매점이 자동 추천됩니다.<br><span style="font-size:0.7rem; color:#94a3b8;">(현재는 전국 16대 1등 성지 지도가 표시 중입니다)</span>';
          }}
          processStoresWithCenter(37.5665, 126.9780, false);
          if (isUserAction) {{
            showToast('브라우저 설정에서 위치 권한을 허용해주시면 실시간 주변 매장을 추천해 드립니다.');
          }}
        }},
        {{ enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }}
      );
    }}

    function onLocationFound(lat, lng, accuracy, isUserAction) {{
      if (!lottoMap) return;

      // 지도 중심을 내 위치로 이동 (적절한 줌 레벨)
      lottoMap.setView([lat, lng], 13);

      // 기존 내 위치 마커 & 원 제거
      if (userMarker) lottoMap.removeLayer(userMarker);
      if (userCircle) lottoMap.removeLayer(userCircle);
      if (radarPolygon) lottoMap.removeLayer(radarPolygon);

      // 펄스 마커 & 정확도 반경
      const userPulseIcon = L.divIcon({{
        className: 'custom-user-pin',
        html: '<div class="user-pulse-marker" title="내 현재 위치"></div>',
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      }});

      userMarker = L.marker([lat, lng], {{ icon: userPulseIcon }})
        .addTo(lottoMap)
        .bindPopup('<div class="popup-box"><div class="popup-title">📍 내 현재 위치</div><div class="popup-addr">GPS 정확도: ±' + accuracy + 'm</div><div style="font-size:0.75rem; color:#38bdf8; font-weight:700;">금주 천운 방위: 동남쪽(135°)</div></div>');

      userCircle = L.circle([lat, lng], {{
        radius: Math.min(accuracy, 1000),
        color: '#38bdf8',
        weight: 1,
        fillColor: '#0284c7',
        fillOpacity: 0.12
      }}).addTo(lottoMap);

      // 🧭 금주 추천 행운 방위: 동남쪽 (손방 巽方: 112.5° ~ 157.5°, 반경 4km 부채꼴) 레이더 그리기
      const sectorPoints = createRadarSector(lat, lng, 4.5, 112.5, 157.5);
      radarPolygon = L.polygon(sectorPoints, {{
        color: '#fbbf24',
        weight: 2,
        fillColor: '#f59e0b',
        fillOpacity: 0.22,
        dashArray: '6, 6'
      }}).addTo(lottoMap);

      // 상태 메시지 업데이트
      const statusText = document.getElementById('locStatusText');
      if (statusText) {{
        statusText.innerHTML = `📍 <strong>현재 위치 감지 완료!</strong> (정확도 ±${{accuracy}}m)<br><span style="color:#fbbf24;">✨ 금주 천운 방위인 동남쪽(손방 135°) 레이더가 활성화되었습니다.</span>`;
      }}

      // 성지 명당과의 거리 및 방위 계산
      processStoresWithCenter(lat, lng, true);

      if (isUserAction) {{
        showToast('내 위치로 지도가 이동되었습니다! 📍');
      }}
    }}

    function processStoresWithCenter(centerLat, centerLng, hasRealLocation) {{
      const calculated = HOLY_STORES.map((s) => {{
        const dist = getDistanceKm(centerLat, centerLng, s.lat, s.lng);
        const brng = getBearing(centerLat, centerLng, s.lat, s.lng);
        const dirName = getBearingDirection(brng);
        const isSE = (brng >= 90 && brng <= 180);
        return {{ ...s, distance: dist, bearing: brng, dirName: dirName, isSoutheast: isSE }};
      }});

      // 거리 오름차순 정렬
      calculated.sort((a, b) => a.distance - b.distance);

      // 1) 가장 가까운 성지 1위
      const nearest = calculated[0];

      // 2) 동남쪽(손방) 방위에 있는 성지 중 최적 1위
      const seStores = calculated.filter(s => s.isSoutheast);
      const recommendedSE = seStores.length > 0 ? seStores[0] : calculated[0];

      // UI 카드에 반영
      const recGrid = document.getElementById('recStoreGrid');
      if (recGrid) recGrid.style.display = 'grid';

      const nearestName = document.getElementById('nearestHolyName');
      const nearestMeta = document.getElementById('nearestHolyMeta');
      const nearestLink = document.getElementById('nearestHolyLink');

      if (nearestName && nearest) {{
        nearestName.innerText = `${{nearest.name}} (${{nearest.region}})`;
        nearestMeta.innerHTML = hasRealLocation 
          ? `📍 거리 <strong>${{nearest.distance}}km</strong> | ${{nearest.count}} 당첨<br>방위: ${{nearest.dirName}}`
          : `🏆 역대 ${{nearest.count}} 배출 명당<br>${{nearest.addr}}`;
        nearestLink.href = 'https://map.kakao.com/link/to/' + encodeURIComponent(nearest.name + '(로또명당)') + ',' + nearest.lat + ',' + nearest.lng;
      }}

      const seName = document.getElementById('southeastHolyName');
      const seMeta = document.getElementById('southeastHolyMeta');
      const seLink = document.getElementById('southeastHolyLink');

      if (seName && recommendedSE) {{
        seName.innerText = `${{recommendedSE.name}} (${{recommendedSE.region}})`;
        seMeta.innerHTML = hasRealLocation
          ? `🧭 방위각 <strong>${{recommendedSE.bearing}}° (${{recommendedSE.dirName}})</strong><br>거리 ${{recommendedSE.distance}}km | ${{recommendedSE.count}}`
          : `✨ 동남쪽 방위 명당<br>역대 ${{recommendedSE.count}} 배출`;
        seLink.href = 'https://map.kakao.com/link/to/' + encodeURIComponent(recommendedSE.name + '(로또명당)') + ',' + recommendedSE.lat + ',' + recommendedSE.lng;
      }}

      // 동남쪽에 위치한 마커는 지도상에서 특별 하이라이트 뱃지 클래스 추가
      holyMarkers.forEach(hm => {{
        const pinEl = document.getElementById('holy-pin-' + encodeURIComponent(hm.store.name));
        if (pinEl) {{
          const isSE = (recommendedSE && hm.store.name === recommendedSE.name);
          if (isSE) {{
            pinEl.classList.add('southeast-pin');
            pinEl.innerHTML = '⭐';
          }} else {{
            pinEl.classList.remove('southeast-pin');
            pinEl.innerHTML = '🏆';
          }}
        }}
      }});
    }}

    function showAllHolySpots() {{
      if (!lottoMap || holyMarkers.length === 0) return;
      const bounds = L.latLngBounds(HOLY_STORES.map(s => [s.lat, s.lng]));
      if (currentCoords) {{
        bounds.extend([currentCoords.lat, currentCoords.lng]);
      }}
      lottoMap.fitBounds(bounds, {{ padding: [35, 35] }});
      showToast('전국 16대 1등 성지 지도로 전환되었습니다! 🏆');
    }}

    // 초기화 실행
    checkLockStatus();
    checkAlarmStatus();
    renderTypes();
    renderStatsRanks();
    setTimeout(() => {{
      initLottoMap();
    }}, 200);
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
