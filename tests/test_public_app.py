"""Synthetic UI inputs and aggregate R reference predictions only."""
import csv
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from renal_calculator import load_model, predicted, calculate, weight_notices
from streamlit.testing.v1 import AppTest


class NumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load_model()

    def test_all_eight_predictions_match_independent_R_output(self):
        with (ROOT/'assets/reference_predictions.csv').open() as f:
            reference = list(csv.DictReader(f))
        self.assertEqual(len(reference), 64)
        for row in reference:
            with self.subTest(endpoint=row['outcome'], weight=row['BW']):
                self.assertAlmostEqual(predicted(self.model, row['outcome'], row['BW']), float(row['predicted']), places=10)

    def test_optional_measures_remain_missing(self):
        self.assertTrue(all(r['measured'] is None and r['ratio'] is None for r in calculate(self.model, 10, 'L')))

    def test_ratio_uses_unrounded_prediction(self):
        for side in ('L','R'):
            mu = predicted(self.model, side+'V', 10)
            self.assertAlmostEqual(calculate(self.model,10,side,{'V':2*mu})[-1]['ratio'], 2, places=13)

    def test_left_and_right_are_distinct(self):
        self.assertNotEqual(predicted(self.model, 'LV', 10), predicted(self.model, 'RV', 10))

    def test_invalid_weights_rejected(self):
        for value in [0,-1,None,True,float('nan'),float('inf'),'犬']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                calculate(self.model,value,'L')

    def test_invalid_measurements_rejected(self):
        for value in [0,-1,True,float('nan'),float('inf'),'未計測']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                calculate(self.model,10,'L',{'L':value})

    def test_invalid_side_rejected(self):
        with self.assertRaises(ValueError):
            calculate(self.model,10,'both')

    def test_unknown_field_not_silently_ignored(self):
        with self.assertRaises(ValueError):
            calculate(self.model,10,'L',{'LL':5})

    def test_range_and_sparse_tail_notices(self):
        self.assertIn('外挿',''.join(weight_notices(self.model,1)))
        self.assertIn('外挿',''.join(weight_notices(self.model,46)))
        self.assertIn('1検査',''.join(weight_notices(self.model,1.37)))
        self.assertIn('11検査',''.join(weight_notices(self.model,45)))
        self.assertEqual(weight_notices(self.model,10),[])

    def test_actual_range_boundaries_not_extrapolation(self):
        for bw in [1.37,45]:
            self.assertNotIn('外挿',''.join(weight_notices(self.model,bw)))

    def test_no_diagnostic_fields_for_extreme_ratios(self):
        for value in [0.001,1000]:
            rows = calculate(self.model,10,'L',{'L':value})
            self.assertEqual(set(rows[0]), {'endpoint','label','unit','predicted','measured','ratio'})

    def test_model_provenance(self):
        self.assertEqual((self.model['n_examinations'], self.model['n_additional'], self.model['n_provisional_individuals']), (122,0,121))
        self.assertEqual(self.model['modality'],'CT')
        self.assertEqual(self.model['known_issue']['statistic'],'standard error of coefficient a')


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()

    def assert_clean(self):
        self.assertEqual([e.value for e in self.app.exception], [])

    def texts(self):
        return '\n'.join(e.value for kind in ('markdown','caption','warning') for e in getattr(self.app,kind))

    def test_starts_without_images_or_measured_values(self):
        self.assert_clean()
        self.assertEqual(len(self.app.number_input),5)
        self.assertTrue(all(x.value is None for x in self.app.number_input[1:]))
        self.assertEqual(len(self.app.get('file_uploader')),0)

    def test_band_off_by_default(self):
        self.assertFalse(self.app.checkbox('show_band').value)
        charts = self.app.get('vega_lite_chart')
        self.assertEqual(len(charts),4)
        for chart in charts:
            self.assertNotIn('"area"', chart.proto.spec)

    def test_weight_changes_prediction(self):
        before = self.app.dataframe[0].value.iloc[0]['体重からの予測値']
        self.app.number_input('weight').set_value(20).run()
        self.assert_clean()
        self.assertGreater(self.app.dataframe[0].value.iloc[0]['体重からの予測値'],before)

    def test_left_right_left_preserves_both_measurements(self):
        self.app.number_input('measured_L_L').set_value(5.6).run()
        self.app.radio('kidney').set_value('右腎').run()
        self.assertIsNone(self.app.number_input('measured_R_L').value)
        self.app.number_input('measured_R_L').set_value(6.1).run()
        self.app.radio('kidney').set_value('左腎').run()
        self.assertEqual(self.app.number_input('measured_L_L').value,5.6)
        self.app.radio('kidney').set_value('右腎').run()
        self.assertEqual(self.app.number_input('measured_R_L').value,6.1)
        self.assert_clean()

    def test_clear_measurement_restores_missing_ratio(self):
        self.app.number_input('measured_L_V').set_value(30).run()
        self.app.number_input('measured_L_V').set_value(None).run()
        self.assert_clean()
        self.assertEqual(self.app.dataframe[0].value.iloc[3]['実測値／予測値'],'—')

    def test_extrapolation_notice(self):
        self.app.number_input('weight').set_value(50).run()
        self.assert_clean()
        self.assertTrue(any('外挿' in w.value for w in self.app.warning))

    def test_band_opt_in_and_disable(self):
        self.app.checkbox('show_band').check().run()
        self.assert_clean()
        self.assertTrue(any('正常範囲' in w.value for w in self.app.warning))
        self.assertEqual(len(self.app.get('vega_lite_chart')),4)
        for chart in self.app.get('vega_lite_chart'):
            self.assertIn('"area"',chart.proto.spec)
        self.app.checkbox('show_band').uncheck().run()
        for chart in self.app.get('vega_lite_chart'):
            self.assertNotIn('"area"',chart.proto.spec)

    def test_source_and_model_shown(self):
        text = self.texts()
        for word in ('原 健人','柿崎竹彦','2026','第23号','3–11頁','renal-ct-20261121-r2'):
            self.assertIn(word,text)

    def test_unresolved_SE_is_visible(self):
        text = self.texts()
        for word in ('係数 a','0.8','0.5166','10.4457','未解決'):
            self.assertIn(word,text)

    def test_cloud_processing_disclosure(self):
        text = self.texts()
        self.assertIn('配信サーバーへ送られます',text)
        self.assertIn('ファイルやデータベースへ保存しません',text)
        self.assertNotIn('外部送信しません',text)
        self.assertEqual(len(self.app.text_input),0)

    def test_CT_limit_and_no_diagnosis(self):
        text = self.texts()
        self.assertIn('単純X線・超音波の計測値への直接適用は未検証',text)
        self.assertIn('正常・腎腫大・腎萎縮を判定する機能はありません',text)

    def test_separate_sessions_do_not_share_inputs(self):
        self.app.number_input('measured_L_L').set_value(5.6).run()
        other = AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
        self.assertIsNone(other.number_input('measured_L_L').value)
        self.assertEqual(self.app.number_input('measured_L_L').value,5.6)


