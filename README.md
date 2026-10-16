# MIMIC-IV 전처리

ICU 입실 후 첫 24시간의 활력징후와 검사값으로 28일 사망 예측용 데이터셋을 만듭니다.
첨부된 Python 파일 6개와 `MIMIC_data_processing.md`는 원본 그대로 보관했습니다.
현재 범위는 전처리이며 모델 학습·평가 코드는 포함하지 않습니다.

## 환경 설치

Python 3.12 기준입니다. 저장소 디렉터리에서 실행하세요.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 데이터 준비

MIMIC-IV 이용 권한을 가진 사용자가 허가된 작업 환경에 직접 데이터를 준비해야 합니다.
환자 데이터, 중간 결과, 최종 데이터셋을 GitHub에 올리지 마세요.
`.gitignore`는 CSV와 주요 데이터 형식을 제외하지만 `git add -f`로 우회하지 마세요.
코드가 환자 행을 화면에 출력하므로 실제 데이터 실행 로그도 공유하지 마세요.

아래 파일들을 저장소 안의 `data/` 폴더에 준비하세요. 현재 코드는 **실행한 폴더**에서 이 이름을 찾습니다.

- `icustays.csv` (MIMIC-IV `icu/icustays.csv.gz`를 압축 해제)
- `chartevents.csv` (`icu/chartevents.csv.gz`를 압축 해제)
- `labevents.csv` (`hosp/labevents.csv.gz`를 압축 해제)
- `patients.csv.gz` (`hosp/`에서 복사)
- `admissions.csv.gz` (`hosp/`에서 복사)

대용량 파일 압축 해제에는 충분한 디스크 공간이 필요합니다.
`d_items.csv.gz`, `d_labitems.csv.gz`는 항목 의미를 확인할 때 참고하며 현재 코드에서는 읽지 않습니다.

## 실행 순서

저장소 디렉터리에서 시작합니다.

```bash
mkdir -p data
cd data
../.venv/bin/python ../01_make_cohort.py
../.venv/bin/python ../02_chartevents_processing.py
../.venv/bin/python ../03_make_vital_features.py
../.venv/bin/python ../04_preprocess_labevents.py
../.venv/bin/python ../05_make_lab_features.py
../.venv/bin/python ../06_make_modeling_dataset.py
```

중간 CSV와 `modeling_dataset.csv`는 모두 `data/` 안에 생성됩니다.
재실행하면 같은 이름의 결과를 덮어쓰므로 필요한 결과는 먼저 별도로 보관하세요.

## 검증 범위 및 연구 시 확인할 사항

가상 데이터 검증은 코드 연결을 확인하며 실제 MIMIC 전체 처리나 임상적 타당성을 보장하지 않습니다.
대용량 이벤트 코드는 선택된 chunk를 메모리에 모으므로 전체 데이터 실행 시 RAM을 확인해야 합니다.
현재 02단계는 일치하는 이벤트가 하나도 없으면 합치기에서 실패합니다.

원본 설명서와 코드에는 차이가 있습니다. 코드의 사망 라벨은 날짜 단위(0~28일 포함)이고,
GCS는 아직 추출하지 않습니다. `intime`은 최종 CSV에 남으므로 모델 입력 열을 별도로 정하세요.
24시간 이내 사망·퇴실한 stay의 포함 기준과 관측 구간도 모델링 전에 검토해야 합니다.
환자별 데이터 분할, 학습 데이터 기준 결측치 대체, 모델 학습·평가는 후속 작업입니다.

## 가상 데이터 검증

```bash
.venv/bin/python tests/smoke_pipeline.py
```

실제 환자 데이터 없이 임시 폴더에서 6단계를 실행하고 성인 필터, 라벨, 24시간 경계,
이상치 제외, 체온 변환, 요약값, 최종 행 수를 검증합니다. 임시 데이터는 종료 시 삭제됩니다.
