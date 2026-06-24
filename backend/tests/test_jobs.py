import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.app.models.job import Job
from src.app.workers.job_worker import process_jobs


class TestJobModel:
    """Тесты модели Job."""

    @pytest.mark.asyncio
    async def test_create_job(self, test_session):
        """Job создаётся с дефолтным статусом pending."""
        job = Job(job_type="CDEK_CREATE_ORDER", payload={"order_id": 1})
        test_session.add(job)
        await test_session.commit()
        await test_session.refresh(job)

        assert job.id is not None
        assert job.status == "pending"
        assert job.payload == {"order_id": 1}
        assert job.attempts == 0


class TestJobWorker:
    """Тесты polling loop job worker'а."""

    @pytest.fixture
    async def job_session(self, test_engine):
        """Dedicated session for the worker to avoid cross-session issues."""
        factory = async_sessionmaker(test_engine, expire_on_commit=False)
        async with factory() as session:
            yield session

    @pytest.mark.asyncio
    async def test_process_jobs_runs_pending_job(self, job_session, monkeypatch):
        """process_jobs забирает pending job и выполняет handler."""
        called = []

        async def fake_handler(job, db):
            called.append(job.job_type)

        monkeypatch.setattr("src.app.workers.job_worker.HANDLERS", {"TEST_JOB": fake_handler})

        job = Job(job_type="TEST_JOB", payload={"foo": "bar"})
        job_session.add(job)
        await job_session.commit()

        monkeypatch.setattr(
            "src.app.workers.job_worker.SessionLocal",
            lambda: async_sessionmaker(job_session.bind, expire_on_commit=False)(),
        )

        processed = await process_jobs()
        assert processed == 1
        assert called == ["TEST_JOB"]

        await job_session.refresh(job)
        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_process_jobs_retries_failed_job(self, job_session, monkeypatch):
        """process_jobs увеличивает attempts при ошибке handler'а."""
        async def fake_handler(job, db):
            raise RuntimeError("boom")

        monkeypatch.setattr("src.app.workers.job_worker.HANDLERS", {"TEST_JOB": fake_handler})

        job = Job(job_type="TEST_JOB", payload={"foo": "bar"})
        job_session.add(job)
        await job_session.commit()

        monkeypatch.setattr(
            "src.app.workers.job_worker.SessionLocal",
            lambda: async_sessionmaker(job_session.bind, expire_on_commit=False)(),
        )

        processed = await process_jobs()
        assert processed == 0

        await job_session.refresh(job)
        assert job.status == "pending"
        assert job.attempts == 1
        assert "boom" in job.processing_log[0]

    @pytest.mark.asyncio
    async def test_process_jobs_unknown_job_type_fails(self, job_session, monkeypatch):
        """Job с неизвестным типом помечается failed."""
        job = Job(job_type="UNKNOWN_JOB", payload={})
        job_session.add(job)
        await job_session.commit()

        monkeypatch.setattr(
            "src.app.workers.job_worker.SessionLocal",
            lambda: async_sessionmaker(job_session.bind, expire_on_commit=False)(),
        )

        processed = await process_jobs()
        assert processed == 0

        await job_session.refresh(job)
        assert job.status == "failed"
        assert "Unknown job_type" in job.processing_log[0]
