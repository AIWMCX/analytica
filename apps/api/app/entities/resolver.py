from __future__ import annotations

from .contracts import BusinessEntity, ResolutionDecision, ResolutionStatus


def _normal(value: str | None) -> str:
    return "".join(character for character in (value or "").lower() if character.isalnum())


class EntityResolver:
    """Deterministic identity matching; ambiguity always wins over convenience."""

    RESOLVED_THRESHOLD = 0.85
    REVIEW_THRESHOLD = 0.65
    AMBIGUITY_MARGIN = 0.05

    def resolve(self, *, submitted_name: str, domain: str | None, state: str | None,
                candidates: list[BusinessEntity]) -> ResolutionDecision:
        scored = [(self._score(submitted_name, domain, state, candidate), candidate) for candidate in candidates]
        scored.sort(key=lambda item: item[0][0], reverse=True)
        if not scored or scored[0][0][0] < self.REVIEW_THRESHOLD:
            return ResolutionDecision(status=ResolutionStatus.UNRESOLVED, entity_id=None, confidence=0, matching_signals=0)
        best_score, best = scored[0]
        if len(scored) > 1 and best_score[0] - scored[1][0][0] <= self.AMBIGUITY_MARGIN:
            return ResolutionDecision(status=ResolutionStatus.AMBIGUOUS, entity_id=None, confidence=best_score[0], matching_signals=best_score[1], candidate_ids=[candidate.entity_id for _, candidate in scored[:2]])
        status = ResolutionStatus.RESOLVED if best_score[0] >= self.RESOLVED_THRESHOLD else ResolutionStatus.HUMAN_REVIEW
        return ResolutionDecision(status=status, entity_id=best.entity_id if status == ResolutionStatus.RESOLVED else None, confidence=best_score[0], matching_signals=best_score[1], candidate_ids=[best.entity_id])

    def _score(self, name: str, domain: str | None, state: str | None, candidate: BusinessEntity) -> tuple[float, int]:
        score = 0.0
        signals = 0
        if _normal(name) in {_normal(candidate.legal_name), _normal(candidate.canonical_name), *(_normal(alias) for alias in candidate.aliases)}:
            score += 0.15; signals += 1
        if domain and _normal(domain) in {_normal(item) for item in candidate.domains}:
            score += 0.25; signals += 1
        if state and _normal(state) in {_normal(item) for item in candidate.states}:
            score += 0.10; signals += 1
        return min(score + (0.6 if signals >= 3 else 0.0), 1.0), signals
