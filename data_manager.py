"""csv persistence for historical sales records and AI recommendations."""

import csv
from datetime import date, datetime
from pathlib import Path
from abc import ABC, abstractmethod
from typing import TypeVar
from storage_interface import IStorage
from record import Record

DATA_FOLDER = Path(__file__).resolve().parent / "data"
RECORDS_FILE = DATA_FOLDER / "sales_records.csv"

AI_RECOMMENDATIONS_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "ai_recommendations.csv"
)

RECORD_FIELDS = [
    "user_name",
    "business_type",
    "record_date",
    "food_item",
    "portions_prepared",
    "portions_sold",
    "past_context",
]

AI_RECOMMENDATION_FIELDS = [
    "user_name",
    "food_item",
    "forecast_date",
    "recommended_portions",
    "reason",
    "verified_evidence",
    "suggested_next_step",
    "forecast_method",
    "confidence",
    "generated_at",
    "warning",
]


class SalesRecord(Record):
    def __init__(
        self,
        user_name: str,
        business_type: str,
        record_date: date,
        food_item: str,
        portions_prepared: int,
        portions_sold: int,
        past_context: str = "",
    ):
        self._user_name = user_name
        self._business_type = business_type
        self._record_date = record_date
        self._food_item = food_item
        self._portions_prepared = portions_prepared
        self._portions_sold = portions_sold
        self._past_context = past_context

    @property
    def user_name(self) -> str:
        return self._user_name

    @property
    def food_item(self) -> str:
        return self._food_item

    @property
    def record_date(self) -> date:
        return self._record_date

    def to_dict(self) -> dict:
        return {
            "user_name": self._user_name,
            "business_type": self._business_type,
            "record_date": self._record_date.isoformat(),
            "food_item": self._food_item,
            "portions_prepared": self._portions_prepared,
            "portions_sold": self._portions_sold,
            "past_context": self._past_context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SalesRecord":
        record_date = data["record_date"]
        if isinstance(record_date, str):
            record_date = date.fromisoformat(record_date)
        elif not isinstance(record_date, date):
            raise TypeError("record_date must be a date or ISO date string")

        return cls(
            user_name=data["user_name"],
            business_type=data["business_type"],
            record_date=record_date,
            food_item=data["food_item"],
            portions_prepared=int(data["portions_prepared"]),
            portions_sold=int(data["portions_sold"]),
            past_context=data.get("past_context", "") or "",
        )

class AIRecommendation(Record):
    def __init__(
        self,
        user_name: str,
        food_item: str,
        forecast_date: date,
        recommended_portions: int,
        reason: str,
        verified_evidence: str,
        suggested_next_step: str,
        forecast_method: str,
        confidence: str,
        generated_at: datetime,
        warning: str,
    ):
        self._user_name = user_name
        self._food_item = food_item
        self._forecast_date = forecast_date
        self._recommended_portions = recommended_portions
        self._reason = reason
        self._verified_evidence = verified_evidence
        self._suggested_next_step = suggested_next_step
        self._forecast_method = forecast_method
        self._confidence = confidence
        self._generated_at = generated_at
        self._warning = warning

    def to_dict(self) -> dict:
        return {
            "user_name": self._user_name,
            "food_item": self._food_item,
            "forecast_date": self._forecast_date.isoformat(),
            "recommended_portions": self._recommended_portions,
            "reason": self._reason,
            "verified_evidence": self._verified_evidence,
            "suggested_next_step": self._suggested_next_step,
            "forecast_method": self._forecast_method,
            "confidence": self._confidence,
            "generated_at": self._generated_at.isoformat(
                timespec="seconds"
            ),
            "warning": self._warning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AIRecommendation":
        return cls(
            user_name=data["user_name"],
            food_item=data["food_item"],
            forecast_date=date.fromisoformat(data["forecast_date"]),
            recommended_portions=int(data["recommended_portions"]),
            reason=data["reason"],
            verified_evidence=data["verified_evidence"],
            suggested_next_step=data["suggested_next_step"],
            forecast_method=data["forecast_method"],
            confidence=data["confidence"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            warning=data.get("warning", "") or "",
        )
    
    @property
    def user_name(self) -> str:
        return self._user_name

    @property
    def food_item(self) -> str:
        return self._food_item

    @property
    def forecast_date(self) -> date:
        return self._forecast_date

# class CsvStorage:
#     def __init__(
#         self,
#         storage_path: Path,
#         record_type: type[T],
#         fieldnames: list[str],
#     ):
#         self._storage_path = storage_path
#         self._record_type = record_type
#         self._fieldnames = fieldnames

#     def load(self) -> list[T]:
#         if not self._storage_path.exists():
#             return []

#         records = []

#         with self._storage_path.open(
#             "r",
#             newline="",
#             encoding="utf-8",
#         ) as file:
#             reader = csv.DictReader(file)

#             for row in reader:
#                 if row:
#                     records.append(self._record_type.from_dict(row))

#         return records

#     def save(self, records: list[T]) -> None:
#         self._storage_path.parent.mkdir(
#             parents=True,
#             exist_ok=True,
#         )

#         with self._storage_path.open(
#             "w",
#             newline="",
#             encoding="utf-8",
#         ) as file:
#             writer = csv.DictWriter(
#                 file,
#                 fieldnames=self._fieldnames,
#             )
#             writer.writeheader()

#             for record in records:
#                 writer.writerow(record.to_dict())

class SalesRecordManager:
    def __init__(self, storage: IStorage):
        self._storage = storage
        self._records: list[SalesRecord] = []

    def load(self) -> None:
        self._records = self._storage.load()

    def get_all(self) -> list[SalesRecord]:
        return list(self._records)

    def save(self) -> None:
        self._storage.save(self._records)

    def add(self, record: SalesRecord) -> None:
        for existing in self._records:
            if (
                existing.user_name.strip().casefold()
                == record.user_name.strip().casefold()
                and existing.food_item.strip().casefold()
                == record.food_item.strip().casefold()
                and existing.record_date == record.record_date
            ):
                raise ValueError(
                    f"You have already recorded "
                    f"'{record.food_item}' on "
                    f"{record.record_date.isoformat()}."
                )

        self._records.append(record)
        self.save()

    def item_names_for_user(self, user_name: str) -> list[str]:
        normalized_name = user_name.casefold().strip()

        names = {
            record.food_item.strip()
            for record in self._records
            if record.user_name.casefold().strip() == normalized_name
        }

        return sorted(names, key=str.casefold)
    
    def records_in_date_range(
        self,
        user_name: str,
        food_item: str,
        start_date: date,
        end_date: date,
    ) -> list[SalesRecord]:
        return [
            record
            for record in self.records_for_item(user_name, food_item)
            if start_date <= record.record_date <= end_date
        ]

    def records_for_item(
        self,
        user_name: str,
        food_item: str,
    ) -> list[SalesRecord]:
        normalized_name = user_name.casefold().strip()
        normalized_item = food_item.casefold().strip()

        matches = [
            record
            for record in self._records
            if record.user_name.casefold().strip() == normalized_name
            and record.food_item.casefold().strip() == normalized_item
        ]

        return sorted(
            matches,
            key=lambda record: record.record_date,
        )

class RecommendationManager:
    def __init__(self, storage: IStorage):
        self._storage = storage
        self._recommendations: list[AIRecommendation] = []

    def load(self) -> None:
        self._recommendations = self._storage.load()

    def get_all(self) -> list[AIRecommendation]:
        return list(self._recommendations)

    def save(self, recommendation: AIRecommendation) -> None:
        self._recommendations.append(recommendation)
        self._storage.save(self._recommendations)

    def replace(self, recommendation: AIRecommendation) -> None:
        self._recommendations = [
            existing
            for existing in self._recommendations
            if not (
                existing.user_name.casefold()
                == recommendation.user_name.casefold()
                and existing.food_item.casefold()
                == recommendation.food_item.casefold()
                and existing.forecast_date
                == recommendation.forecast_date
            )
        ]

        self._recommendations.append(recommendation)
        self._storage.save(self._recommendations)


    
