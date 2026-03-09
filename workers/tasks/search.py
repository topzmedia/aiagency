"""Search tasks: process a search query and rank candidate videos."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select

from workers.celery_app import app
from workers.db import get_sync_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _prefilter_candidates(
    session: Any,
    parsed_query: dict[str, Any],
    search: Any,
) -> list[Any]:
    """Return a list of CandidateVideo objects that pass basic keyword and
    metadata pre-filters.  This avoids running expensive analysis on every
    candidate in the database."""
    from apps.api.models.candidate_video import CandidateVideo

    stmt = select(CandidateVideo)

    # Platform filter
    if search.platforms:
        stmt = stmt.where(CandidateVideo.platform.in_(search.platforms))

    # Date range filter
    if search.date_from:
        stmt = stmt.where(CandidateVideo.publish_date >= search.date_from)
    if search.date_to:
        stmt = stmt.where(CandidateVideo.publish_date <= search.date_to)

    # Language filter
    if search.language:
        stmt = stmt.where(CandidateVideo.language == search.language)

    # Region filter
    if search.region:
        stmt = stmt.where(CandidateVideo.region_hint == search.region)

    candidates = session.execute(stmt).scalars().all()

    # Keyword pre-filter on caption text
    keywords = set(parsed_query.get("entities", []) + parsed_query.get("actions", []))
    synonyms = set(parsed_query.get("synonyms", []))
    all_terms = keywords | synonyms
    exclude_terms = set(parsed_query.get("exclude", []))

    if all_terms:
        filtered = []
        for c in candidates:
            text = " ".join([
                c.caption_text or "",
                " ".join(c.hashtags_json or []),
            ]).lower()

            # Check exclusions
            if any(ex.lower() in text for ex in exclude_terms):
                continue

            # Check at least one keyword match
            if any(term.lower() in text for term in all_terms):
                filtered.append(c)

        # If keyword filter is too strict, fall back to all candidates
        if not filtered:
            filtered = list(candidates)
        candidates = filtered

    return candidates


def _score_candidate(
    candidate: Any,
    analysis: Any | None,
    parsed_query: dict[str, Any],
) -> tuple[float, dict[str, float], list[str]]:
    """Score a candidate video against the parsed query.

    Returns (final_score, score_breakdown, reason_codes).
    """
    breakdown: dict[str, float] = {}
    reasons: list[str] = []

    # 1. Caption/text relevance (0-0.35)
    caption_score = 0.0
    text_corpus = " ".join([
        candidate.caption_text or "",
        " ".join(candidate.hashtags_json or []),
    ]).lower()

    entities = parsed_query.get("entities", [])
    actions = parsed_query.get("actions", [])
    synonyms = parsed_query.get("synonyms", [])
    all_query_terms = entities + actions + synonyms

    if all_query_terms:
        matches = sum(1 for t in all_query_terms if t.lower() in text_corpus)
        caption_score = min(0.35, (matches / len(all_query_terms)) * 0.35)
        if matches > 0:
            reasons.append(f"caption_match:{matches}_terms")
    breakdown["caption_relevance"] = round(caption_score, 4)

    # 2. Analysis relevance (0-0.35)
    analysis_score = 0.0
    if analysis and analysis.status.value == "completed":
        analysis_text = " ".join([
            str(analysis.objects_json or ""),
            str(analysis.scenes_json or ""),
            str(analysis.actions_json or ""),
            analysis.transcript_text or "",
            str(analysis.ocr_text_json or ""),
        ]).lower()

        if all_query_terms:
            a_matches = sum(1 for t in all_query_terms if t.lower() in analysis_text)
            analysis_score = min(0.35, (a_matches / len(all_query_terms)) * 0.35)
            if a_matches > 0:
                reasons.append(f"analysis_match:{a_matches}_terms")
    breakdown["analysis_relevance"] = round(analysis_score, 4)

    # 3. Scene match bonus (0-0.15)
    scene_score = 0.0
    query_scenes = set(parsed_query.get("scenes", []))
    if analysis and analysis.scenes_json and query_scenes:
        detected = {s.get("label", "") for s in (analysis.scenes_json or [])}
        overlap = query_scenes & detected
        if overlap:
            scene_score = min(0.15, len(overlap) / len(query_scenes) * 0.15)
            reasons.append(f"scene_match:{','.join(overlap)}")
    breakdown["scene_match"] = round(scene_score, 4)

    # 4. Audio cue match (0-0.1)
    audio_score = 0.0
    query_audio = set(parsed_query.get("audio_events", []))
    if analysis and analysis.audio_events_json and query_audio:
        detected_audio = {e.get("label", "") for e in (analysis.audio_events_json or [])}
        audio_overlap = query_audio & detected_audio
        if audio_overlap:
            audio_score = min(0.1, len(audio_overlap) / len(query_audio) * 0.1)
            reasons.append(f"audio_match:{','.join(audio_overlap)}")
    breakdown["audio_match"] = round(audio_score, 4)

    # 5. Recency bonus (0-0.05)
    recency_score = 0.0
    if candidate.publish_date:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        try:
            pub = candidate.publish_date
            if pub.tzinfo is None:
                from datetime import timezone as tz
                pub = pub.replace(tzinfo=tz.utc)
            days_old = (now - pub).days
            if days_old < 30:
                recency_score = 0.05
            elif days_old < 90:
                recency_score = 0.03
            elif days_old < 365:
                recency_score = 0.01
        except Exception:
            pass
    breakdown["recency_bonus"] = round(recency_score, 4)

    # Penalties
    penalty = 0.0
    exclude_terms = parsed_query.get("exclude", [])
    if exclude_terms:
        for ex in exclude_terms:
            if ex.lower() in text_corpus:
                penalty += 0.2
                reasons.append(f"penalty:excluded_term:{ex}")
    breakdown["penalty"] = round(-penalty, 4)

    final = max(0.0, min(1.0, caption_score + analysis_score + scene_score + audio_score + recency_score - penalty))
    return round(final, 4), breakdown, reasons


def _deduplicate_results(
    rankings: list[dict[str, Any]],
    session: Any,
) -> list[dict[str, Any]]:
    """Mark near-duplicate entries in the result list.

    Uses a simple caption-text similarity approach: if two candidates share >80%
    of their caption tokens, the lower-ranked one is marked as a duplicate.
    """
    from apps.api.models.duplicate_group import DuplicateGroup

    if not rankings:
        return rankings

    def _tokenize(text: str) -> set[str]:
        return {w.lower().strip() for w in (text or "").split() if len(w) > 2}

    seen: list[tuple[set[str], str]] = []  # (token_set, group_key)

    for r in rankings:
        tokens = _tokenize(r.get("caption_text", ""))
        is_dup = False
        for seen_tokens, group_key in seen:
            if not tokens or not seen_tokens:
                continue
            overlap = len(tokens & seen_tokens) / max(len(tokens | seen_tokens), 1)
            if overlap > 0.8:
                # Mark as duplicate
                r["duplicate_group_key"] = group_key
                is_dup = True
                break
        if not is_dup:
            group_key = f"group_{r['candidate_video_id']}"
            seen.append((tokens, group_key))
            r["duplicate_group_key"] = None

    return rankings


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------

@app.task(name="workers.tasks.search.process_search", bind=True, max_retries=2)
def process_search(self, search_id: str) -> dict:
    """Full search pipeline: parse query, prefilter, analyze, score, rank, dedup."""
    from apps.api.models.search import Search, SearchStatus
    from apps.api.models.video_analysis import VideoAnalysis, AnalysisStatus
    from apps.api.models.result_ranking import ResultRanking
    from apps.api.models.duplicate_group import DuplicateGroup
    from apps.api.services.query_interpreter import interpret_query

    session = get_sync_session()
    try:
        search = session.get(Search, uuid.UUID(search_id))
        if search is None:
            logger.error("Search %s not found", search_id)
            return {"error": "search_not_found"}

        # Mark as processing
        search.status = SearchStatus.processing
        search.progress_percent = 5
        session.commit()

        # 1. Parse the query
        parsed = interpret_query(
            search.raw_query,
            include_filters=search.include_filters_json,
            exclude_filters=search.exclude_filters_json,
        )
        search.normalized_query_json = parsed.to_dict()
        search.progress_percent = 10
        session.commit()

        # 2. Prefilter candidates
        candidates = _prefilter_candidates(session, parsed.to_dict(), search)
        search.total_candidates = len(candidates)
        search.progress_percent = 20
        session.commit()

        if not candidates:
            search.status = SearchStatus.completed
            search.progress_percent = 100
            search.total_results = 0
            session.commit()
            return {"search_id": search_id, "status": "completed", "total_results": 0}

        # 3. Check/ensure analysis exists for top candidates
        analyzed_count = 0
        for i, candidate in enumerate(candidates):
            # Check if analysis already exists
            analysis = session.execute(
                select(VideoAnalysis).where(
                    VideoAnalysis.candidate_video_id == candidate.id
                )
            ).scalar_one_or_none()

            if analysis is None:
                # Create a placeholder analysis with pending status
                analysis = VideoAnalysis(
                    id=uuid.uuid4(),
                    candidate_video_id=candidate.id,
                    status=AnalysisStatus.pending,
                )
                session.add(analysis)

            if analysis.status == AnalysisStatus.completed:
                analyzed_count += 1

            # Update progress periodically
            if i % 10 == 0:
                pct = 20 + int((i / len(candidates)) * 30)
                search.progress_percent = min(pct, 50)
                session.commit()

        search.total_analyzed = analyzed_count
        search.progress_percent = 50
        session.commit()

        # 4. Score all candidates
        scored: list[dict[str, Any]] = []
        for i, candidate in enumerate(candidates):
            analysis = session.execute(
                select(VideoAnalysis).where(
                    VideoAnalysis.candidate_video_id == candidate.id
                )
            ).scalar_one_or_none()

            final_score, breakdown, reasons = _score_candidate(
                candidate, analysis, parsed.to_dict(),
            )

            if final_score >= search.confidence_threshold:
                scored.append({
                    "candidate_video_id": str(candidate.id),
                    "final_score": final_score,
                    "score_breakdown": breakdown,
                    "reason_codes": reasons,
                    "caption_text": candidate.caption_text or "",
                })

            if i % 10 == 0:
                pct = 50 + int((i / len(candidates)) * 30)
                search.progress_percent = min(pct, 80)
                session.commit()

        # 5. Rank by score
        scored.sort(key=lambda x: x["final_score"], reverse=True)
        scored = scored[:search.max_results]

        # 6. Deduplicate
        scored = _deduplicate_results(scored, session)

        search.progress_percent = 90
        session.commit()

        # 7. Store result rankings
        for rank, entry in enumerate(scored, start=1):
            dup_group_id = None
            dup_key = entry.get("duplicate_group_key")
            if dup_key:
                # Find or create duplicate group
                existing_group = session.execute(
                    select(DuplicateGroup).where(DuplicateGroup.group_key == dup_key)
                ).scalar_one_or_none()
                if existing_group:
                    dup_group_id = existing_group.id
                else:
                    new_group = DuplicateGroup(
                        id=uuid.uuid4(),
                        group_key=dup_key,
                        representative_candidate_video_id=uuid.UUID(entry["candidate_video_id"]),
                    )
                    session.add(new_group)
                    session.flush()
                    dup_group_id = new_group.id

            ranking = ResultRanking(
                id=uuid.uuid4(),
                search_id=uuid.UUID(search_id),
                candidate_video_id=uuid.UUID(entry["candidate_video_id"]),
                final_score=entry["final_score"],
                rank_position=rank,
                accepted=entry.get("duplicate_group_key") is None,
                reason_codes_json=entry.get("reason_codes"),
                score_breakdown_json=entry.get("score_breakdown"),
                duplicate_group_id=dup_group_id,
            )
            session.add(ranking)

        # 8. Finalize search
        search.total_results = len(scored)
        search.status = SearchStatus.completed
        search.progress_percent = 100
        session.commit()

        logger.info(
            "Search %s completed: %d candidates -> %d results",
            search_id, len(candidates), len(scored),
        )
        return {
            "search_id": search_id,
            "status": "completed",
            "total_candidates": len(candidates),
            "total_results": len(scored),
        }

    except Exception as exc:
        session.rollback()
        logger.exception("Search %s failed: %s", search_id, exc)
        try:
            search = session.get(Search, uuid.UUID(search_id))
            if search:
                search.status = SearchStatus.failed
                search.error_message = str(exc)
                session.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=15)
    finally:
        session.close()


@app.task(name="workers.tasks.search.rerank_search", bind=True, max_retries=1)
def rerank_search(self, search_id: str) -> dict:
    """Re-score and re-rank existing results for a search."""
    from apps.api.models.search import Search, SearchStatus
    from apps.api.models.result_ranking import ResultRanking
    from apps.api.models.candidate_video import CandidateVideo
    from apps.api.models.video_analysis import VideoAnalysis
    from apps.api.services.query_interpreter import interpret_query

    session = get_sync_session()
    try:
        search = session.get(Search, uuid.UUID(search_id))
        if search is None:
            return {"error": "search_not_found"}

        parsed = interpret_query(
            search.raw_query,
            include_filters=search.include_filters_json,
            exclude_filters=search.exclude_filters_json,
        )

        # Get existing rankings
        rankings = session.execute(
            select(ResultRanking).where(ResultRanking.search_id == uuid.UUID(search_id))
        ).scalars().all()

        if not rankings:
            return {"search_id": search_id, "status": "no_results_to_rerank"}

        # Re-score each
        rescored = []
        for r in rankings:
            candidate = session.get(CandidateVideo, r.candidate_video_id)
            if candidate is None:
                continue
            analysis = session.execute(
                select(VideoAnalysis).where(
                    VideoAnalysis.candidate_video_id == candidate.id
                )
            ).scalar_one_or_none()

            final_score, breakdown, reasons = _score_candidate(
                candidate, analysis, parsed.to_dict(),
            )
            r.final_score = final_score
            r.score_breakdown_json = breakdown
            r.reason_codes_json = reasons
            rescored.append(r)

        # Re-rank
        rescored.sort(key=lambda x: x.final_score, reverse=True)
        for rank, r in enumerate(rescored, start=1):
            r.rank_position = rank

        session.commit()

        logger.info("Reranked search %s: %d results", search_id, len(rescored))
        return {"search_id": search_id, "status": "reranked", "total_results": len(rescored)}

    except Exception as exc:
        session.rollback()
        logger.exception("Rerank search %s failed: %s", search_id, exc)
        raise self.retry(exc=exc, countdown=10)
    finally:
        session.close()
