import pandas as pd

# =========================
# 1. cohort 읽기
# =========================

cohort = pd.read_csv(
    "cohort_base.csv",
    usecols=[
        "subject_id",
        "hadm_id",
        "stay_id",
        "intime",
        "window_end"
    ]
)

cohort["intime"] = pd.to_datetime(
    cohort["intime"]
)

cohort["window_end"] = pd.to_datetime(
    cohort["window_end"]
)


# 분석 대상 stay_id
valid_stays = set(
    cohort["stay_id"]
)


# =========================
# 2. 사용할 Vital itemid
# =========================

vital_itemids = [
    220045,  # Heart Rate
    220210,  # Respiratory Rate

    220179,  # NIBP systolic
    220180,  # NIBP diastolic
    220181,  # NIBP mean

    220277,  # SpO2

    223761,  # Temperature Fahrenheit
    223762   # Temperature Celsius
]


# =========================
# 3. chartevents chunk 단위 읽기
# =========================

chunksize = 1_000_000

selected_chunks = []

for i, chunk in enumerate(
    pd.read_csv(
        "chartevents.csv",
        usecols=[
            "subject_id",
            "hadm_id",
            "stay_id",
            "charttime",
            "itemid",
            "valuenum",
            "valueuom"
        ],
        chunksize=chunksize
    )
):

    print(f"chunk {i + 1} 처리 중...")

    # 사용할 ICU stay만
    chunk = chunk[
        chunk["stay_id"].isin(valid_stays)
    ]

    # 사용할 Vital만
    chunk = chunk[
        chunk["itemid"].isin(vital_itemids)
    ]

    if len(chunk) > 0:
        selected_chunks.append(chunk)


# =========================
# 4. 합치기
# =========================

chart = pd.concat(
    selected_chunks,
    ignore_index=True
)

print("\nitemid 필터링 후:")
print(chart.shape)


# =========================
# 5. 시간 변환
# =========================

chart["charttime"] = pd.to_datetime(
    chart["charttime"],
    errors="coerce"
)


# =========================
# 6. cohort와 연결
# =========================

chart = chart.merge(
    cohort[
        [
            "stay_id",
            "intime",
            "window_end"
        ]
    ],
    on="stay_id",
    how="inner"
)


# =========================
# 7. ICU 입실 후 24시간만
# =========================

chart = chart[
    (chart["charttime"] >= chart["intime"]) &
    (chart["charttime"] < chart["window_end"])
].copy()


print("\n첫 24시간 필터링 후:")
print(chart.shape)


# =========================
# 8. itemid별 개수 확인
# =========================

print("\nitemid별 측정 횟수:")
print(
    chart["itemid"]
    .value_counts()
)


print("\nitemid별 측정 ICU stay 수:")
print(
    chart
    .groupby("itemid")["stay_id"]
    .nunique()
    .sort_values(ascending=False)
)


# =========================
# 9. 저장
# =========================

chart.to_csv(
    "chartevents_24h_raw.csv",
    index=False
)

print(
    "\nchartevents_24h_raw.csv 저장 완료!"
)