"""Tests for the /blogs full-pipeline entry and the AI keyword-selection layer."""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.base import uuid_str
from app.models.blog import BlogDraft, BlogJob
from app.models.onboarding import Brand, BrandProfile, Job
from app.services import seo_research
from tests.conftest import FakeQueue, auth_headers, create_user


def _ready_brand(db: Session, user) -> Brand:
    brand = Brand(
        org_id=user.org_id,
        name="Acme",
        website_url="https://acme.example",
        dna_source="crawl",
        status="READY",
        created_by=user.id,
    )
    db.add(brand)
    db.flush()
    db.add(BrandProfile(
        brand_id=brand.id,
        name="Acme",
        one_liner="We make robots.",
        tone_rules="Friendly.",
        unique_angle="Spatial robotics.",
        generation_source="manual",
    ))
    db.commit()
    return brand


def test_create_blog_runs_keyword_research_pipeline(
    client: TestClient, db_session: Session, fake_queues: dict[str, FakeQueue]
) -> None:
    user = create_user(db_session, "blog-admin@example.com")
    brand = _ready_brand(db_session, user)

    resp = client.post(
        f"/v1/brands/{brand.id}/blogs",
        headers=auth_headers(user),
        json={"keyword": "running shoes for flat feet"},
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # The entry point is now Pipeline 1 (keyword research), not content generation.
    enqueued = [c for q in fake_queues.values() for c in q.calls]
    assert any("run_keyword_research_pipeline" in c.func for c in enqueued)
    assert not any("content_generation" in c.func for c in enqueued)

    # The pipeline job shares the BlogJob id and links the draft back via blog_job_id.
    pipeline_job = db_session.query(Job).filter(Job.id == job_id).first()
    assert pipeline_job is not None
    assert pipeline_job.job_type == "keyword_research"
    assert pipeline_job.input_payload["blog_job_id"] == job_id
    assert pipeline_job.input_payload["blog_integration"] is True


def test_blog_status_pending_review_when_draft_ready(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session, "blog-status@example.com")
    brand = _ready_brand(db_session, user)
    job_id = uuid_str()

    db_session.add(BlogJob(id=job_id, org_id=user.org_id, brand_id=brand.id,
                           created_by=user.id, keyword="kw", status="GENERATING"))
    db_session.add(Job(id=job_id, org_id=user.org_id, brand_id=brand.id,
                       job_type="keyword_research", status="SUCCEEDED", stage="CONTENT",
                       input_payload={"keyword": "kw", "blog_job_id": job_id}))
    # Draft keyed to the BlogJob id is the completion signal.
    db_session.add(BlogDraft(id=uuid_str(), job_id=job_id, title="T",
                             meta_description="A primer.", html_content="<h1>Done</h1>"))
    db_session.commit()

    resp = client.get(f"/v1/brands/{brand.id}/blogs/{job_id}", headers=auth_headers(user))
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING_REVIEW"


def test_select_primary_target_keyword_falls_back_to_top_score(monkeypatch) -> None:
    scored = [
        {"related_keyword": "running shoes", "search_volume": 90000, "keyword_difficulty": 70},
        {"related_keyword": "running shoes for flat feet", "search_volume": 8000, "keyword_difficulty": 30},
    ]

    class BoomLLM:
        async def call(self, *_a, **_k):
            raise RuntimeError("LLM down")

    monkeypatch.setattr("app.services.llm.LLMService", BoomLLM)
    chosen = asyncio.run(
        seo_research.select_primary_target_keyword("running shoes for flat feet", scored)
    )
    # On LLM failure it falls back to the highest-scoring (first) candidate.
    assert chosen == "running shoes"


def test_select_primary_target_keyword_uses_ai_pick(monkeypatch) -> None:
    scored = [
        {"related_keyword": "running shoes", "search_volume": 90000, "keyword_difficulty": 70},
        {"related_keyword": "running shoes for flat feet", "search_volume": 8000, "keyword_difficulty": 30},
    ]

    class PickLLM:
        async def call(self, *_a, **_k):
            return '{"keyword": "running shoes for flat feet", "reason": "stays on intent"}'

    monkeypatch.setattr("app.services.llm.LLMService", PickLLM)
    chosen = asyncio.run(
        seo_research.select_primary_target_keyword("running shoes for flat feet", scored)
    )
    assert chosen == "running shoes for flat feet"


def test_select_primary_target_keyword_rejects_invalid_pick(monkeypatch) -> None:
    scored = [{"related_keyword": "running shoes", "search_volume": 90000, "keyword_difficulty": 70}]

    class HallucinateLLM:
        async def call(self, *_a, **_k):
            return '{"keyword": "something not in the list"}'

    monkeypatch.setattr("app.services.llm.LLMService", HallucinateLLM)
    chosen = asyncio.run(seo_research.select_primary_target_keyword("running shoes", scored))
    # A keyword outside the candidate set is rejected; falls back to top score.
    assert chosen == "running shoes"


# --- Content-generation JSON parsing & outline robustness (regression for the
#     truncated-LLM-JSON -> empty-outline crash found during a live staging run) ---

from app.services.content_generation import safe_json_parse, parse_and_validate_outline


def test_safe_json_parse_strips_fences_and_prose() -> None:
    assert safe_json_parse("Here is the JSON:\n```json\n{\"a\": 1}\n```\nThanks!") == {"a": 1}
    assert safe_json_parse("```json\n{\"slug\": \"x\", \"sections\": []}\n```")["slug"] == "x"
    assert safe_json_parse("{\"plain\": true}") == {"plain": True}


def test_safe_json_parse_returns_empty_on_truncation() -> None:
    # A response cut off mid-object (hit max_tokens) must not raise.
    assert safe_json_parse("```json\n{\"goal\": \"establish auth") == {}
    assert safe_json_parse(None) == {}  # type: ignore[arg-type]


def test_outline_falls_back_instead_of_crashing() -> None:
    # Empty outline + provided fallback headings -> uses the fallbacks.
    o = parse_and_validate_outline({"sections": []}, ["Intro", "Tips"])
    assert [s.heading for s in o.sections] == ["Intro", "Tips"]
    assert [s.index for s in o.sections] == [0, 1]

    # Empty outline + no fallback -> generic non-empty default (never crashes).
    assert len(parse_and_validate_outline({"sections": []}).sections) >= 1


def test_outline_skips_malformed_sections() -> None:
    o = parse_and_validate_outline({"sections": [{"heading": "A"}, {"no": "heading"}, "B"]})
    assert [s.heading for s in o.sections] == ["A", "B"]


# --- LLM type-variance coercion (regression for the ContentBrief ValidationError:
#     target_audience returned as a list, target_word_count as a "2400-2800" range) ---

from app.services.content_generation import ContentBrief, ValidatedSection


def test_content_brief_coerces_list_audience_and_range_word_count() -> None:
    cb = ContentBrief(
        goal="g", content_type="blog_post",
        target_audience=["Urban homeowners", "wellness seekers"],  # list -> joined str
        search_intent="informational",
        target_word_count="2400-2800",                              # range -> midpoint int
        content_angle="guide",
        ctas="Shop now",                                            # str -> [str]
        sections=["Intro", {"heading": "Body"}],                    # mixed -> list[dict]
    )
    assert cb.target_audience == "Urban homeowners, wellness seekers"
    assert cb.target_word_count == 2600
    assert cb.ctas == ["Shop now"]
    assert cb.sections == [{"heading": "Intro"}, {"heading": "Body"}]


def test_validated_section_coerces_variant_types() -> None:
    vs = ValidatedSection(index=0, heading=["A", "B"], phases="Explain", estimated_words="250-350")
    assert vs.heading == "A, B"
    assert vs.phases == ["Explain"]
    assert vs.estimated_words == 300  # midpoint of 250-350
