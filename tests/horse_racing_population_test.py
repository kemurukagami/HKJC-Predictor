import sys
import os

# Get the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Append it to sys.path
sys.path.append(parent_dir)

import horse_racing_population as hrp
import Gen_Report as gr

hrp.set_relevant(True)
hrp.set_racecard()

hrp.extract_horses()
hrp.insert_horse_performance()

gr.set_file_name("../test_report.txt")
gr.rank_racecards_by_horse_performance()
gr.rank_by_stakes()