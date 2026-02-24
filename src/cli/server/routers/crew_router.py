from fastapi import APIRouter
from pydantic import BaseModel
from snakesss.cli.server.routers.crews.crew import TravelCrew

router = APIRouter(prefix="/crew")


class TravelInput(BaseModel):
    location: str


@router.post("/travel")
async def crew_chat(input: TravelInput):
    trip_plan_crew = TravelCrew().trip_plan_crew()
    response = trip_plan_crew.kickoff(inputs={"location": input.location})

    return {"content": response}
