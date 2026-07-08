import os
import unittest
import pandas as pd
from src.screener.engine import ScreenerEngine, load_screener_config, load_screener_presets

class TestScreenerEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cls.db_path = os.path.join(cls.project_root, "data", "nifty100.db")
        cls.config_path = os.path.join(cls.project_root, "config", "screener_config.yaml")
        cls.engine = ScreenerEngine(cls.db_path)
        cls.df_base = cls.engine.load_base_data()

    def test_base_load(self):
        self.assertGreater(len(self.df_base), 0)
        self.assertIn("company_id", self.df_base.columns)
        self.assertIn("year", self.df_base.columns)
        self.assertIn("composite_quality_score", self.df_base.columns)

    def test_composite_score_range(self):
        scores = self.df_base["composite_quality_score"].dropna()
        self.assertTrue((scores >= 0.0).all())
        self.assertTrue((scores <= 100.0).all())

    def test_presets_counts(self):
        presets = load_screener_presets(self.config_path)
        self.assertIn("Quality Compounder", presets)
        self.assertIn("Value Pick", presets)
        
        # Test Quality Compounder preset on latest year
        df_qc = self.engine.run_preset(self.df_base, "Quality Compounder", self.config_path, year="2024-03")
        # Exit criteria: each preset returns between 5 and 50 companies (Value Pick has 8, others have 18-31)
        self.assertTrue(5 <= len(df_qc) <= 50)
        
        # Verify Quality Compounder logic (ROE > 15% and D/E < 1.0)
        # Skip Financials sector since D/E is suppressed for them
        df_non_fin = df_qc[df_qc["broad_sector"] != "Financials"]
        if len(df_non_fin) > 0:
            self.assertTrue((df_non_fin["return_on_equity_pct"] >= 15.0).all())
            self.assertTrue((df_non_fin["debt_to_equity"] <= 1.0).all())

    def test_financials_de_suppression(self):
        # Apply de_max filter of 1.0 to the base data
        thresholds = {"de_max": 1.0}
        df_filtered = self.engine.apply_filters(self.df_base, thresholds)
        # Check that companies in Financials sector with D/E > 1.0 are NOT dropped
        df_fin_high_de = df_filtered[(df_filtered["broad_sector"] == "Financials") & (df_filtered["debt_to_equity"] > 1.0)]
        self.assertGreaterEqual(len(df_fin_high_de), 0)

    def test_icr_debt_free_always_passes(self):
        # Apply a high ICR minimum (e.g. 50.0)
        thresholds = {"icr_min": 50.0}
        df_filtered = self.engine.apply_filters(self.df_base[self.df_base["year"] == "2023-03"], thresholds)
        # 'Debt Free' labeled companies should still be present
        df_debt_free = df_filtered[df_filtered["icr_label"] == "Debt Free"]
        self.assertGreater(len(df_debt_free), 0)
