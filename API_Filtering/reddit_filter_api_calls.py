# # save as: filter_com_only.py
# import csv, re
# from pathlib import Path

# # 입력/출력 경로 (네 경로로 기본 설정)
# IN_PATH  = Path("/Users/yoonhyejun/Desktop/Android/Code/IFDS/reddit_api_calls.csv")
# OUT_PATH = Path("/Users/yoonhyejun/Desktop/Android/Code/IFDS/reddit_all_call_candidates.csv")

# # 'Lcom/' 또는 'com/' 모두 매칭
# RX = re.compile(r'\bL?com/')

# def row_has_com(row: dict, fieldnames: list[str]) -> bool:
#     # 존재하는 모든 필드의 값을 합쳐 검색 (필드 그대로 유지)
#     hay = " ".join((row.get(k) or "") for k in fieldnames)
#     return bool(RX.search(hay))

# with IN_PATH.open("r", encoding="utf-8", errors="replace", newline="") as fin, \
#      OUT_PATH.open("w", encoding="utf-8", errors="replace", newline="") as fout:

#     reader = csv.DictReader(fin)
#     writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
#     writer.writeheader()

#     for row in reader:
#         if row_has_com(row, reader.fieldnames):
#             writer.writerow(row)


# save as: extract_reddit_fullcall_txt.py
import csv, re
from pathlib import Path

# ===== 경로 설정 (필요시 수정) =====
ROOT = Path("/Users/yoonhyejun/Desktop/Android/Code/IFDS")
IN_CSV = ROOT / "reddit_all_call_candidates.csv"
OUT_SINK_TXT = ROOT / "reddit_sinks.txt"
OUT_SOURCE_TXT = ROOT / "reddit_sources.txt"

# ===== Reddit 전용 분류 (full_call 문자열만 사용) =====
# 1) Reddit 코드 주체 힌트(선택): full_call 내에 caller가 Lcom/reddit/로 표기되는 형식이면 오탐↓
RX_CALLER_REDDIT_HINT = re.compile(r'^Lcom/reddit/.*?->', re.IGNORECASE)

# 2) SINK: 네트워크/파일쓰기/로그·프로파일러/Reddit 도메인 등 "유출/기록/쓰기" 행위
RX_SINK = re.compile(
    r'(?:'
    # Reddit 도메인(아주 강력)
    r'oauth\.reddit\.com|api\.reddit\.com|i\.redd\.it|v\.redd\.it|packaged-media\.redd\.it|'
    # 네트워크 라이브러리/클래스 흔적
    r'okhttp3|retrofit2|java/net/HttpURLConnection|HttpUrlConnection|org/apache/http|'
    r'com/google/firebase/perf/network|'
    # 파일/버퍼/IO (쓰기 계열 키워드 우선)
    r'FileOutputStream|FileWriter|RandomAccessFile|openFileOutput|BufferedSink|okio/(?:Sink|BufferedSink)|'
    # 로깅/프로파일/크래시
    r'android/util/Log|crashlytics|com/bugsnag/|com/datadog/|com/facebook/profilo/logger'
    r')',
    re.IGNORECASE
)

# 3) SOURCE: 민감한 값/식별자/토큰을 '반환'하는 계열
RX_SOURCE = re.compile(
    r'(?:'
    r'android/provider/Settings\$Secure;->getString|'
    r'TelephonyManager;->get(DeviceId|Imei|Meid)|'
    r'AdvertisingIdClient|'
    r'AccountManager;->getAccounts|'
    r'SharedPreferences;->get'
    r')',
    re.IGNORECASE
)

def main():
    sinks = set()
    sources = set()

    with IN_CSV.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        if "full_call" not in (reader.fieldnames or []):
            raise SystemExit("ERROR: 'full_call' 컬럼이 CSV에 없습니다.")

        for row in reader:
            full = (row.get("full_call") or "").strip()
            if not full:
                continue

            # (선택) Reddit caller 힌트가 있으면 가산점처럼 활용하고 싶다면 아래 주석을 해제
            # is_reddit_caller = bool(RX_CALLER_REDDIT_HINT.search(full))
            # 여기서는 full_call만으로 분류하므로 필수 조건으로 두지 않고,
            # 패턴 그 자체(RX_SINK/RX_SOURCE)로 판단합니다.

            is_sink = bool(RX_SINK.search(full))
            is_source = bool(RX_SOURCE.search(full))

            # 둘 다 매칭될 수 있는데, 보통 SINK 우선 분류가 깔끔함(필요시 정책 바꿔도 됨)
            if is_sink and not is_source:
                sinks.add(full)
            elif is_source and not is_sink:
                sources.add(full)
            elif is_sink and is_source:
                # 충돌시 우선순위: SINK
                sinks.add(full)
            # 둘 다 아니면 버림(OTHER)

    # 정렬 후 저장
    OUT_SINK_TXT.write_text("\n".join(sorted(sinks)), encoding="utf-8")
    OUT_SOURCE_TXT.write_text("\n".join(sorted(sources)), encoding="utf-8")

if __name__ == "__main__":
    main()
