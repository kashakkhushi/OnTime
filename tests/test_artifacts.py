import hashlib
import json
import re
import numpy as np
import pandas as pd
from PIL import Image
from ontime import config as c
from ontime.ingest import sha256, NAMES
from ontime.pipeline import canonical_json
from ontime.models import logistic, boosted, score


def test_metrics_are_finite_canonical_json(metrics):
    text = (c.OUTPUTS / "metrics.json").read_text()
    assert text == canonical_json(metrics)
    assert "NaN" not in text and "Infinity" not in text


def test_models_are_deterministic():
    rng=np.random.default_rng(c.SEED)
    X=rng.normal(size=(800,5))
    y=(X[:,0]+rng.normal(size=800)>0.5).astype(int)
    for factory in (logistic,boosted):
        left=factory().fit(X,y).predict_proba(X)[:,1]
        right=factory().fit(X,y).predict_proba(X)[:,1]
        assert canonical_json(score(y,left)) == canonical_json(score(y,right))


def test_dataset_cache_checksums():
    manifest=json.loads((c.DATA / "manifest.json").read_text())
    assert set(manifest) == {name+'.csv' for name in NAMES}
    for filename,record in manifest.items():
        assert sha256(c.RAW / filename) == record["sha256"]


def test_eight_pngs_with_captions_and_resolution():
    paths=sorted(c.FIGURES.glob('fig*.png'))
    assert len(paths) == 8
    for path in paths:
        with Image.open(path) as img:
            assert img.width > 1100 and img.height > 650
            assert abs(img.info['dpi'][0]-150) < 1
        assert len(path.with_suffix('.caption.txt').read_text()) > 50


def test_tables_reconcile_with_metrics(metrics):
    ladder=pd.read_csv(c.TABLES / 'model_ladder.csv')
    assert np.allclose(ladder.pr_auc,[row['pr_auc'] for row in metrics['model_ladder']])
    assert len(ladder) == 7
    for kind in ('state','seller','route'):
        segments=pd.read_csv(c.TABLES / f'smr_{kind}.csv')
        assert segments.orders.sum() == metrics['population']['orders']
        assert segments.observed.sum() == metrics['population']['late_orders']


def test_readme_relative_images_resolve():
    text=(c.ROOT / 'README.md').read_text(encoding='utf8')
    paths=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text)
    assert len(paths) >= 3
    assert all(not path.startswith(('http','/','C:')) and (c.ROOT / path).exists() for path in paths)


def test_memo_length_and_number_ledger():
    text=(c.ROOT / 'docs' / 'DECISION_MEMO.md').read_text(encoding='utf8')
    assert 1200 <= len(text.split()) <= 1800
    assert 'Limitations' in text
    ledger=pd.read_csv(c.TABLES / 'memo_number_ledger.csv',dtype=str)
    assert len(ledger) > 20
    # Every numeric token in prose is emitted by the report's tracked num() helper.
    tokens=set(re.findall(r'(?<![A-Za-z_])\d+(?:[,.]\d+)*(?:%)?',text))
    allowed=set(ledger.display)
    assert tokens <= allowed, tokens-allowed
