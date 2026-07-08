import os
import sqlite3
import unittest
import pandas as pd
from src.analytics.peer import PeerPercentileEngine, get_company_peer_group, calculate_percent_rank

class TestPeerPercentileEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cls.db_path = os.path.join(cls.project_root, "data", "nifty100.db")
        cls.engine = PeerPercentileEngine(cls.db_path)

    def test_company_peer_group_mapping(self):
        # Valid company mapped to a group
        self.assertEqual(get_company_peer_group("INFY", self.db_path), "IT Services")
        # Invalid/non-mapped company
        self.assertEqual(get_company_peer_group("INVALID_XYZ", self.db_path), "No peer group assigned")

    def test_percent_rank_calculation(self):
        series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        ranks = calculate_percent_rank(series)
        self.assertAlmostEqual(ranks.iloc[0], 0.0)
        self.assertAlmostEqual(ranks.iloc[2], 0.5)
        self.assertAlmostEqual(ranks.iloc[4], 1.0)
        
        # Test D/E inversion
        ranks_inverted = calculate_percent_rank(series, invert=True)
        self.assertAlmostEqual(ranks_inverted.iloc[0], 1.0)
        self.assertAlmostEqual(ranks_inverted.iloc[2], 0.5)
        self.assertAlmostEqual(ranks_inverted.iloc[4], 0.0)

    def test_database_records(self):
        conn = sqlite3.connect(self.db_path)
        df_pcts = pd.read_sql_query("SELECT * FROM peer_percentiles", conn)
        conn.close()
        
        self.assertGreater(len(df_pcts), 0)
        self.assertIn("company_id", df_pcts.columns)
        self.assertIn("peer_group_name", df_pcts.columns)
        self.assertIn("percentile_rank", df_pcts.columns)
        
        # Check specific IT Services rankings
        df_it = df_pcts[(df_pcts["peer_group_name"] == "IT Services") & (df_pcts["metric"] == "ROE") & (df_pcts["year"] == "2024-03")]
        if len(df_it) > 0:
            # The company with highest ROE value should have percentile rank = 1.0
            max_val = df_it["value"].max()
            max_rank_row = df_it[df_it["value"] == max_val].iloc[0]
            self.assertAlmostEqual(max_rank_row["percentile_rank"], 1.0)
