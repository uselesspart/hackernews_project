from fastapi import APIRouter

from api import queries as q
from api.deps import SessionDep
from api.schemas import DatasetMeta

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta", response_model=DatasetMeta, summary="Сводка по выборке данных")
def dataset_meta(session: SessionDep):
    return DatasetMeta(**q.dataset_meta(session))


@router.get("/health", summary="Проверка, что сервис жив")
def health():
    return {"status": "ok"}
