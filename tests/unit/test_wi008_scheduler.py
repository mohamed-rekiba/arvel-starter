"""WI-008 Scheduler tests — ScheduleEntry registration and Scheduler.run().

Covers Epic 005 Story 5: Scheduler with PruneExpiredTokensJob.
"""

from __future__ import annotations


from arvel.queue.fake import QueueFake
from arvel.scheduler import InMemoryLockBackend, Scheduler
from arvel.scheduler.fake import SchedulerFake

from app.jobs.prune_expired_tokens_job import PruneExpiredTokensJob


class TestSchedulerRegistration:
    def test_job_registers_hourly_entry(self) -> None:
        queue = QueueFake()
        scheduler = Scheduler(queue=queue, lock_backend=InMemoryLockBackend())
        scheduler.job(PruneExpiredTokensJob).hourly().without_overlapping()
        entries = scheduler.entries()
        assert len(entries) == 1
        assert entries[0].job_class is PruneExpiredTokensJob

    def test_multiple_jobs_register_independently(self) -> None:
        queue = QueueFake()
        scheduler = Scheduler(queue=queue, lock_backend=InMemoryLockBackend())
        scheduler.job(PruneExpiredTokensJob).hourly()
        scheduler.job(PruneExpiredTokensJob).daily_at("03:00")
        entries = scheduler.entries()
        assert len(entries) == 2


class TestSchedulerFake:
    def test_assert_scheduled_passes_for_registered_job(self) -> None:
        fake = SchedulerFake()
        fake.job(PruneExpiredTokensJob).hourly()
        fake.assert_scheduled(PruneExpiredTokensJob)

    def test_assert_not_scheduled_passes_for_missing_job(self) -> None:
        fake = SchedulerFake()
        fake.assert_not_scheduled(PruneExpiredTokensJob)


class TestPruneExpiredTokensJobPayload:
    def test_job_defaults(self) -> None:
        job = PruneExpiredTokensJob()
        assert job.max_retries == 1
        assert job.queue_name == "maintenance"
