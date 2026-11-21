from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import streamlit as st
import pandas as pd
import altair as alt
from renal_calculator import load_model, calculate, weight_notices, predicted, LABELS, ROOT

st.set_page_config(page_title='犬の腎臓サイズ参考計算｜VARS',page_icon='📏',layout='wide')
st.title('犬の腎臓サイズ参考計算')
st.caption('VARS 独立参考計算機 · 犬のCT計測モデル · アプリ 0.1.0-rc1')
st.write('体重に応じた予測値と、ご自身で計測した値を比べられます。所見を記述するための参考情報としてお使いください。')
st.caption('体重・任意の実測値は、表示のため配信サーバーへ送られます。このアプリは入力値をファイルやデータベースへ保存しません。')
model=load_model()
c1,c2,c3=st.columns([1,1,2])
with c1: bw=st.number_input('体重（kg）',min_value=0.01,value=10.0,step=0.1,format='%.2f',key='weight')
with c2: kidney=st.radio('評価する腎臓',['左腎','右腎'],horizontal=True,key='kidney')
with c3:
    st.markdown('**対象：犬　／　測定方法：CT**')
    st.caption('単純X線・超音波の計測値への直接適用は未検証です。')
side='L' if kidney=='左腎' else 'R'
for notice in weight_notices(model,bw): st.warning(notice)
st.subheader('実測値（任意）')
st.caption('未計測の項目は空欄のままで構いません。左右の入力は別々に保持します。')
# Keep the data apart from transient widgets so values survive a left/right switch.
st.session_state.setdefault('measurements',{'L':{},'R':{}})
values={}
for col,(axis,(label,unit)) in zip(st.columns(4),LABELS.items()):
    with col:
        widget_key=f'measured_{side}_{axis}'
        if widget_key not in st.session_state:
            st.session_state[widget_key]=st.session_state['measurements'][side].get(axis)
        values[axis]=st.number_input(f'{label}（{unit}）',min_value=0.001,value=None,step=0.1,format='%.3f',placeholder='未入力',key=widget_key)
        st.session_state['measurements'][side][axis]=values[axis]
try: rows=calculate(model,bw,side,values)
except ValueError as error: st.error(str(error));st.stop()
st.subheader(f'{kidney}の参考値 · {bw:g} kg')
st.dataframe(pd.DataFrame([{'項目':r['label'],'単位':r['unit'],'体重からの予測値':round(r['predicted'],3),'実測値':'—' if r['measured'] is None else f"{r['measured']:.3f}",'実測値／予測値':'—' if r['ratio'] is None else f"{r['ratio']:.3f}"} for r in rows]),hide_index=True,width='stretch',column_config={'体重からの予測値':st.column_config.NumberColumn(format='%.3f')})
st.caption('実測値／予測値は単位のない比です。この比から正常・腎腫大・腎萎縮を判定する機能はありません。')
st.subheader('体重とサイズの関係')
show_band=st.checkbox('探索的な名目95%個体予測帯を表示する',value=False,key='show_band')
if show_band:
    st.warning('予測帯は検証途中の参考情報です。健康犬の正常範囲・95%基準範囲ではありません。体重域ごとの95%包含は確認できていません。8項目を同時に95%包含する帯でもありません。')
