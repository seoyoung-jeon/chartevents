import pandas as pd
import numpy as np


# =========================
# 1. 데이터 읽기
# =========================

print("labevents_24h_raw.csv 읽는 중...")

df = pd.read_csv(
    "labevents_24h_raw.csv",
    usecols=[
        "stay_id",
        "itemid",
        "valuenum",
        "valueuom",
        "variable"
    ]
)

print("원본 크기:")
print(df.shape)


# =========================
# 2. valuenum 숫자형 확인
# =========================

df["valuenum"] = pd.to_numeric(
    df["valuenum"],
    errors="coerce"
)


# =========================
# 3. 변수별 이상치 범위 설정
# =========================
# 정상범위가 아니라
# "생리적으로 매우 비현실적인 값"을 제거하기 위한 범위
#
# 최종 보고서에서는 반드시
# 참고문헌/기존 MIMIC preprocessing 기준을 근거로 정리하는 것을 추천

ranges = {
    "Creatinine":  (0.1, 30),
    "Glucose":     (20, 1500),
    "Sodium":      (90, 200),
    "Potassium":   (1.0, 15),
    "Bicarbonate": (2, 60),
    "AnionGap":    (0, 80),

    "Hemoglobin":  (2, 25),
    "Hematocrit":  (5, 75),
    "WBC":         (0.1, 200),
    "Platelet":    (1, 2000),

    "Bilirubin":   (0.1, 80),
    "AST":         (1, 20000),
    "ALT":         (1, 20000),
    "INR":         (0.5, 20),
    "Lactate":     (0.2, 40)
}


# =========================
# 4. 이상치 처리
# =========================

print("\n이상치 개수:")

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
        f"{var}: {mask.sum()}"
    )

    # 행 전체 삭제 X
    # 잘못된 값만 NaN
    df.loc[
        mask,
        "valuenum"
    ] = np.nan


# =========================
# 5. 숫자값 없는 측정행 제거
# =========================
# 환자를 삭제하는 것이 아니라
# 해당 검사 기록만 제외

before = len(df)

df = df.dropna(
    subset=["valuenum"]
)

after = len(df)

print("\nNaN 제거 전:", before)
print("NaN 제거 후:", after)
print(
    "제거된 측정행:",
    before - after
)


# =========================
# 6. stay_id + 검사별 요약
# =========================
# Lab은 측정 횟수가 적을 수 있으므로
# 우선 mean/min/max만 사용

summary = (
    df
    .groupby(
        [
            "stay_id",
            "variable"
        ]
    )["valuenum"]
    .agg(
        mean="mean",
        min="min",
        max="max",
        count="count"
    )
    .reset_index()
)


print("\n요약 결과:")
print(summary.head(20))


# =========================
# 7. wide format으로 변환
# =========================
# 현재:
#
# stay_id | variable | mean | min | max
#
# ↓
#
# stay_id | Creatinine_mean | Creatinine_min ...

feature_values = summary.pivot(
    index="stay_id",
    columns="variable",
    values=[
        "mean",
        "min",
        "max"
    ]
)


# MultiIndex 열 이름 정리
feature_values.columns = [
    f"{variable}_{stat}"
    for stat, variable in feature_values.columns
]

feature_values = (
    feature_values
    .reset_index()
)


# =========================
# 8. 측정 횟수 feature
# =========================
# 이건 선택사항
#
# 검사를 얼마나 자주 했는지도
# 환자 중증도와 관련될 수 있으므로
# 따로 저장해둘 수 있음

count_features = summary.pivot(
    index="stay_id",
    columns="variable",
    values="count"
)

count_features.columns = [
    f"{variable}_count"
    for variable in count_features.columns
]

count_features = (
    count_features
    .reset_index()
)


# =========================
# 9. 값 feature + count feature 병합
# =========================

lab_features = feature_values.merge(
    count_features,
    on="stay_id",
    how="left"
)


# =========================
# 10. 결과 확인
# =========================

print("\n최종 lab feature 크기:")
print(lab_features.shape)

print("\n열 이름:")
print(
    lab_features.columns.tolist()
)

print("\n앞 5개:")
print(
    lab_features.head()
)


# =========================
# 11. 결측률 확인
# =========================

missing_rate = (
    lab_features
    .isna()
    .mean()
    .mul(100)
    .sort_values(
        ascending=False
    )
)

print("\n결측률(%):")
print(missing_rate)


# =========================
# 12. 측정된 ICU stay 수 확인
# =========================

print("\nLab feature가 있는 ICU stay 수:")
print(
    lab_features["stay_id"]
    .nunique()
)


# =========================
# 13. 저장
# =========================

lab_features.to_csv(
    "lab_features.csv",
    index=False
)

print(
    "\nlab_features.csv 저장 완료!"
)