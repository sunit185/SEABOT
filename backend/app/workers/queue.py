"""Background job queue for Seabot."""
from __future__ import annotations

import asyncio
from enum import Enum
import logging
from typing import Any, Callable, Coroutine, Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger("seabot.queue")


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class JobQueue:
    def __init__(self, max_concurrent: int = 2) -> None:
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._queue: Optional[asyncio.Queue] = None
        self._workers: list[asyncio.Task] = []
        self._status: Dict[str, Dict[str, Any]] = {}
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._queue = asyncio.Queue()
        for i in range(self.max_concurrent):
            worker_task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker_task)
        logger.info("JobQueue started with %d workers", self.max_concurrent)

    async def stop(self) -> None:
        self._running = False
        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("JobQueue stopped")

    async def enqueue(
        self,
        job_id: str,
        coro_fn: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if not self._queue:
            await self.start()
        self._status[job_id] = {
            "status": JobStatus.PENDING,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "started_at": None,
            "finished_at": None,
        }
        await self._queue.put((job_id, coro_fn, args, kwargs))
        logger.info("Job %s enqueued", job_id)

    async def get_status(self, job_id: str) -> Dict[str, Any]:
        return self._status.get(
            job_id,
            {"status": "unknown", "error": f"Job {job_id} not found"},
        )

    async def _worker_loop(self, worker_id: int) -> None:
        while self._running:
            try:
                job_id, coro_fn, args, kwargs = await self._queue.get()
                self._status[job_id]["status"] = JobStatus.RUNNING
                self._status[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()
                logger.info("Worker %d starting job %s", worker_id, job_id)
                try:
                    await coro_fn(*args, **kwargs)
                    self._status[job_id]["status"] = JobStatus.DONE
                    logger.info("Worker %d finished job %s successfully", worker_id, job_id)
                except Exception as exc:
                    self._status[job_id]["status"] = JobStatus.FAILED
                    self._status[job_id]["error"] = str(exc)
                    logger.exception("Worker %d failed job %s: %s", worker_id, job_id, exc)
                finally:
                    self._status[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker %d encountered error: %s", worker_id, e)
