from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.base import uuid_str
from app.models.blog import (
    BLOG_STATUS_BRIEFING,
    BLOG_STATUS_FAILED,
    BLOG_STATUS_PENDING_BRIEF_REVIEW,
    BLOG_STATUS_PENDING_REVIEW,
    BLOG_STATUS_RESEARCHING,
    BLOG_STATUS_WRITING,
    BlogBrief,
    BlogDraft,
    BlogJob,
    BlogSection,
)
from app.models.onboarding import BrandProfile
from app.services.llm import LLMError, LLMService, safe_json_parse
from app.services.prompts import render_prompt
from app.services.seo_research import fetch_serp_data, format_serp_for_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry point (called from RQ worker)
# ---------------------------------------------------------------------------

def run_blog_research_and_brief(db: Session, *, job_id: str) -> None:
    """Sync RQ entry point: runs research + brief generation."""
    asyncio.run(_research_and_brief(db, job_id=job_id))


def run_blog_writing(db: Session, *, job_id: str) -> None:
    """Sync RQ entry point: runs section writing after brief is approved."""
    asyncio.run(_write_article(db, job_id=job_id))


# ---------------------------------------------------------------------------
# Stage 1 & 2: Research + Brief
# ---------------------------------------------------------------------------

async def _research_and_brief(db: Session, *, job_id: str) -> None:
    job = db.query(BlogJob).filter(BlogJob.id == job_id).one_or_none()
    if not job:
        logger.error("BlogJob %s not found", job_id)
        return

    job.attempt_count = (job.attempt_count or 0) + 1

    try:
        # Stage 1: SERP research
        job.status = BLOG_STATUS_RESEARCHING
        db.commit()

        serp = await fetch_serp_data(job.keyword)
        serp_text = format_serp_for_prompt(serp)

        # Stage 2: Brief generation
        job.status = BLOG_STATUS_BRIEFING
        db.commit()

        profile = db.query(BrandProfile).filter(BrandProfile.brand_id == job.brand_id).first()
        if not profile:
            raise ValueError(f"Brand profile not found for brand {job.brand_id}")

        prompt = render_prompt("blog/v1/brief.txt", {
            "brand_name": profile.name,
            "industry": profile.industry or "",
            "one_liner": profile.one_liner,
            "tone_rules": profile.tone_rules,
            "audience_personas": profile.audience_personas or [],
            "unique_angle": profile.unique_angle,
            "allowed_topics": profile.allowed_topics or [],
            "disallowed_topics": profile.disallowed_topics or [],
            "keyword": job.keyword,
            "serp_data": serp_text,
        })

        s = get_settings()
        llm = LLMService()
        raw = await llm.call(
            model=s.blog_model,
            prompt=prompt,
            response_format="json",
            max_tokens=s.blog_brief_max_tokens,
            temperature=0.4,
        )
        data = safe_json_parse(raw)

        # Delete old brief if retrying
        existing = db.query(BlogBrief).filter(BlogBrief.job_id == job.id).first()
        if existing:
            db.delete(existing)
            db.flush()

        brief = BlogBrief(
            id=uuid_str(),
            job_id=job.id,
            selected_title=data.get("selected_title", data.get("titles", ["Untitled"])[0]),
            title_options=data.get("titles", []),
            meta_description=data.get("meta_description", ""),
            search_intent=data.get("search_intent", "informational"),
            target_word_count=int(data.get("target_word_count", 1500)),
            target_audience=data.get("target_audience"),
            keyword_variants=data.get("keyword_variants", []),
            outline=data.get("outline", []),
            aeo=data.get("aeo", {}),
            tags=data.get("tags", []),
            serp_snapshot=serp,
        )
        db.add(brief)

        job.status = BLOG_STATUS_PENDING_BRIEF_REVIEW
        db.commit()
        logger.info("Brief generated for job %s — awaiting review", job_id)

    except Exception as exc:
        logger.exception("Blog brief failed for job %s", job_id)
        db.rollback()
        _mark_failed(db, job, str(exc))


# ---------------------------------------------------------------------------
# Stage 3: Writing (after brief approval)
# ---------------------------------------------------------------------------

