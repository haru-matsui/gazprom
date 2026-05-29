from pydantic import BaseModel
from typing import List

class Housing(BaseModel):
    percent: int
    type: str

class UserInput(BaseModel):
    production_volume: int
    employees: int
    budget_mln: int
    railway_mode: str
    max_distance_to_highway: int
    architecture_priority: str
    landscaping: List[str]
    housing: Housing
    kindergarten_places: int
    sports: List[str]
