from pydantic import BaseModel, ConfigDict


class AttributeOut(BaseModel):
    """Справочник характеристик (admin view, Phase 5 #121)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    value_type: str
    unit: str | None
    is_filterable: bool
    sort: int


class AttributeUpdate(BaseModel):
    """Редактируемые админом поля атрибута (мастер code/value_type — 1С)."""

    name: str | None = None
    unit: str | None = None
    is_filterable: bool | None = None
    sort: int | None = None


class AttributePatchOut(AttributeOut):
    """Ответ PATCH: reindex_required=true, если набор filterable изменился."""

    reindex_required: bool = False


class ReindexJobOut(BaseModel):
    """Ответ POST /admin/search/reindex/ (идемпотентный enqueue)."""

    job_id: int
    status: str
    created: bool
