from datetime import date
from pathlib import Path
from display_menu import display_welcome, display_all
from display_record import display_records, forecast_display
from hawker import Hawker
from data_validation import business_type, date_vaildation, positive_integer, sold_portions


class IOManager:
    ##Consolidates all terminal I/O, validation checks, and SQLite database for team integration

    def __init__(self, sales_manager, recommendation_manager):
        self.sales_manager = sales_manager
        self.recommendation_manager = recommendation_manager
        self.registered_business = {}
        

    def save_sales_record(self, record: dict) -> None:
        ##Convert dictionary to OOP object and save via SalesRecordManager
        from data_manager import SalesRecord
        try:
            sales_record = SalesRecord.from_dict(record)
            self.sales_manager.add(sales_record)
            print("Sales record successfully saved!")
        except ValueError as e:
            print(f"[Error] {e}")


    def load_sales_records(self, user_name: str) -> list[dict]:
        """Get records from SalesRecordManager and filter by user."""
        normalized_target = " ".join(user_name.split()).lower()
        records = []

        # Get all records from your manager (Aggregation!)
        all_records = self.sales_manager.get_all()

        for record in all_records:
            if " ".join(record.user_name.split()).lower() == normalized_target:
                # Convert back to dict for his display functions
                records.append({
                    "user_name": record.user_name,
                    "business_type": record._business_type,
                    "record_date": record.record_date,
                    "food_item": record.food_item,
                    "portions_prepared": record._portions_prepared,
                    "portions_sold": record._portions_sold,
                    "past_context": record._past_context
                })
        return records

    def authenticate_user(self) -> tuple[str, str]:
        while True:
            user_name = input("Enter your name: ").strip()
            if not user_name:
                print("Name cannot be empty. Please try again.")
                continue

            biz_type_input = input("Enter your business type: ").strip()
            if not biz_type_input:
                print("Business type cannot be empty. Please try again.")
                continue

            normalized_name = " ".join(user_name.split()).lower()
            
            
            if normalized_name not in self.registered_business:
                for record in self.sales_manager.get_all():
                    if record.user_name.strip().lower() == normalized_name:
                        self.registered_business[normalized_name] = record._business_type
                        break

            validator = business_type(user_name, self.registered_business)
            try:
                validator.check_business_type(biz_type_input)
                return user_name, biz_type_input
            except ValueError as err:
                print(f"\n[Error] {err}")
                print("Existing name does not match the registered business type. Please re-enter.\n")    

    def run_application(self) -> None:

        display_welcome()
        user_name, biz_type = self.authenticate_user()
        hawker_session = Hawker(user_name, biz_type)
        
        ##Instantiate validation classes from data_vaildation.py
        date_validator = date_vaildation()
        pos_int_validator = positive_integer()

        while True:
            choice = display_all()

            if choice == "1":
                # Collect sales record via Hawker session (incorporating positive_integer and sold_portions checks)
                record = hawker_session.collect_sales_record()
                self.save_sales_record(record)

            elif choice == "2":
                forecast_info = hawker_session.collect_forecast_infomation()
                records = self.load_sales_records(user_name)

                matching = [
                    r for r in records
                    if r["food_item"].strip().casefold()
                    == forecast_info["food_item"].strip().casefold()
                ]
                if not matching:
                    print(
                        f"\n[Error] No historical sales records were found for "
                        f"'{forecast_info['food_item']}'. Add a sales record "
                        "before generating a forecast.\n"
                    )
                    continue

                existing_recommendation = next(
                    (
                        recommendation
                        for recommendation in self.recommendation_manager.get_all()
                        if recommendation.user_name.strip().casefold()
                        == user_name.strip().casefold()
                        and recommendation.food_item.strip().casefold()
                        == forecast_info["food_item"].strip().casefold()
                        and recommendation.forecast_date
                        == forecast_info["target_date"]
                    ),
                    None,
                )

                save_mode = "save"
                if existing_recommendation is not None:
                    action = forecast_display.ask_duplicate_forecast_action()
                    if action == "view":
                        forecast_display.show_past_forecasts(
                            [existing_recommendation.to_dict()]
                        )
                        continue
                    if action == "cancel":
                        continue
                    save_mode = "replace"

                recorded_sales = [r["portions_sold"] for r in matching]
                suggested = int(sum(recorded_sales) / len(recorded_sales))

                forecast_response = {
                    "user_name": user_name,
                    "food_item": forecast_info["food_item"],
                    "forecast_date": forecast_info["target_date"].isoformat(),
                    "recorded_sales": recorded_sales,
                    "suggested_portions": suggested,
                    "confidence": "moderate",
                    "reasoning": f"Based on past sales records for {forecast_info['food_item']}.",
                    "evidence": [
                        {"claim": "Average historical sales", "metric": "portions", "value": str(suggested)}
                    ],
                    "business_advice": "Prepare ingredients slightly ahead of peak hours.",
                    "warning": "" if recorded_sales else "No prior records found; using baseline estimate.",
                }
                
                # 1. Display the forecast
                forecast_display.show_forecast(forecast_response)

                # 2. SAVE the forecast to the database using YOUR OOP class
                from data_manager import AIRecommendation
                from datetime import datetime

                new_recommendation = AIRecommendation(
                    user_name=user_name,
                    food_item=forecast_info["food_item"],
                    forecast_date=forecast_info["target_date"],
                    recommended_portions=suggested,
                    reason=forecast_response["reasoning"],
                    verified_evidence="; ".join(item["claim"] for item in forecast_response["evidence"]),
                    suggested_next_step=forecast_response["business_advice"],
                    forecast_method="Historical Average",
                    confidence=forecast_response["confidence"],
                    generated_at=datetime.now(),
                    warning=forecast_response["warning"]
                )
                
                if save_mode == "replace":
                    self.recommendation_manager.replace(new_recommendation)
                else:
                    self.recommendation_manager.save(new_recommendation)
                print("Forecast successfully saved to database!")

            elif choice == "3":
                records = self.load_sales_records(user_name)
                unique_items = sorted(set(r["food_item"] for r in records))
                display_records.show_items(unique_items)

            elif choice == "4":
                # Option 4: View historical records with validated start and end dates using date_vaildation
                print("\n--- Enter Search Date Range ---")
                start_date = None
                while not start_date:
                    s_input = input("Enter start date (YYYY-MM-DD): ").strip()
                    start_date = date_validator.read_date(s_input)

                end_date = None
                while not end_date:
                    e_input = input("Enter end date (YYYY-MM-DD): ").strip()
                    end_date = date_validator.read_date(e_input)

                # Validate date ordering
                if start_date > end_date:
                    print("\n[Error] Start date cannot be after end date. Please try searching again.\n")
                    continue

                food_item_input = input("Enter food item to filter: ").strip()

                records = self.load_sales_records(user_name)

                filtered = [
                    r for r in records
                    if r["food_item"].lower() == food_item_input.lower()
                    and start_date <= r["record_date"] <= end_date
                ]
                display_records.show_records(filtered)

            elif choice == "5":
                forecast_date = date_validator.read_date(
                    input("\nEnter forecast date to view (YYYY-MM-DD): ").strip()
                )
                forecast_food_item = input("Enter food item to view: ").strip()
                normalized_user = user_name.strip().casefold()
                normalized_food_item = forecast_food_item.casefold()
                forecasts_for_date = [
                    rec.to_dict()
                    for rec in self.recommendation_manager.get_all()
                    if rec.user_name.strip().casefold() == normalized_user
                    and rec.forecast_date == forecast_date
                    and rec.food_item.strip().casefold() == normalized_food_item
                ]
                forecast_display.show_past_forecasts(forecasts_for_date)

            elif choice == "6":
               
                search_info = hawker_session.collect_record_search()
                
                records = self.load_sales_records(user_name)

                # Filter records by food item and date range
                filtered = [
                    r for r in records
                    if r["food_item"].strip().casefold() == search_info["food_item"].strip().casefold()
                    and search_info["start_date"] <= r["record_date"] <= search_info["end_date"]
                ]
                
                if not filtered:
                    print("\n[Error] No records found for this food item in the given date range.\n")
                    continue

                # Calculate statistics
                total_prepared = sum(r["portions_prepared"] for r in filtered)
                total_sold = sum(r["portions_sold"] for r in filtered)
                
                ##Calculate Average Wastage % (Leftovers / Prepared * 100)
                if total_prepared > 0:
                    total_wasted = total_prepared - total_sold
                    wastage_pct = (total_wasted / total_prepared) * 100
                else:
                    wastage_pct = 0.0
                
                # Calculate Average Daily Sales (Total sold / Number of recorded days)
                # Note: This assumes "average" means average per day you actually recorded data
                avg_daily_sales = total_sold / len(filtered)

                # Build the dictionary for the display class
                summary_data = {
                    "food_item": search_info["food_item"],
                    "start_date": search_info["start_date"].isoformat(),
                    "end_date": search_info["end_date"].isoformat(),
                    "total_prepared": total_prepared,
                    "total_sold": total_sold,
                    "wastage_percentage": wastage_pct,
                    "average_daily_sales": avg_daily_sales
                }

                display_records.show_sales_summary(summary_data)

            
            elif choice == "7":
                print("\nExiting Hawker AI. Goodbye!")
                break

            else:
                print("Invalid option. Please choose between 1 and 7.")