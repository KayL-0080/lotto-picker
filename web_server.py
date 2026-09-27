"""
로또 6/45 실시간 분석 및 추천 경량 웹 서버
파이썬 기본 내장 라이브러리(http.server)만으로 동작하여 외부 의존성 없음
"""

import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

# Windows 콘솔 인코딩 대응
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from analyzer import LottoAnalyzer
from crawler import HISTORY_JSON, load_cached_history, sync_lotto_data

PORT = 8088
DIR_PATH = os.path.dirname(os.path.abspath(__file__))

# 전역 분석기 캐시
cached_history = []
analyzer_instance = None


def init_analyzer():
    global cached_history, analyzer_instance
    history_dict = load_cached_history()
    if not history_dict:
        cached_history = sync_lotto_data()
    else:
        cached_history = [history_dict[r] for r in sorted(history_dict.keys())]
    analyzer_instance = LottoAnalyzer(cached_history)


class LottoHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/generate":
            global analyzer_instance
            if not analyzer_instance:
                init_analyzer()

            types = analyzer_instance.generate_all_5_types()
            stats = analyzer_instance.get_summary_statistics()
            last_item = analyzer_instance.history[-1]

            payload = {
                "success": True,
                "latest_item": last_item,
                "stats": stats,
                "types": types,
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/sync":
            global cached_history, analyzer_instance
            cached_history = sync_lotto_data()
            analyzer_instance = LottoAnalyzer(cached_history)

            payload = {
                "success": True,
                "message": f"최신 {analyzer_instance.latest_round}회차까지 동기화 완료되었습니다.",
                "latest_round": analyzer_instance.latest_round,
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            # index.html 등 정적 파일 제공
            file_name = "index.html" if path in ["/", "/index.html"] else path.lstrip("/")
            file_path = os.path.join(DIR_PATH, file_name)

            if os.path.exists(file_path) and os.path.isfile(file_path):
                content_type = "text/html; charset=utf-8"
                if file_name.endswith(".css"):
                    content_type = "text/css"
                elif file_name.endswith(".js"):
                    content_type = "application/javascript"
                elif file_name.endswith(".json"):
                    content_type = "application/json"

                with open(file_path, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 Not Found")


def run_server():
    init_analyzer()
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, LottoHandler)
    print(f"\n============================================================")
    print(f" [로또 6/45 5대 유형 분석기 대시보드 서버 가동]")
    print(f" • 접속 주소: http://localhost:{PORT}")
    print(f" • 종료하려면 창을 닫거나 Ctrl+C를 누르세요.")
    print(f"============================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
