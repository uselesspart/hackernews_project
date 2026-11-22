from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from analytics.catalog import CATALOG
from api.deps import SessionDep
from api.schemas import Forecast
from db.models import Tech, TechForecast

router = APIRouter(prefix="/api/techs", tags=["techs"])


@router.get("/{key}/forecast", response_model=Forecast)
def forecast(key: str, session: SessionDep):
    key = key.lower()
    tech_id = session.scalar(select(Tech.id).where(Tech.name == key))
    if tech_id is None and key not in CATALOG:
        raise HTTPException(status_code=404, detail="Технология не отслеживается")
    result = session.get(TechForecast, tech_id) if tech_id is not None else None
    if result is None:
        return Forecast(status="not_computed")
    return Forecast(**result.payload, computed_at=result.computed_at)
