# save as: filter_com_only.py
import csv, re
from pathlib import Path

# 입력/출력 경로 (네 경로로 기본 설정)
IN_PATH  = Path("/Users/yoonhyejun/Desktop/Android/Code/IFDS/kakaostory_api_calls.csv")
OUT_PATH = Path("/Users/yoonhyejun/Desktop/Android/Code/IFDS/kakaostory_all_call_candidates.csv")

# 'Lcom/' 또는 'com/' 모두 매칭
RX = re.compile(r'\bL?com/')

def row_has_com(row: dict, fieldnames: list[str]) -> bool:
    # 존재하는 모든 필드의 값을 합쳐 검색 (필드 그대로 유지)
    hay = " ".join((row.get(k) or "") for k in fieldnames)
    return bool(RX.search(hay))

with IN_PATH.open("r", encoding="utf-8", errors="replace", newline="") as fin, \
     OUT_PATH.open("w", encoding="utf-8", errors="replace", newline="") as fout:

    reader = csv.DictReader(fin)
    writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
    writer.writeheader()

    for row in reader:
        if row_has_com(row, reader.fieldnames):
            writer.writerow(row)
