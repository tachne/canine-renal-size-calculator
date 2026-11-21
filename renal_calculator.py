"""Reference calculations only; no diagnostic classification or model fitting."""
from pathlib import Path
import json, math

ROOT = Path(__file__).resolve().parent
LABELS = {'L': ('長径', 'cm'), 'S': ('短径', 'cm'), 'T': ('横径', 'cm'), 'V': ('体積', 'cm³')}

def load_model(path=None):
    model = json.loads(Path(path or ROOT/'assets/model.json').read_text(encoding='utf-8'))
    if model.get('formula') != 'a * BW ** b' or set(model['coefficients']) != {'LV','RV','LL','RL','LS','RS','LT','RT'}:
        raise ValueError('モデルの形式を確認してください。')
    return model

def positive_number(value, label):
    if isinstance(value, bool):
        raise ValueError(f'{label}には正の数を入力してください。')
    try: number = float(value)
    except (ValueError, TypeError): raise ValueError(f'{label}には正の数を入力してください。') from None
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f'{label}には0より大きい有限の数を入力してください。')
    return number

def predicted(model, endpoint, bw):
    bw = positive_number(bw, '体重')
    if endpoint not in model['coefficients']: raise ValueError('測定項目が不明です。')
    c = model['coefficients'][endpoint]
    try: value = c['a'] * bw ** c['b']
    except OverflowError: raise ValueError('入力値が計算可能な範囲を超えています。') from None
    if not math.isfinite(value) or value <= 0: raise ValueError('計算結果を確認できません。')
    return value

def calculate(model, bw, side, measured=None):
    bw = positive_number(bw, '体重')
    if side not in ('L', 'R'): raise ValueError('左腎または右腎を選んでください。')
    measured = measured or {}
    if set(measured) - set(LABELS): raise ValueError('実測値の項目が不明です。')
    rows=[]
    for axis, (label,unit) in LABELS.items():
        mu=predicted(model, side+axis, bw)
        y=measured.get(axis)
        if y is not None: y=positive_number(y, label)
        ratio=None if y is None else y/mu
        if ratio is not None and not math.isfinite(ratio): raise ValueError('実測値／予測値が計算可能な範囲を超えています。')
        rows.append({'endpoint':side+axis,'label':label,'unit':unit,'predicted':mu,
                     'measured':y,'ratio':ratio})
    return rows

def weight_notices(model, bw):
    bw=positive_number(bw,'体重');lo,hi=model['weight_range_kg']
    notices=[]
    if bw < lo or bw > hi:
        notices.append(f'対象データの体重範囲（{lo:g}〜{hi:g} kg）外です。予測値は外挿で、予測精度は未検証です。')
    elif bw < 1.8:
        notices.append('1.8 kg未満の対象は1検査だけです。原著記載の下限1.8 kgと元データの1.37 kgの相違があり、この体重域の精度は未確認です。')
    if bw > 30:
        notices.append('30 kg超の対象は11検査です。特に左腎横径では探索的予測区間の包含率が低く、追加検証が必要です。')
    return notices
