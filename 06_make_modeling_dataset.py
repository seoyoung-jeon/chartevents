import pandas as pd


# =========================
# 1. 파일 읽기
# =========================

print("파일 읽는 중...")

cohort = pd.read_csv(
    "cohort_base.csv"
)

vital = pd.read_csv(
    "vital_features.csv"
)

lab = pd.read_csv(
    "lab_features.csv"
)

print("cohort:", cohort.shape)
print("vital:", vital.shape)
print("lab:", lab.shape)


# =========================
# 2. stay_id 중복 확인
# =========================

print("\nstay_id 중복 확인")

print(
    "cohort 중복:",
    cohort["stay_id"].duplicated().sum()
)

print(
    "vital 중복:",
    vital["stay_id"].duplicated().sum()
)

print(
    "lab 중복:",
    lab["stay_id"].duplicated().sum()
)


# =========================
# 3. cohort + vital 병합
# =========================

df = cohort.merge(
    vital,
    on="stay_id",
    how="left"
)

print("\nVital 병합 후:")
print(df.shape)


# =========================
# 4. lab 병합
# =========================

df = df.merge(
    lab,
    on="stay_id",
    how="left"
)

print("\nLab 병합 후:")
print(df.shape)


# =========================
# 5. 행 수 확인
# =========================
# left join이므로
# cohort 행 수와 같아야 정상

print("\n원래 cohort 행 수:")
print(len(cohort))

print("최종 데이터 행 수:")
print(len(df))

if len(df) == len(cohort):
    print("행 수 정상: cohort 유지됨")
else:
    print("주의: merge 후 행 수가 달라졌습니다.")


# =========================
# 6. 사용하지 않을 중간 열 제거
# =========================
# 아래 열들은 모델 feature로 사용하지 않음
# 단 subject_id / hadm_id / stay_id는
# train/val/test 분리 전까지는 유지

drop_cols = [
    "anchor_age",
    "anchor_year",
    "dod",
    "deathtime",
    "death_days",
    "outtime",
    "window_end",
    "icu_hours",
    "hours_to_death"
]

# 실제로 존재하는 열만 제거
drop_cols = [
    col
    for col in drop_cols
    if col in df.columns
]

df = df.drop(
    columns=drop_cols
)

print("\n중간 열 제거 후:")
print(df.shape)


# =========================
# 7. lab count feature 제거
# =========================
# 첫 모델에서는 측정 횟수는 제외
# 나중에 별도 실험 가능

count_cols = [
    col
    for col in df.columns
    if col.endswith("_count")
]

print("\n제거할 count feature 수:")
print(len(count_cols))

df = df.drop(
    columns=count_cols
)


# =========================
# 8. std 사용 여부
# =========================
# 첫 baseline을 단순하게 하려면
# std도 제외 가능
#
# 아래는 기본적으로 유지하는 코드
# 만약 std를 빼고 싶으면 아래 주석 해제

# std_cols = [
#     col
#     for col in df.columns
#     if col.endswith("_std")
# ]
#
# df = df.drop(columns=std_cols)


# =========================
# 9. 성별 확인
# =========================

print("\nGender 분포:")
print(
    df["gender"]
    .value_counts(
        dropna=False
    )
)


# =========================
# 10. 라벨 확인
# =========================

print("\n28일 사망 분포:")
print(
    df["mortality_28d"]
    .value_counts()
)

print("\n28일 사망 비율:")
print(
    df["mortality_28d"]
    .value_counts(
        normalize=True
    )
)


# =========================
# 11. 결측률 계산
# =========================

feature_missing = (
    df
    .isna()
    .mean()
    .mul(100)
    .sort_values(
        ascending=False
    )
)

print("\n결측률 상위 30개:")
print(
    feature_missing.head(30)
)


# =========================
# 12. 완전히 비어있는 열 확인
# =========================

all_missing_cols = [
    col
    for col in df.columns
    if df[col].isna().all()
]

print("\n100% 결측 열:")
print(all_missing_cols)

if len(all_missing_cols) > 0:

    df = df.drop(
        columns=all_missing_cols
    )


# =========================
# 13. feature 개수 확인
# =========================

id_cols = [
    "subject_id",
    "hadm_id",
    "stay_id"
]

target_col = "mortality_28d"

non_feature_cols = (
    id_cols
    + [target_col]
)

feature_cols = [
    col
    for col in df.columns
    if col not in non_feature_cols
]

print("\n모델 후보 feature 수:")
print(len(feature_cols))

print("\n모델 후보 feature:")
print(feature_cols)


# =========================
# 14. 최종 데이터 앞부분 확인
# =========================

print("\n최종 데이터 앞 5개:")
print(
    df.head()
)


# =========================
# 15. 저장
# =========================

df.to_csv(
    "modeling_dataset.csv",
    index=False
)

print("\nmodeling_dataset.csv 저장 완료!")