class AggregateAssetTests(unittest.TestCase):
    def test_prediction_grid_is_aggregate_and_self_consistent(self):
        model = load_model()
        grids = {}
        with (ROOT/'assets/exploratory_prediction_grid.csv').open() as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames,['outcome','BW','predicted','lower','upper'])
            for row in reader:
                x,mu,lo,hi = map(float,[row[k] for k in ('BW','predicted','lower','upper')])
                self.assertTrue(all(math.isfinite(v) for v in (x,mu,lo,hi)))
                self.assertTrue(1.37<=x<=45)
                self.assertTrue(0<lo<mu<hi)
                self.assertAlmostEqual(mu,predicted(model,row['outcome'],x),places=9)
                grids.setdefault(row['outcome'],[]).append(x)
        self.assertEqual(set(grids),set(model['coefficients']))
        for weights in grids.values():
            self.assertEqual(weights,grids['LV'])
            self.assertEqual(weights,sorted(set(weights)))

    def test_only_two_expected_aggregate_tables(self):
        self.assertEqual({p.name for p in (ROOT/'assets').glob('*.csv')},
                         {'reference_predictions.csv','exploratory_prediction_grid.csv'})
        with (ROOT/'assets/reference_predictions.csv').open() as f:
            self.assertEqual(csv.DictReader(f).fieldnames,['outcome','BW','predicted'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