grid=pd.read_csv(ROOT/'assets/exploratory_prediction_grid.csv')
lo,hi=model['weight_range_kg']
panels=st.columns(2)
for i,r in enumerate(rows):
    g=grid[grid.outcome==r['endpoint']].copy()
    g['体重（kg）']=g['BW'];g['予測値']=g['predicted']
    xlabel=alt.X('体重（kg）:Q',title='体重（kg）',scale=alt.Scale(zero=False))
    ylabel=alt.Y('予測値:Q',title=f"{r['label']}（{r['unit']}）",scale=alt.Scale(zero=False))
    layers=[]
    if show_band:
        layers.append(alt.Chart(g).mark_area(color='#187080',opacity=.14).encode(x=xlabel,y=alt.Y('lower:Q',title=f"{r['label']}（{r['unit']}）"),y2='upper:Q'))
    layers.append(alt.Chart(g).mark_line(color='#166576',strokeWidth=2.5).encode(x=xlabel,y=ylabel,tooltip=['体重（kg）',alt.Tooltip('予測値:Q',format='.3f')]))
    if bw<lo or bw>hi:
        edge=lo if bw<lo else hi
        extra=pd.DataFrame([{'体重（kg）':edge+(bw-edge)*j/60,'予測値':predicted(model,r['endpoint'],edge+(bw-edge)*j/60)} for j in range(61)])
        layers.append(alt.Chart(extra).mark_line(color='#166576',strokeDash=[5,4]).encode(x=xlabel,y=ylabel))
    points=[{'体重（kg）':bw,'値':r['predicted'],'表示':'現在の体重の予測値'}]
    if r['measured'] is not None: points.append({'体重（kg）':bw,'値':r['measured'],'表示':'入力した実測値'})
    layers.append(alt.Chart(pd.DataFrame(points)).mark_point(size=100,filled=True).encode(x=xlabel,y=alt.Y('値:Q',title=f"{r['label']}（{r['unit']}）"),color=alt.Color('表示:N',scale=alt.Scale(domain=['現在の体重の予測値','入力した実測値'],range=['#166576','#ca6a28']),legend=alt.Legend(title=None,orient='bottom')),tooltip=['表示',alt.Tooltip('値:Q',format='.3f')]))
    with panels[i%2]: st.altair_chart(alt.layer(*layers).properties(height=230,title=f"{kidney} · {r['label']}"),width='stretch')
st.caption('実線：対象体重範囲内の予測曲線。範囲外は破線で表示します。探索的予測帯は範囲内だけに表示します。')
with st.expander('使用モデル・検証状況'):
    st.write(f"モデル：{model['version']}　／　解析日：{model['analysis_date']}")
    st.write('原著元データ122検査を再解析しています。追加データは0件です。同一犬の別時期CTが2検査あり、暫定121個体としてグループ単位で予測性能を再評価しました。診療番号欠損2件の個体識別は未確認です。')
    st.write('中心の予測式は原尺度の非線形最小二乗法で再推定した y = a × BW^b です。原著の丸め前係数を再現し、掲載された丸め式とは区別しています。122検査を等しく重み付けしています。')
    st.write('探索的予測帯は個体単位のブートストラップと経験的相対誤差によるものです。交差検証は同一個体の検査が学習側と評価側に分かれないように実施しました。方法の比較にも同じデータを使っており、外部検証は未実施です。')
    if 'validation' in model: st.write(model['validation']['summary_ja'])
    st.write('同一犬の2検査のうち片方ずつを外した感度分析では、8項目の予測値の最大変化は対象体重範囲内で0.49%未満でした。中心の予測式は元の122検査モデルを維持しています。')
    st.warning('既知の未解決事項：左腎体積の係数 a の標準誤差は原著記載0.8、再計算0.5166で一致していません。残差標準誤差10.4457とは別の統計量です。原因は未解決で、原著の数値は修正していません。')
    st.write('腎結石注記10検査を含むCT受診集団です。健康犬の基準集団とはみなしません。左右・径・体積は個別の予測であり、病因診断を生成しません。')
    st.dataframe(pd.DataFrame([{'測定項目':k,'a':v['a'],'b':v['b']} for k,v in model['coefficients'].items()]),hide_index=True,width='stretch')
st.divider()
st.markdown('**基礎研究**')
st.write('原 健人・柿崎竹彦ら（2026）「CT検査を受けたイヌにおける腎臓サイズと体重との関係」『獣医画像診断』第23号、3–11頁。')
st.caption('中心の予測式は原著元データの再解析版です。追加症例は含みません。この画面の探索的予測帯と個体単位の再検証は、原著論文に掲載済みの成果ではありません。')

with st.expander('入力情報の取り扱い'):
    st.write('入力欄は体重、左右の選択、任意のCT実測値のみです。氏名・診療番号や画像を集める機能はありません。値は利用中のセッションのメモリで保持し、左右を切り替えても残ります。再読み込みや接続切断後の保持は保証しません。')
    st.write('アプリには入力値のファイル・データベース保存、外部AIへの送信、利用者間の入力共有機能はありません。クラウドでの配信時はブラウザーと配信サーバーの通信が発生します。ホスティング事業者による運用ログ等の取り扱いは、事業者の方針に従います。')
