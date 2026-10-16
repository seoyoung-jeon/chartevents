# MIMIC-IV 28일 사망예측 프로젝트 전처리 최종 정리

## 1. 프로젝트 목표

ICU 입실 후 **첫 24시간 동안 측정된 임상정보**를 이용하여 환자가 **ICU 입실 후 28일 이내 사망하는지** 예측한다.

관측 구간은 병원 입원시간(`admittime`)이 아니라 **ICU 입실시간(`icustays.intime`)** 을 기준으로 한다.

```text
ICU 입실시간 = intime
intime ≤ 측정시간 < intime + 24시간
```

## 2. 사용할 데이터 파일

| 파일 | 역할 |
|---|---|
| `icustays.csv.gz` | ICU stay와 ICU 입실시간 기준 설정 |
| `patients.csv.gz` | 나이, 성별, 사망일 |
| `admissions.csv.gz` | 입원 정보 및 병원 내 사망정보 확인 |
| `d_items.csv.gz` | `chartevents`의 `itemid` 의미 확인 |
| `chartevents.csv.gz` | Vital sign 추출 |
| `d_labitems.csv.gz` | `labevents`의 `itemid` 의미 확인 |
| `labevents.csv.gz` | 혈액검사 추출 |

`d_items`, `d_labitems`는 모델에 직접 넣는 데이터가 아니라 `itemid`의 의미를 확인하는 **사전(dictionary)** 역할을 한다.

## 3. `icustays` 전처리

### 사용할 열

```text
subject_id
hadm_id
stay_id
intime
```

선택적으로 `first_careunit`을 남길 수 있다.

### 모델 입력으로 사용하지 않을 열

```text
last_careunit
outtime
los
```

특히 `los`는 ICU 체류가 끝난 뒤 결정되는 값이므로 예측 feature로 사용하면 미래정보 누수(data leakage)가 생길 수 있다.

```python
icu["intime"] = pd.to_datetime(icu["intime"])
icu["window_end"] = icu["intime"] + pd.Timedelta(hours=24)
```

각 ICU stay에서 사용할 데이터는 다음 범위다.

```text
intime ≤ charttime < window_end
```

## 4. `patients` 전처리

### 사용할 열

```text
subject_id
gender
anchor_age
anchor_year
dod
```

역할은 다음과 같다.

```text
subject_id  → 다른 파일과 환자 연결
gender      → 모델 feature
anchor_age  → 나이 계산
anchor_year → 나이 계산
dod         → 28일 사망 라벨 생성
```

### ICU 입실 당시 나이 계산

```python
age = anchor_age + (intime.year - anchor_year)
```

성인 ICU 연구라면 필요에 따라 `age >= 18` 조건을 적용할 수 있다.

## 5. 28일 사망 라벨 생성

ICU 입실시간과 사망일을 비교한다.

```text
0 ≤ dod - intime ≤ 28일
```

이면 `mortality_28d = 1`, 그 외는 `mortality_28d = 0`으로 정의한다.

```python
df["mortality_28d"] = (
    (df["dod"] >= df["intime"]) &
    (df["dod"] <= df["intime"] + pd.Timedelta(days=28))
).astype(int)
```

`dod` 자체는 모델 입력 feature로 사용하지 않는다.

## 6. Vital sign itemid 선택

| 변수 | itemid | 실제 항목 |
|---|---:|---|
| Heart Rate | 220045 | Heart Rate |
| Respiratory Rate | 220210 | Respiratory Rate |
| 수축기 혈압 | 220179 | Non Invasive BP systolic |
| 이완기 혈압 | 220180 | Non Invasive BP diastolic |
| 평균 혈압 | 220181 | Non Invasive BP mean |
| SpO₂ | 220277 | O2 saturation pulseoxymetry |
| 체온 °C | 223762 | Temperature Celsius |
| 체온 °F | 223761 | Temperature Fahrenheit |
| GCS Eye | 220739 | GCS - Eye Opening |
| GCS Verbal | 223900 | GCS - Verbal Response |
| GCS Motor | 223901 | GCS - Motor Response |

선택적으로 동맥 혈압을 추가할 수 있다.

```text
220050 Arterial BP systolic
220051 Arterial BP diastolic
220052 Arterial BP mean
```

Alarm 관련 항목은 제외한다.

## 7. `chartevents` 전처리

### 사용할 열

```text
subject_id
hadm_id
stay_id
charttime
itemid
value
valuenum
valueuom
```

처리 순서는 다음과 같다.

