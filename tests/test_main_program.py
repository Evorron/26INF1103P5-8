import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

import data.data_manager as data_manager
import data.setup_db as setup_db
import input_output.in_out_main as in_out_main


class TestMainProgram(unittest.TestCase):
    def test_script_initializes_schema_loads_both_managers_and_runs_application(self):
        main_path = Path(__file__).resolve().parents[1] / "main.py"

        with patch.object(setup_db.DatabaseSchema, "initialize") as initialize, \
             patch.object(data_manager.SalesRecordManager, "load") as load_sales, \
             patch.object(data_manager.RecommendationManager, "load") as load_recommendations, \
             patch.object(in_out_main.IOManager, "run_application") as run_application:
            runpy.run_path(str(main_path), run_name="__main__")

        initialize.assert_called_once()
        load_sales.assert_called_once()
        load_recommendations.assert_called_once()
        run_application.assert_called_once()

    def test_importing_main_does_not_initialize_database_or_start_interactive_app(self):
        main_path = Path(__file__).resolve().parents[1] / "main.py"

        with patch.object(setup_db.DatabaseSchema, "initialize") as initialize, \
             patch.object(in_out_main.IOManager, "run_application") as run_application:
            runpy.run_path(str(main_path), run_name="hawker_main_import_test")

        initialize.assert_not_called()
        run_application.assert_not_called()


if __name__ == "__main__":
    unittest.main()
