"""Application coordinator for the Hawker AI command-line program.

This module connects the six managers without duplicating their work:

* ``Input_output_manager`` collects and displays information.
* ``logic_manager`` validates data and applies business rules.
* ``data_manager`` reads and writes CSV files.
* ``forecast_coordinator`` creates a safe, user-facing forecast.
* ``ai_manager`` is called by the adapter when an AI estimate is needed.
* ``activity_logger`` is called by the adapter to keep an audit trail.
"""
from pathlib import Path

from data import data_manager, database_storage
from data.setup_db import DatabaseSchema
from input_output.in_out_main import IOManager

# Define the database path
DB_PATH = Path(__file__).resolve().parent / "hawker_data" / "hawker.db"

# --- SALES MANAGER SETUP ---
sales_storage = database_storage.DatabaseStorage(
    DB_PATH, 
    "sales_records", 
    data_manager.SalesRecord
)
sales_manager = data_manager.SalesRecordManager(sales_storage)

# --- AI MANAGER SETUP ---
recommendation_storage = database_storage.DatabaseStorage(
    DB_PATH, 
    "ai_recommendations", 
    data_manager.AIRecommendation
)
recommendation_manager = data_manager.RecommendationManager(recommendation_storage)



if __name__ == "__main__":
    # 1. initialize the database schema
    DatabaseSchema(DB_PATH).initialize()

    sales_manager.load()
    recommendation_manager.load()
    
    # 2. Pass the loaded managers to IOManager
    app = IOManager(sales_manager, recommendation_manager)
    
    # 3. Run menu loop
    app.run_application()