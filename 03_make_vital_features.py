import pandas as pd
import numpy as np

print("chartevents_24h_raw.csv 읽는 중...")

df = pd.read_csv(
    "chartevents_24h_raw.csv",
    usecols=[
        "stay_id",
        "itemid",
        "valuenum",
        "valueuom"
    ]
)

print("원본 크기:", df.shape)


# =========================
# 1. 변수 이름 매핑
# =========================

item_map = {
    220045: "HR",
    220210: "RR",
    220179: "SBP",
    220180: "DBP",
    220181: "MAP",
    220277: "SpO2",
    223761: "Temp_F",
    223762: "Temp_C"
}

df["variable"] = df["itemid"].map(item_map)


# =========================
# 2. 체온 F → C 변환
# =========================

mask_f = df["itemid"] == 223761

df.loc[mask_f, "valuenum"] = (
    (df.loc[mask_f, "valuenum"] - 32)
    * 5 / 9
)

# F와 C를 하나의 Temperature 변수로 합침
df.loc[
    df["itemid"].isin([223761, 223762]),
    "variable"
] = "Temp"


# =========================
# 3. 명백한 이상치 처리
# =========================
# 범위는 생리적으로 불가능한 값 제거 목적
# '정상범위'가 아니라 'plausible range'

ranges = {
    "HR":   (20, 300),
    "RR":   (3, 80),
    "SBP":  (40, 300),
    "DBP":  (20, 200),
    "MAP":  (20, 250),
    "SpO2": (40, 100),
    "Temp": (25, 45)
}

for var, (low, high) in ranges.items():

    mask = (
        (df["variable"] == var)
        &
        (
            (df["valuenum"] < low)
            |
            (df["valuenum"] > high)
        )
    )

    print(
        f"{var} 이상치:",
        mask.sum()
    )

    df.loc[mask, "valuenum"] = np.nan


# =========================
# 4. 결측값 제거
# =========================
# summary 계산 전 숫자가 없는 측정행만 제거
# 환자 전체를 삭제하는 것이 아님

df = df.dropna(
    subset=["valuenum"]
)


# =========================
# 5. stay_id + 변수별 요약
# =========================

summary = (
    df
    .groupby(
        ["stay_id", "variable"]
    )["valuenum"]
    .agg(
        ["mean", "min", "max", "std"]
    )
    .reset_index()
)

print("\n요약 후:")
print(summary.head())


# =========================
# 6. wide format으로 변환
# =========================

wide = summary.pivot(
    index="stay_id",
    columns="variable"
)

# MultiIndex 열 이름 정리
wide.columns = [
    f"{variable}_{stat}"
    for stat, variable in wide.columns
]

wide = wide.reset_index()


# =========================
# 7. 결과 확인
# =========================

print("\n최종 vital feature 크기:")
print(wide.shape)

print("\n열 이름:")
print(wide.columns.tolist())

print("\n앞 5개:")
print(wide.head())


# =========================
# 8. 결측률 확인
# =========================

missing = (
    wide.isna().mean() * 100
).sort_values(
    ascending=False
)

print("\n결측률(%):")
print(missing)


# =========================
# 9. 저장
# =========================

wide.to_csv(
    "vital_features.csv",
    index=False
)

print("\nvital_features.csv 저장 완료!")