1. 선택한 `itemid`만 남긴다.
2. `stay_id` 기준으로 `icustays`와 연결한다.
3. ICU 입실 후 첫 24시간만 남긴다.
4. 단위를 통일한다.
5. 명백한 오류값만 `NaN`으로 처리한다.
6. ICU stay별 summary feature를 생성한다.

## 8. Vital 단위 통일

서로 다른 변수끼리 단위가 다른 것은 문제없다.

```text
Heart Rate → bpm
Blood Pressure → mmHg
SpO₂ → %
Creatinine → mg/dL
```

문제는 같은 변수가 여러 단위로 기록되는 경우다. 대표적으로 체온은 °F와 °C가 있으므로 모두 Celsius로 통일한다.

```text
C = (F - 32) × 5 / 9
```

## 9. 이상치 처리

정상범위를 벗어난 값이라고 바로 삭제하면 안 된다. 예를 들어 `SBP = 70`, `SpO2 = 85`는 비정상이지만 ICU 환자에서 실제로 가능한 값이며 예측에 중요한 정보일 수 있다.

반면 다음처럼 명백히 불가능한 값은 오류로 보고 해당 값만 `NaN` 처리한다.

```text
Heart Rate = -20
SpO2 = 700
```

즉:

```text
비정상적인 실제 값 → 유지
명백한 측정 오류 → NaN
```

가능하면 환자 행 전체를 삭제하지 않는다.

## 10. Vital 반복 측정값 요약

첫 24시간 동안 같은 Vital이 여러 번 측정되므로 ICU stay별로 다음과 같이 요약한다.

```text
HR_mean
HR_min
HR_max
HR_std

SBP_mean
SBP_min
SBP_max

SpO2_mean
SpO2_min
SpO2_max
```

필요하면 `slope`를 추가할 수 있다.

## 11. GCS 전처리

GCS는 다음 세 구성요소로 이루어진다.

```text
220739 GCS Eye
223900 GCS Verbal
223901 GCS Motor
```

점수 범위는 다음과 같다.

```text
Eye    : 1~4
Verbal : 1~5
Motor  : 1~6
```

총점은 다음과 같다.

```text
GCS = Eye + Verbal + Motor
```

GCS 값은 문자열로 저장되어 있을 수 있으므로 숫자 점수로 변환하는 전처리가 필요할 수 있다.

## 12. 사용할 Lab itemid

| 변수 | itemid |
|---|---:|
| Creatinine | 50912 |
| Glucose | 50931 |
| Sodium | 50983 |
| Potassium | 50971 |
| Bicarbonate | 50882 |
| Anion Gap | 50868 |
| Hemoglobin | 51222 |
| Hematocrit | 51221 |
| WBC | 51301 |
| Platelet | 51265 |
| Bilirubin Total | 50885 |
| AST | 50878 |
| ALT | 50861 |
| INR | 51237 |
| Lactate | 50813 |

## 13. `labevents` 전처리

### 사용할 열

```text
subject_id
hadm_id
itemid
charttime
valuenum
valueuom
```

참고용으로 다음 열을 남길 수 있다.

```text
ref_range_lower
ref_range_upper
flag
```

처리 순서는 다음과 같다.

1. 사용할 `itemid`만 추출한다.
2. `subject_id + hadm_id` 기준으로 ICU 정보와 연결한다.
3. ICU 입실 후 첫 24시간만 남긴다.
4. 단위를 확인하고 필요하면 통일한다.
5. 명백한 오류값을 처리한다.
6. ICU stay별 summary feature를 생성한다.

## 14. Lab 반복 측정값 요약

예시는 다음과 같다.

```text
Creatinine_mean
Creatinine_min
Creatinine_max

Glucose_mean
Glucose_min
Glucose_max

WBC_mean
WBC_max

Lactate_mean
Lactate_max
```

Lab은 Vital보다 측정 횟수가 적을 수 있으므로 처음부터 모든 Lab에 `std`, `slope`를 만들 필요는 없다.

## 15. 최종 데이터셋 생성

모든 정보를 합친 후 **한 ICU stay = 한 행**이 되도록 만든다.

| stay_id | subject_id | age | gender | HR_mean | SBP_min | SpO2_min | Creatinine_max | WBC_mean | Lactate_max | mortality_28d |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| A | 1001 | 72 | M | 93 | 76 | 89 | 1.8 | 13.2 | 2.9 | 1 |
| B | 1002 | 55 | F | 78 | 108 | 96 | NaN | 7.8 | NaN | 0 |

모든 환자는 **동일한 열 구조**를 가져야 한다. 값이 없는 경우 해당 칸만 `NaN`으로 남긴다.

## 16. 결측률 확인

