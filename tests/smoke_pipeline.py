from pathlib import Path
import subprocess
import tempfile
import pandas as pd
import numpy as np
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='mimic-synthetic-') as tmp:
    d=Path(tmp)
    def write(name, rows): pd.DataFrame(rows).to_csv(d/name,index=False)
    write('icustays.csv', [dict(subject_id=i,hadm_id=100+i,stay_id=1000+i,intime='2150-01-01 12:00:00',outtime='2150-01-04 12:00:00') for i in (1,2,3)])
    write('patients.csv.gz',[dict(subject_id=i,gender='M' if i==1 else 'F',anchor_age=60 if i<3 else 16,anchor_year=2150,dod='2150-01-10' if i==1 else None) for i in (1,2,3)])
    write('admissions.csv.gz',[dict(subject_id=i,hadm_id=100+i,deathtime='2150-01-10' if i==1 else None) for i in (1,2,3)])
    chart=[]
    for i in (1,2,3):
        for item,value in [(220045,80),(220045,100),(220045,700),(223761,98.6),(223762,37)]:
            chart.append(dict(subject_id=i,hadm_id=100+i,stay_id=1000+i,charttime='2150-01-01 13:00:00',itemid=item,valuenum=value,valueuom='test'))
    for t in ('2150-01-01 11:59:59','2150-01-02 12:00:00'):
        chart.append(dict(subject_id=1,hadm_id=101,stay_id=1001,charttime=t,itemid=220045,valuenum=250,valueuom='bpm'))
    write('chartevents.csv',chart)
    labs=[]
    for i in (1,2,3):
        for value,t in [(1,'2150-01-01 13:00:00'),(3,'2150-01-01 14:00:00'),(100,'2150-01-01 15:00:00'),(20,'2150-01-02 12:00:00')]:
            labs.append(dict(subject_id=i,hadm_id=100+i,charttime=t,itemid=50912,valuenum=value,valueuom='mg/dL'))
    write('labevents.csv',labs)
    for script in sorted(root.glob('[0-9][0-9]_*.py')):
        result=subprocess.run([str(root/'.venv/bin/python'),str(script)],cwd=d,capture_output=True,text=True)
        if result.returncode:
            print(result.stdout); print(result.stderr); raise SystemExit(result.returncode)
        print('PASS',script.name)
    cohort=pd.read_csv(d/'cohort_base.csv')
    assert cohort.stay_id.tolist()==[1001,1002]
    assert cohort.mortality_28d.tolist()==[1,0]
    chart=pd.read_csv(d/'chartevents_24h_raw.csv')
    assert len(chart)==10
    labs=pd.read_csv(d/'labevents_24h_raw.csv')
    assert len(labs)==6
    final=pd.read_csv(d/'modeling_dataset.csv').set_index('stay_id')
    assert len(final)==2 and final.index.is_unique
    assert np.allclose(final.HR_mean,90)
    assert np.allclose(final.Temp_mean,37)
    assert np.allclose(final.Creatinine_mean,2)
    assert not any(c.endswith('_count') for c in final.columns)
    assert not {'dod','deathtime','death_days','outtime','window_end'}.intersection(final.columns)
    print('PASS: adult filter, mortality labels, time boundaries, outliers, temperature conversion, summaries, row preservation, excluded columns')
