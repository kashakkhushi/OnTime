"""Slow acceptance check, separate from the <60-second offline pytest suite."""
import hashlib
import json
from pathlib import Path
from ontime import config as c
from ontime.pipeline import run

def digest():
    return hashlib.sha256((c.OUTPUTS / 'metrics.json').read_bytes()).hexdigest()

if __name__ == '__main__':
    run()
    first=digest()
    run()
    second=digest()
    assert first == second, 'Identical seeds did not produce identical metrics.json'
    record={'first_metrics_sha256':first,'second_metrics_sha256':second,'identical':True,
            'scope':'Two complete offline statistical pipeline runs, including all models, calibration, standardisation and economic scenarios.'}
    (c.OUTPUTS / 'reproducibility.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Full-run determinism verified:',second)