```python
missing_rate = (df.isna().mean() * 100).sort_values(ascending=False)
print(missing_rate)
```

결측률이 지나치게 높은 feature는 제외를 고려한다. 다만 `50% 이상이면 무조건 삭제` 같은 절대적인 기준은 없다.

## 17. Train / Validation / Test 분리

추천 비율:

```text
Train      70%
Validation 15%
Test       15%
```

가능하면 `subject_id` 기준으로 분리한다. 같은 환자의 여러 ICU stay가 Train과 Test에 동시에 들어가지 않도록 하기 위해서다.

## 18. 결측치 대체

데이터를 Train / Validation / Test로 나눈 후 수행한다.

### 수치형 변수

```text
HR
BP
SpO2
Creatinine
WBC
Lactate
```

→ Train set의 **median**으로 대체한다.

```text
전체 데이터의 median 사용 X
Train median 사용 O
```

### 범주형 변수

예를 들어 `gender`는 최빈값 등으로 처리할 수 있다.

## 19. 결측 indicator

MIMIC에서는 검사를 하지 않았다는 사실 자체가 정보일 수 있다.

```python
df["Lactate_missing"] = df["Lactate_max"].isna().astype(int)
```

그러면 모델에 `Lactate_max`와 `Lactate_missing`을 함께 넣을 수 있다.

## 20. Scaling

Scaling은 변수들의 숫자 크기를 비슷하게 맞추는 작업이다.

### Logistic Regression

`StandardScaler` 사용을 추천한다.

```python
scaler.fit(X_train)

X_train = scaler.transform(X_train)
X_val   = scaler.transform(X_val)
X_test  = scaler.transform(X_test)
```

주의:

```text
fit → Train만
transform → Train / Validation / Test
```

### Random Forest

일반적으로 scaling이 필요하지 않다.

### XGBoost

일반적으로 scaling이 필요하지 않다.

## 21. 모델에 넣지 말아야 하는 변수

```text
subject_id
hadm_id
stay_id

dod
deathtime
dischtime
discharge_location
hospital_expire_flag
los
```

`subject_id`, `hadm_id`, `stay_id`는 연결용 ID이고, 나머지 일부는 미래정보 또는 정답과 매우 가까운 정보이므로 data leakage를 일으킬 수 있다.

## 22. 사용할 모델

### Logistic Regression

- Baseline model
- Scaling 권장

### Random Forest

- 여러 Decision Tree의 결과를 종합해 예측
- Scaling은 일반적으로 필요하지 않음

### XGBoost

- 이전 Tree의 오류를 다음 Tree가 보완하며 학습
- `mean`, `min`, `max`, `std` 등으로 만들어진 tabular 데이터에 적합
- 이번 프로젝트의 주 모델로 사용 가능

## 23. 평가 지표

사망 환자가 생존 환자보다 적을 가능성이 높기 때문에 Accuracy만 사용하면 안 된다.

추천 지표:

```text
AUROC
AUPRC
Recall
Precision
F1-score
```

가능하면 다음도 추가한다.

```text
Sensitivity
Specificity
Calibration
```

## 24. 전체 전처리 파이프라인

```text
원본 7개 파일
        ↓
icustays로 ICU cohort 정의
        ↓
ICU intime 기준 설정
        ↓
patients 결합
        ↓
age / gender 생성
        ↓
28일 사망 라벨 생성
        ↓
d_items에서 Vital itemid 선정
        ↓
chartevents 첫 24시간 추출
        ↓
단위 통일
        ↓
명백한 오류값 → NaN
        ↓
Vital mean / min / max / std
        ↓
d_labitems에서 Lab itemid 선정
        ↓
labevents 첫 24시간 추출
        ↓
Lab mean / min / max
        ↓
stay_id당 한 행으로 통합
        ↓
결측률 확인
        ↓
subject_id 기준 Train / Validation / Test 분리
        ↓
Train 기준 결측치 대체
        ↓
필요한 모델만 Scaling
        ↓
Logistic Regression / Random Forest / XGBoost
        ↓
Validation set으로 모델 선택 및 튜닝
        ↓
Test set으로 최종 평가
```

## 25. 특히 주의해야 할 점

1. **ICU 입실 후 24시간만 사용한다.**
2. **미래정보를 feature로 넣지 않는다.**
3. **같은 환자를 Train과 Test에 동시에 넣지 않는다.**
4. **결측치 대체 기준은 Train에서만 계산한다.**
5. **이상치 때문에 환자 전체를 삭제하지 않는다.**
6. **모든 환자의 열 구조를 동일하게 맞춘다.**
7. **Test set은 최종 평가에만 사용한다.**
