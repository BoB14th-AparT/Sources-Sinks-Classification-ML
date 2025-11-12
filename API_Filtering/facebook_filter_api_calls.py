# # save as: filter_com_rows.py
# import csv, re
# from pathlib import Path

# IN_PATH  = Path("/Users/yoonhyejun/Desktop/Android/Code/IFDS/api_calls.csv")
# OUT_PATH = Path("/Users/yoonhyejun/Desktop/Android/Code/IFDS/facebook_all_call_candidates.csv")

# # 'Lcom/'과 'com/' 모두 잡기
# RX = re.compile(r'\bL?com/')

# # 주요 컬럼 우선 검사, 없으면 전체 컬럼 검사
# PRIORITY_COLS = ["caller_class", "called_class", "descriptor", "full_call"]

# with IN_PATH.open("r", encoding="utf-8", newline="") as fin, \
#      OUT_PATH.open("w", encoding="utf-8", newline="") as fout:

#     reader = csv.DictReader(fin)
#     writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
#     writer.writeheader()

#     # 실제 존재하는 컬럼만 사용, 하나도 없으면 전체 검사
#     cols = [c for c in PRIORITY_COLS if c in reader.fieldnames]
#     check_all = not cols

#     for row in reader:
#         if check_all:
#             hay = " ".join((row.get(k) or "") for k in reader.fieldnames)
#             ok = bool(RX.search(hay))
#         else:
#             ok = any(RX.search(row.get(c) or "") for c in cols)
#         if ok:
#             writer.writerow(row)



# save as: autolabel_fb_calls.py
import csv, re
from pathlib import Path

ROOT = Path("/Users/yoonhyejun/Desktop/Android/Code/IFDS")
INCSV = ROOT / "facebook_all_call_candidates.csv"
OUT_SINKS = ROOT / "sinks_facebook.txt"
OUT_SOURCES = ROOT / "sources_facebook.txt"

# --- 규칙: 패키지 스코프 ---
PKG_RX = re.compile(r"^Lcom/facebook/")

# --- 키워드 기반 휴리스틱 ---
# SINK 후보 키워드 (method name)
SINK_METHOD_RX = re.compile(
    r"(log|trace|record|write|save|store|persist|append|open|put|apply|commit|"
    r"execSQL|insert|update|delete|send|post|upload|execute|enqueue|perform)",
    re.IGNORECASE
)
# SINK 클래스 힌트
SINK_CLASS_RX = re.compile(
    r"(profilo|logger|appevents|analytics|network|http|cache|disk|file|storage|prefs|preference)",
    re.IGNORECASE
)

# SOURCE 후보 키워드 (method name)
SOURCE_METHOD_RX = re.compile(r"(get.*Id|read.*Token|getToken|getUserId|getApplicationId)", re.IGNORECASE)
# SOURCE 클래스 힌트
SOURCE_CLASS_RX = re.compile(r"(AccessToken|FacebookSdk|Profile)", re.IGNORECASE)

# 시그니처 파싱용 (full_call이 있으면 우선)
SIG_RX = re.compile(r"(L[^;]+;)->([^\(]+)\(([^)]*)\)(.+)")  # Lcls;->method(args)ret

def row_to_sig(row):
    # full_call 우선, 없으면 조합
    fc = (row.get("full_call") or "").strip()
    if fc and SIG_RX.match(fc):
        return fc
    cls = (row.get("called_class") or "").strip()
    mtd = (row.get("called_method") or "").strip()
    desc = (row.get("descriptor") or "").strip()
    if cls and mtd and desc and cls.startswith("L"):
        return f"{cls}->{mtd}{desc}"
    return None

def classify(sig: str) -> str | None:
    """
    반환: 'SINK' | 'SOURCE' | None
    """
    m = SIG_RX.match(sig)
    if not m:
        return None
    cls, meth, args, ret = m.groups()
    if not PKG_RX.search(cls):
        return None  # com.facebook 외는 무시

    # SINK 우선 판정
    if SINK_CLASS_RX.search(cls) and SINK_METHOD_RX.search(meth):
        return "SINK"
    if SINK_METHOD_RX.search(meth) and ("V" in ret or "OutputStream" in args or "Writer" in args):
        return "SINK"

    # SOURCE 판정
    if SOURCE_CLASS_RX.search(cls) and SOURCE_METHOD_RX.search(meth):
        return "SOURCE"
    if SOURCE_METHOD_RX.search(meth) and "Ljava/lang/String;" in ret:
        return "SOURCE"

    return None

def main():
    sinks = set()
    sources = set()

    with INCSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sig = row_to_sig(row)
            if not sig:
                continue
            label = classify(sig)
            if label == "SINK":
                sinks.add(f"re:^{re.escape(sig)}$ -> _SINK_")
            elif label == "SOURCE":
                sources.add(f"re:^{re.escape(sig)}$ -> _SOURCE_")

    # 고정(핸드메이드) 규칙도 추가(초기 화이트리스트)
    sinks.update({
        r"re:^Lcom/facebook/profilo/logger/MultiBufferLogger;->.*\(.*\).*$ -> _SINK_",
        r"re:^Lcom/facebook/appevents/AppEventsLogger;->log.*\(.*\).*$ -> _SINK_",
        r"re:^Lcom/facebook/.+network.+;->(send|upload|post|put|execute|enqueue|perform).*\(.*\).*$ -> _SINK_",
        r"re:^Lcom/facebook/.+http.+;->(execute|enqueue|perform|send).*\(.*\).*$ -> _SINK_",
        r"re:^Lcom/facebook/.+cache.+;->(write|save|store|persist|put|append).*\(.*\).*$ -> _SINK_",
        r"re:^Lcom/facebook/.+disk.+;->(write|save|store|persist|put|append).*\(.*\).*$ -> _SINK_",
        r"re:^Lcom/facebook/.+file.+;->(write|save|store|persist|put|append|open).*\(.*\).*$ -> _SINK_",
        r"re:^Lcom/facebook/.+;->(execSQL|insert|update|delete)\(.*\).*$ -> _SINK_",
        r"re:^Lcom/facebook/.+SharedPreferences\$Editor;->(put.*|apply|commit)\(.*\).*$ -> _SINK_",
    })

    sources.update({
        r"re:^Lcom/facebook/AccessToken;->getToken\(\)Ljava/lang/String;$ -> _SOURCE_",
        r"re:^Lcom/facebook/AccessToken;->getUserId\(\)Ljava/lang/String;$ -> _SOURCE_",
        r"re:^Lcom/facebook/FacebookSdk;->getApplicationId\(\)Ljava/lang/String;$ -> _SOURCE_",
        r"re:^Lcom/facebook/.*;->get.*Id\(.*\)Ljava/lang/String;$ -> _SOURCE_",
        r"re:^Lcom/facebook/.*;->read.*Token.*\(.*\)Ljava/lang/String;$ -> _SOURCE_",
        r"re:^Lcom/facebook/Profile;->getId\(\)Ljava/lang/String;$ -> _SOURCE_",
        r"re:^Lcom/facebook/Profile;->getName\(\)Ljava/lang/String;$ -> _SOURCE_",
    })

    OUT_SINKS.write_text("\n".join(sorted(sinks)) + "\n", encoding="utf-8")
    OUT_SOURCES.write_text("\n".join(sorted(sources)) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()