async def _write_article(db: Session, *, job_id: str) -> None:
    job = db.query(BlogJob).filter(BlogJob.id == job_id).one_or_none()
    if not job or not job.brief:
        logger.error("BlogJob %s or its brief not found", job_id)
        return

    try:
        job.status = BLOG_STATUS_WRITING
        db.commit()

        profile = db.query(BrandProfile).filter(BrandProfile.brand_id == job.brand_id).first()
        if not profile:
            raise ValueError("Brand profile not found")

        brief = job.brief
        outline = brief.outline

        # Delete old sections if retrying
        db.query(BlogSection).filter(BlogSection.job_id == job.id).delete()
        db.flush()

        # Create section rows
        sections = []
        for idx, item in enumerate(outline):
            sec = BlogSection(
                id=uuid_str(),
                job_id=job.id,
                section_index=idx,
                heading=item.get("heading", f"Section {idx+1}"),
                heading_type=item.get("type", "h2"),
                key_points=item.get("key_points", []),
                estimated_words=int(item.get("estimated_words", 200)),
                status="PENDING",
            )
            db.add(sec)
            sections.append(sec)
        db.commit()

        # Generate sections in parallel (batches of 3 to avoid rate limits)
        s = get_settings()
        llm = LLMService()
        total = len(sections)

        async def generate_section(sec: BlogSection) -> None:
            prompt = render_prompt("blog/v1/section.txt", {
                "brand_name": profile.name,
                "tone_rules": profile.tone_rules,
                "unique_angle": profile.unique_angle,
                "banned_phrases": profile.banned_phrases or [],
                "audience_personas": profile.audience_personas or [],
                "title": brief.selected_title,
                "keyword": job.keyword,
                "section_index": sec.section_index + 1,
                "total_sections": total,
                "heading": sec.heading,
                "heading_type": sec.heading_type,
                "key_points": sec.key_points,
                "estimated_words": sec.estimated_words,
            })
            try:
                html = await llm.call(
                    model=s.blog_model,
                    prompt=prompt,
                    response_format="text",
                    max_tokens=s.blog_section_max_tokens,
                    temperature=0.6,
                )
                sec.content_html = html.strip()
                sec.word_count = len(re.sub(r"<[^>]+>", "", html).split())
                sec.status = "GENERATED"
            except LLMError as exc:
                logger.warning("Section %d failed: %s", sec.section_index, exc)
                sec.status = "FAILED"
                sec.content_html = f"<p>[Generation failed: {exc}]</p>"

        # Run in batches of 3
        batch_size = 3
        for i in range(0, len(sections), batch_size):
            batch = sections[i:i + batch_size]
            await asyncio.gather(*[generate_section(s_) for s_ in batch])
            db.commit()

        # Assemble article
        intro_html = _build_intro(brief)
        body_html = "\n\n".join(sec.content_html or "" for sec in sections)
        faq_html = _build_faq(brief)
        full_html = f"{intro_html}\n\n{body_html}\n\n{faq_html}".strip()

        total_words = sum(sec.word_count for sec in sections)
        seo_score = _calc_seo_score(full_html, job.keyword, brief.meta_description)
        aeo_score = _calc_aeo_score(brief)
        virality_score = _calc_virality_score(total_words, seo_score, aeo_score)

        # Delete old draft if retrying
        existing_draft = db.query(BlogDraft).filter(BlogDraft.job_id == job.id).first()
        if existing_draft:
            db.delete(existing_draft)
            db.flush()

        draft = BlogDraft(
            id=uuid_str(),
            job_id=job.id,
            title=brief.selected_title,
            meta_description=brief.meta_description,
            html_content=full_html,
            word_count=total_words,
            seo_score=seo_score,
            aeo_score=aeo_score,
            virality_score=virality_score,
        )
        db.add(draft)
        job.status = BLOG_STATUS_PENDING_REVIEW
        db.commit()
        logger.info("Article written for job %s — awaiting review", job_id)

    except Exception as exc:
        logger.exception("Blog writing failed for job %s", job_id)
        db.rollback()
        _mark_failed(db, job, str(exc))


# ---------------------------------------------------------------------------
# HTML assembly helpers
# ---------------------------------------------------------------------------

def _build_intro(brief: BlogBrief) -> str:
    direct_answer = brief.aeo.get("direct_answer", "")
    if not direct_answer:
        return ""
    return f'<p class="direct-answer"><strong>{direct_answer}</strong></p>'


def _build_faq(brief: BlogBrief) -> str:
    faqs = brief.aeo.get("faqs", [])
    if not faqs:
        return ""
    items = "\n".join(
        f"<div class='faq-item'><h3>{faq['question']}</h3><p>{faq['answer']}</p></div>"
        for faq in faqs
    )
    return f"<section class='faq'>\n<h2>Frequently Asked Questions</h2>\n{items}\n</section>"


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _calc_seo_score(html: str, keyword: str, meta_desc: str) -> int:
    score = 0
    text = re.sub(r"<[^>]+>", "", html).lower()
    kw = keyword.lower()

    # Keyword in content
    count = text.count(kw)
    if count >= 3:
        score += 30
    elif count >= 1:
        score += 15

    # Keyword in meta description
    if kw in meta_desc.lower():
        score += 20

    # Meta description length
    if 140 <= len(meta_desc) <= 165:
        score += 15

    # H2 headings present
    h2_count = html.lower().count("<h2")
    if h2_count >= 3:
        score += 20
    elif h2_count >= 1:
        score += 10

    # Word count
    word_count = len(text.split())
    if word_count >= 1200:
        score += 15
    elif word_count >= 800:
        score += 8

    return min(score, 100)


def _calc_aeo_score(brief: BlogBrief) -> int:
    score = 0
    aeo = brief.aeo
    if aeo.get("direct_answer"):
        score += 35
    faqs = aeo.get("faqs", [])
    if len(faqs) >= 3:
        score += 35
    elif len(faqs) >= 1:
        score += 20
    if len(aeo.get("entities", [])) >= 3:
        score += 30
    return min(score, 100)


def _calc_virality_score(word_count: int, seo: int, aeo: int) -> int:
    wc_score = min(word_count / 20, 30)
    return min(int(wc_score + seo * 0.4 + aeo * 0.3), 100)


# ---------------------------------------------------------------------------
# Failure helper
# ---------------------------------------------------------------------------

def _mark_failed(db: Session, job: BlogJob, message: str) -> None:
    try:
        job.status = BLOG_STATUS_FAILED
        job.error_message = message
        db.commit()
    except Exception:
        db.rollback()
