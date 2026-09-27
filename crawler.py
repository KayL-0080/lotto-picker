"""
동행복권 6/45 로또 데이터 수집 모듈 (1회부터 최신 회차까지)
https://www.dhlottery.co.kr/lt645/result
"""

import json
import os
import re
import sys
import time
import urllib.request
from typing import Dict, List, Optional, Tuple

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HISTORY_JSON = os.path.join(DATA_DIR, "lotto_history.json")
HISTORY_CSV = os.path.join(DATA_DIR, "lotto_history.csv")


def get_latest_round_from_web() -> int:
    """동행복권 사이트 메인 결과 페이지에서 최신 회차 번호를 파싱합니다."""
    url = "https://www.dhlottery.co.kr/lt645/result"
    req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # id="ltEpsdDiv" 내 <button ... data-value="1243">
            matches = re.findall(r'class="option-il"[^>]*data-value="(\d+)"', html)
            if not matches:
                matches = re.findall(r'data-value="(\d+)"', html)
            if matches:
                rounds = [int(x) for x in matches if int(x) > 0]
                if rounds:
                    return max(rounds)
    except Exception as e:
        print(f"[경고] 최신 회차 웹 조회 실패: {e}", file=sys.stderr)
    return 0


def fetch_batch_from_api(
    cursor_round: Optional[int] = None, dir_mode: str = "center"
) -> List[Dict]:
    """
    동행복권 신규 API에서 10개 회차 정보를 가져옵니다.
    endpoint: /lt645/selectPstLt645InfoNew.do
    """
    if dir_mode == "center":
        url = f"https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do?srchDir=center&srchLtEpsd={cursor_round}"
    else:
        url = f"https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do?srchDir=older&srchCursorLtEpsd={cursor_round}"

    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(raw)
            if data.get("data") and data["data"].get("list"):
                return data["data"]["list"]
    except Exception as e:
        print(f"[오류] API 호출 실패 ({url}): {e}", file=sys.stderr)
    return []


def parse_round_item(item: Dict) -> Dict:
    """API 응답 항목을 표준 딕셔너리로 정규화합니다."""
    return {
        "round": int(item.get("ltEpsd", 0)),
        "date": str(item.get("ltRflYmd", "")),
        "numbers": sorted(
            [
                int(item["tm1WnNo"]),
                int(item["tm2WnNo"]),
                int(item["tm3WnNo"]),
                int(item["tm4WnNo"]),
                int(item["tm5WnNo"]),
                int(item["tm6WnNo"]),
            ]
        ),
        "bonus": int(item.get("bnsWnNo", 0)),
        "winner_count": int(item.get("rnk1WnNope", 0)),
        "first_prize": int(item.get("rnk1WnAmt", 0)),
        "total_sell_amount": int(item.get("wholEpsdSumNtslAmt", 0)),
    }


def load_cached_history() -> Dict[int, Dict]:
    """기존 저장된 로컬 JSON 캐시를 불러옵니다."""
    if not os.path.exists(HISTORY_JSON):
        return {}
    try:
        with open(HISTORY_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(item["round"]): item for item in data}
    except Exception as e:
        print(f"[경고] 로컬 캐시 로드 실패: {e}", file=sys.stderr)
        return {}


def save_history(history: Dict[int, Dict]):
    """수집된 전체 데이터를 JSON 및 CSV로 저장합니다."""
    os.makedirs(DATA_DIR, exist_ok=True)
    sorted_items = [history[r] for r in sorted(history.keys())]

    with open(HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(sorted_items, f, ensure_ascii=False, indent=2)

    with open(HISTORY_CSV, "w", encoding="utf-8") as f:
        f.write("round,date,num1,num2,num3,num4,num5,num6,bonus,winner_count,first_prize\n")
        for item in sorted_items:
            n = item["numbers"]
            f.write(
                f"{item['round']},{item['date']},{n[0]},{n[1]},{n[2]},{n[3]},{n[4]},{n[5]},"
                f"{item['bonus']},{item['winner_count']},{item['first_prize']}\n"
            )


def sync_lotto_data(progress_callback=None) -> List[Dict]:
    """
    1회부터 최신 회차까지 모든 로또 번호를 수집/동기화합니다.
    이미 캐시된 회차는 건너뛰고 누락된 회차만 똑똑하게 가져옵니다.
    """
    history = load_cached_history()
    latest_web_round = get_latest_round_from_web()
    if latest_web_round == 0 and history:
        latest_web_round = max(history.keys())
    elif latest_web_round == 0:
        latest_web_round = 1243  # fallback

    missing_rounds = set(range(1, latest_web_round + 1)) - set(history.keys())

    if not missing_rounds and history:
        print(f"[완료] 이미 최신 회차({latest_web_round}회)까지 모두 저장되어 있습니다.")
        return [history[r] for r in sorted(history.keys())]

    print(f"[동기화] 대상: 1회 ~ {latest_web_round}회 (누락 회차: {len(missing_rounds)}개)")

    # 효율적 수집: 최신 회차부터 역순으로 older 커서 페이징
    cursor = latest_web_round
    retry_count = 0

    while cursor >= 1:
        # 이 커서 기준으로 10개(cursor ~ cursor-9) 중 누락된 것이 없으면 스킵 가능
        block = set(range(max(1, cursor - 9), cursor + 1))
        if block.issubset(history.keys()):
            cursor = min(block) - 1
            continue

        raw_list = fetch_batch_from_api(cursor, dir_mode="center")
        if not raw_list:
            retry_count += 1
            if retry_count > 3:
                print(f"[경고] {cursor}회차 조회 실패로 다음으로 진행합니다.")
                cursor -= 10
                retry_count = 0
            time.sleep(0.5)
            continue

        min_in_batch = cursor
        new_count = 0
        for item in raw_list:
            parsed = parse_round_item(item)
            r = parsed["round"]
            min_in_batch = min(min_in_batch, r)
            if r not in history:
                history[r] = parsed
                new_count += 1

        if progress_callback:
            progress_callback(len(history), latest_web_round)
        else:
            print(f"  -> 수집 진행률: {len(history)} / {latest_web_round} 회차 (현재: {min_in_batch}회차)...", end="\r")

        if min_in_batch <= 1:
            break
        cursor = min_in_batch - 1
        time.sleep(0.05)  # 서버 부하 방지용 짧은 딜레이

    print()
    save_history(history)
    print(f"[완료] 총 {len(history)}개 회차 데이터 저장 완료 ({HISTORY_JSON})")
    return [history[r] for r in sorted(history.keys())]


if __name__ == "__main__":
    sync_lotto_data()
