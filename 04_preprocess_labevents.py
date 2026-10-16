import pandas as pd

# =========================
# 1. cohort 읽기
# =========================

print("cohort_base.csv 읽는 중...")

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
    cohort["intime"],
    errors="coerce"
)

cohort["window_end"] = pd.to_datetime(
    cohort["window_end"],
    errors="coerce"
)

print("cohort 크기:", cohort.shape)


# =========================
# 2. 사용할 Lab itemid
# =========================

lab_itemids = [
    50912,  # Creatinine
    50931,  # Glucose
    50983,  # Sodium
    50971,  # Potassium
    50882,  # Bicarbonate
    50868,  # Anion Gap

    51222,  # Hemoglobin
    51221,  # Hematocrit
    51301,  # White Blood Cells
    51265,  # Platelet Count

    50885,  # Bilirubin, Total
    50878,  # AST
    50861,  # ALT
    51237,  # INR
    50813   # Lactate
]


# =========================
# 3. cohort의 입원 ID 준비
# =========================

valid_hadm_ids = set(
    cohort["hadm_id"]
    .dropna()
    .astype(int)
)


# =========================
# 4. labevents를 chunk 단위로 읽기
# =========================

chunksize = 1_000_000

selected_chunks = []

print("\nlabevents 읽기 시작...")

for i, chunk in enumerate(
    pd.read_csv(
        "labevents.csv",
        usecols=[
            "subject_id",
            "hadm_id",
            "itemid",
            "charttime",
            "valuenum",
            "valueuom"
        ],
        chunksize=chunksize
    )
):

    print(f"chunk {i + 1} 처리 중...")

    # -------------------------
    # hadm_id가 없는 lab 제거
    # -------------------------

    chunk = chunk[
        chunk["hadm_id"].notna()
    ].copy()

    if len(chunk) == 0:
        continue

    # hadm_id를 cohort와 같은 타입으로
    chunk["hadm_id"] = (
        chunk["hadm_id"]
        .astype(int)
    )

    # -------------------------
    # cohort 입원만 선택
    # -------------------------

    chunk = chunk[
        chunk["hadm_id"].isin(
            valid_hadm_ids
        )
    ]

    # -------------------------
    # 사용할 Lab만 선택
    # -------------------------

    chunk = chunk[
        chunk["itemid"].isin(
            lab_itemids
        )
    ]

    if len(chunk) > 0:
        selected_chunks.append(chunk)


# =========================
# 5. 필터링된 chunk 합치기
# =========================

if len(selected_chunks) == 0:
    raise ValueError(
        "선택된 labevents 데이터가 없습니다."
    )

labs = pd.concat(
    selected_chunks,
    ignore_index=True
)

print("\nitemid + cohort 필터링 후:")
print(labs.shape)


# =========================
# 6. 검사시간 datetime 변환
# =========================

labs["charttime"] = pd.to_datetime(
    labs["charttime"],
    errors="coerce"
)


# =========================
# 7. cohort와 연결
# =========================
# 중요:
# 같은 hadm_id 안에 ICU stay가 여러 개 있을 수 있으므로
# subject_id + hadm_id를 사용한다.

labs = labs.merge(
    cohort[
        [
            "subject_id",
            "hadm_id",
            "stay_id",
            "intime",
            "window_end"
        ]
    ],
    on=[
        "subject_id",
        "hadm_id"
    ],
    how="inner"
)


print("\ncohort merge 후:")
print(labs.shape)


# =========================
# 8. ICU 입실 후 첫 24시간만
# =========================

labs = labs[
    (labs["charttime"] >= labs["intime"])
    &
    (labs["charttime"] < labs["window_end"])
].copy()


print("\n첫 24시간 필터링 후:")
print(labs.shape)


# =========================
# 9. itemid별 측정 횟수 확인
# =========================

print("\nitemid별 측정 횟수:")

print(
    labs["itemid"]
    .value_counts()
)


# =========================
# 10. itemid별 측정 ICU stay 수
# =========================

print("\nitemid별 측정 ICU stay 수:")

print(
    labs
    .groupby("itemid")["stay_id"]
    .nunique()
    .sort_values(
        ascending=False
    )
)


# =========================
# 11. itemid 이름 확인용
# =========================

lab_names = {
    50912: "Creatinine",
    50931: "Glucose",
    50983: "Sodium",
    50971: "Potassium",
    50882: "Bicarbonate",
    50868: "AnionGap",

    51222: "Hemoglobin",
    51221: "Hematocrit",
    51301: "WBC",
    51265: "Platelet",

    50885: "Bilirubin",
    50878: "AST",
    50861: "ALT",
    51237: "INR",
    50813: "Lactate"
}

labs["variable"] = (
    labs["itemid"]
    .map(lab_names)
)


print("\n검사별 측정 횟수:")

print(
    labs["variable"]
    .value_counts()
)


# =========================
# 12. 단위 확인
# =========================

print("\n검사별 단위:")

print(
    labs
    .groupby("variable")["valueuom"]
    .value_counts()
)


# =========================
# 13. 저장
# =========================

labs.to_csv(
    "labevents_24h_raw.csv",
    index=False
)

print(
    "\nlabevents_24h_raw.csv 저장 완료!"
)