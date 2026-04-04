from __future__ import annotations

from app.db.repository import RepositoryProtocol, RepositoryUnavailableError
from backend.verified_dataset import compute_moat_metrics, export_verified_dataset
from models.verified_dataset import VerifiedDatasetExport, VerifiedDatasetMoatMetrics


class VerifiedTrainingService:
    def __init__(self, repository: RepositoryProtocol | None) -> None:
        self._repository = repository

    def _require_repository(self) -> RepositoryProtocol:
        if self._repository is None:
            raise RepositoryUnavailableError('Database evidence repository is not configured')
        return self._repository

    async def export_dataset(self, *, limit: int = 1000) -> VerifiedDatasetExport:
        repository = self._require_repository()
        bundles = await repository.fetch_training_candidates(limit=limit)
        return export_verified_dataset(bundles)

    async def moat_metrics(self, *, limit: int = 1000) -> VerifiedDatasetMoatMetrics:
        dataset = await self.export_dataset(limit=limit)
        return compute_moat_metrics(dataset)
