import pandas as pd

# =========================
# 1. 데이터 읽기
# =========================

print("데이터 읽는 중...")

icu = pd.read_csv(
    "icustays.csv",
    usecols=[
        "subject_id",
        "hadm_id",
        "stay_id",
        "intime",
        "outtime"
    ]
)

patients = pd.read_csv(
    "patients.csv.gz",
    usecols=[
        "subject_id",
        "gender",
        "anchor_age",
        "anchor_year",
        "dod"
    ]
)

admissions = pd.read_csv(
    "admissions.csv.gz",
    usecols=[
        "subject_id",
        "hadm_id",
        "deathtime"
    ]
)

print("icustays:", icu.shape)
print("patients:", patients.shape)
print("admissions:", admissions.shape)


# =========================
# 2. 날짜/시간 형식 변환
# =========================

icu["intime"] = pd.to_datetime(
    icu["intime"],
    errors="coerce"
)

icu["outtime"] = pd.to_datetime(
    icu["outtime"],
    errors="coerce"
)

patients["dod"] = pd.to_datetime(
    patients["dod"],
    errors="coerce"
)

admissions["deathtime"] = pd.to_datetime(
    admissions["deathtime"],
    errors="coerce"
)


# =========================
# 3. ICU 첫 24시간 종료 시점 생성
# =========================

icu["window_end"] = (
    icu["intime"]
    + pd.Timedelta(hours=24)
)


# =========================
# 4. patients 연결
# =========================

cohort = icu.merge(
    patients,
    on="subject_id",
    how="left"
)


# =========================
# 5. admissions 연결
# =========================

cohort = cohort.merge(
    admissions,
    on=["subject_id", "hadm_id"],
    how="left"
)


# =========================
# 6. ICU 입실 당시 나이 계산
# =========================

cohort["age"] = (
    cohort["anchor_age"]
    + cohort["intime"].dt.year
    - cohort["anchor_year"]
)


# =========================
# 7. 성인 환자만 선택
# =========================

cohort = cohort[
    cohort["age"] >= 18
].copy()


# =========================
# 8. 28일 사망까지 걸린 기간
# =========================

cohort["death_days"] = (
    cohort["dod"].dt.normalize()
    - cohort["intime"].dt.normalize()
).dt.days


# =========================
# 9. 28일 사망 라벨 생성
# =========================

cohort["mortality_28d"] = (
    cohort["death_days"]
    .between(0, 28, inclusive="both")
    .astype(int)
)


# =========================
# 10. 결과 확인
# =========================

print("\n최종 cohort 크기:")
print(cohort.shape)

print("\n앞 10개:")
print(
    cohort[
        [
            "subject_id",
            "hadm_id",
            "stay_id",
            "intime",
            "window_end",
            "age",
            "gender",
            "dod",
            "mortality_28d"
        ]
    ].head(10)
)

print("\n28일 사망 분포:")
print(
    cohort["mortality_28d"]
    .value_counts()
)

print("\n28일 사망 비율:")
print(
    cohort["mortality_28d"]
    .value_counts(normalize=True)
)


# =========================
# 11. 중복 확인
# =========================

print("\n중복 stay_id 개수:")
print(
    cohort["stay_id"]
    .duplicated()
    .sum()
)


# =========================
# 12. 결측값 확인
# =========================

print("\n주요 열 결측값:")
print(
    cohort[
        [
            "subject_id",
            "hadm_id",
            "stay_id",
            "intime",
            "age",
            "gender",
            "dod"
        ]
    ].isna().sum()
)


# =========================
# 13. 저장
# =========================

cohort.to_csv(
    "cohort_base.csv",
    index=False
)

print("\ncohort_base.csv 저장")
