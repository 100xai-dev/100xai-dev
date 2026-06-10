# app/services/content_generation.py
import asyncio
import json
import logging
import re
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config import get_settings
from app.models.blog import BlogJob, BlogBrief, BlogSection, BlogDraft
from app.models.onboarding import BrandProfile, Job
from app.models.serp_analysis import SerpAnalysis, CompetitorAnalysis
from app.services.llm import LLMService
from app.services.leonardo import LeonardoService
from app.services.placid import PlacidService
from app.services.blog_pipeline import _calc_seo_score, _calc_virality_score

logger = logging.getLogger(__name__)


def _calc_aeo_score_from_html(html: str) -> int:
    """Estimate AEO score from generated HTML without needing a BlogBrief."""
    score = 0
    if "FAQPage" in html:
        score += 35
    if 'class="direct-answer"' in html or "<strong>" in html[:500]:
        score += 35
    h_count = html.lower().count("<h2") + html.lower().count("<h3")
    if h_count >= 6:
        score += 30
    elif h_count >= 3:
        score += 15
    return min(score, 100)

# Job stage constants for Pipeline 3
JOB_STAGE_CONTENT = "CONTENT"
JOB_STAGE_DRAFT = "DRAFT"
JOB_STAGE_IMAGE = "IMAGE"
JOB_STAGE_COMPLETE = "COMPLETE"

# Content generation data models
class SerpAnalysisData(BaseModel):
    keywords: List[tuple[str, Optional[float], Optional[int], Optional[float]]]  # (keyword, score, volume, difficulty)
    competitor_gaps: List[str]
    competitive_advantages: List[str]
    serp_metadata: Dict

class ContentBrief(BaseModel):
    goal: str
    content_type: str
    target_audience: str
    search_intent: str
    target_word_count: int
    content_angle: str
    ctas: List[str]
    sections: List[dict]

class MetaAndOutline(BaseModel):
    slug: str
    meta_title: str
    meta_description: str
    h1: str
    sections: List[dict]

class ValidatedSection(BaseModel):
    index: int
    heading: str
    heading_type: str = "h2"
    phases: List[str]
    estimated_words: int = 300

class ValidatedOutline(BaseModel):
    sections: List[ValidatedSection]

class GeneratedSection(BaseModel):
    index: int
    heading: str
    heading_type: str
    content: str
    word_count: int

class AssembledContent(BaseModel):
    introduction: str
    table_of_contents: str
    body: str
    conclusion: str
    brand_value_section: Optional[str] = None  # "How [Brand] helps you in this"
    faq_section: Optional[str] = None
    total_word_count: int

class LinkData(BaseModel):
    url: str
    anchor_text: str
    link_type: str  # "internal", "external", "source", "product", "service"
    description: Optional[str] = None
    rel_attributes: Optional[str] = "noopener"  # "nofollow noopener", "sponsored noopener", etc.

class SourceCitation(BaseModel):
    title: str
    url: str
    author: Optional[str] = None
    publication: Optional[str] = None
    date: Optional[str] = None
    relevance_score: float = 1.0

class LinkStrategy(BaseModel):
    internal_links: List[LinkData] = []
    source_citations: List[SourceCitation] = []
    product_links: List[LinkData] = []
    external_references: List[LinkData] = []

class LinkData(BaseModel):
    url: str
    anchor_text: str
    link_type: str  # "internal", "external", "source", "product", "service", "affiliate"
    description: Optional[str] = None
    rel_attributes: Optional[str] = "noopener"  # "nofollow noopener", "sponsored noopener", etc.
    priority: str = "medium"  # "high", "medium", "low"
    keywords: List[str] = []
    target_blank: bool = True  # Open in new tab for external links

class SourceCitation(BaseModel):
    title: str
    url: str
    author: Optional[str] = None
    publication: Optional[str] = None
    date: Optional[str] = None
    relevance_score: float = 1.0
    trust_level: str = "medium"  # "high", "medium", "low"
    citation_style: str = "inline"  # "inline", "reference", "footnote"

class LinkStrategy(BaseModel):
    internal_links: List[LinkData] = []
    source_citations: List[SourceCitation] = []
    product_links: List[LinkData] = []
    external_references: List[LinkData] = []
    affiliate_links: List[LinkData] = []
    max_links_per_section: int = 3
    require_disclosures: bool = True

class FinalArticle(BaseModel):
    meta_title: str
    meta_description: str
    slug: str
    html_content: str
    word_count: int
    links_added: List[LinkData] = []
    sources_cited: List[SourceCitation] = []
    link_disclosures: List[str] = []

# Core content generation functions
async def load_serp_analysis(job_id: str, brand_id: str, db: Session, serp_job_id: str = None) -> SerpAnalysisData:
    """Load + aggregate SERP analysis from Pipeline 2
    
    Args:
        job_id: Current content generation job ID
        brand_id: Brand ID
        db: Database session
        serp_job_id: Optional specific SERP job ID to load from
    """
    
    # If serp_job_id provided, use it. Otherwise get the most recent SERP analysis for this brand
    if serp_job_id:
        serp_analyses = db.query(SerpAnalysis).filter(
            SerpAnalysis.brand_id == brand_id,
            SerpAnalysis.job_id == serp_job_id
        ).all()
    else:
        # Get most recent SERP analyses for this brand (regardless of job_id)
        serp_analyses = db.query(SerpAnalysis).filter(
            SerpAnalysis.brand_id == brand_id
        ).order_by(SerpAnalysis.created_at.desc()).limit(20).all()
    
    competitor_analyses = []
    for serp in serp_analyses:
        competitors = db.query(CompetitorAnalysis).filter(
            CompetitorAnalysis.serp_analysis_id == serp.id
        ).all()
        competitor_analyses.extend(competitors)
    
    # Also get keyword research data for volume/difficulty
    from app.models.keyword import Keyword
    keyword_data = {}
    
    # If we have SERP analyses, get matching keywords
    if serp_analyses:
        keyword_texts = [s.keyword_text for s in serp_analyses]
        keywords = db.query(Keyword).filter(
            Keyword.brand_id == brand_id,
            Keyword.related_keyword.in_(keyword_texts)
        ).all()
    else:
        # Fallback: Get top keywords from Pipeline 1 if no SERP data
        logger.info("No SERP analyses found, falling back to top keywords from keyword research")
        keywords = db.query(Keyword).filter(
            Keyword.brand_id == brand_id
        ).order_by(Keyword.score.desc().nullslast()).limit(20).all()
        
    keyword_data = {kw.related_keyword: {
        "search_volume": kw.search_volume,
        "difficulty": kw.keyword_difficulty,
        "cpc": kw.cpc,
        "score": kw.score
    } for kw in keywords}
    
    # Combine SERP analysis scores with keyword research data
    enhanced_keywords = []
    
    if serp_analyses:
        # Use SERP analysis data with keyword research enrichment
        for s in serp_analyses:
            kw_data = keyword_data.get(s.keyword_text, {})
            enhanced_keywords.append((
                s.keyword_text, 
                s.content_gap_score or kw_data.get("score", 0),
                kw_data.get("search_volume"),
                kw_data.get("difficulty")
            ))
    else:
        # Fallback: Use keyword research data directly
        for kw in keywords:
            enhanced_keywords.append((
                kw.related_keyword,
                kw.score or 0,
                kw.search_volume,
                kw.keyword_difficulty
            ))
    
    return SerpAnalysisData(
        keywords=enhanced_keywords,  # Now includes volume and difficulty
        competitor_gaps=extract_content_gaps(competitor_analyses),
        competitive_advantages=identify_advantages(competitor_analyses),
        serp_metadata=compile_serp_metadata(serp_analyses)
    )

def extract_content_gaps(competitor_analyses: List[CompetitorAnalysis]) -> List[str]:
    """Extract content gaps from competitor analysis"""
    gaps = []
    for comp in competitor_analyses:
        if comp.content_gaps:
            if isinstance(comp.content_gaps, list):
                gaps.extend(comp.content_gaps)
            elif isinstance(comp.content_gaps, str):
                gaps.append(comp.content_gaps)
    return gaps[:10]  # Top 10 gaps

def identify_advantages(competitor_analyses: List[CompetitorAnalysis]) -> List[str]:
    """Identify competitive advantages from analysis"""
    advantages = []
    for comp in competitor_analyses:
        # DB model column is `competitive_advantage` (singular Text); handle
        # both string and (defensively) list shapes.
        if comp.competitive_advantage:
            if isinstance(comp.competitive_advantage, list):
                advantages.extend(comp.competitive_advantage)
            elif isinstance(comp.competitive_advantage, str):
                advantages.append(comp.competitive_advantage)
    return advantages[:5]  # Top 5 advantages

def compile_serp_metadata(serp_analyses: List[SerpAnalysis]) -> Dict:
    """Compile SERP metadata for content generation"""
    return {
        "avg_content_score": sum(s.content_gap_score or 0 for s in serp_analyses) / max(len(serp_analyses), 1),
        "total_keywords": len(serp_analyses),
        "analyzed_urls": [s.top_competitor_url for s in serp_analyses if s.top_competitor_url],
        "analysis_date": max(s.created_at for s in serp_analyses) if serp_analyses else None
    }

def _brand_knowledge_block(brand_knowledge: str) -> str:
    """Render retrieved brand knowledge as a prompt block, or '' when empty.

    When empty, the prompt is byte-identical to the pre-RAG version (backward
    compatible for brands without ingested vectors).
    """
    if not brand_knowledge or not brand_knowledge.strip():
        return ""
    return (
        "\nBRAND KNOWLEDGE (verified facts from this brand's own material — "
        "ground the content in these and do not contradict or invent details):\n"
        f"{brand_knowledge.strip()}\n"
    )


async def generate_content_brief(
    serp_data: SerpAnalysisData,
    brand_profile: BrandProfile,
    target_keyword: str,
    brand_knowledge: str = ""
) -> ContentBrief:
    """AI · reads brand profile + serp data (+ retrieved brand knowledge) → content brief"""

    knowledge_block = _brand_knowledge_block(brand_knowledge)
    prompt = f"""Generate a comprehensive content brief for a blog article.

BRAND PROFILE:
- Brand: {brand_profile.name}
- One-liner: {brand_profile.one_liner}
- Industry: {brand_profile.industry or 'General'}
- Tone: {brand_profile.tone_rules}
- Unique Angle: {brand_profile.unique_angle}
- Target Audience: {', '.join(brand_profile.audience_personas)}
- CTAs: {', '.join(brand_profile.ctas)}

TARGET KEYWORD: {target_keyword}

COMPETITIVE INTELLIGENCE:
- Competitor Gaps: {', '.join(serp_data.competitor_gaps[:5])}
- Our Advantages: {', '.join(serp_data.competitive_advantages[:3])}
- Market Context: {serp_data.serp_metadata}
{knowledge_block}
Generate a content brief with:
1. Content goal and type
2. Target audience
3. Search intent
4. Target word count (1500-3000)
5. Unique content angle
6. Call-to-action suggestions
7. Article outline with exactly 8-10 main sections (each section should be substantial and cover different aspects)

IMPORTANT: Generate exactly 8-10 main sections for the table of contents.

Return ONLY a valid JSON object (no markdown, no prose) with keys: goal, type, audience, intent, word_count, angle, ctas, sections"""

    llm = LLMService()
    raw = await llm.call(
        model=get_settings().extraction_model,
        prompt=prompt,
        response_format="json",
        # A full 8-10 section brief for a 1500-3000 word article is large
        # structured JSON; 2000 truncated it mid-object. 4000 fits with margin.
        max_tokens=4000,
        temperature=0.4
    )
    
    data = safe_json_parse(raw)
    return ContentBrief(
        goal=data.get("goal", "Create engaging content"),
        content_type=data.get("type", "blog_post"),
        target_audience=data.get("audience", "General audience"),
        search_intent=data.get("intent", "informational"),
        target_word_count=data.get("word_count", 2000),
        content_angle=data.get("angle", "Comprehensive guide"),
        ctas=data.get("ctas", brand_profile.ctas[:2]),
        sections=data.get("sections", [])
    )

async def generate_meta_and_outline(
    content_brief: ContentBrief,
    brand_profile: BrandProfile,
    keyword: str
) -> MetaAndOutline:
    """AI · generate meta tags and detailed outline"""
    
    prompt = f"""Create SEO meta tags and detailed article outline.

CONTENT BRIEF:
- Goal: {content_brief.goal}
- Target Audience: {content_brief.target_audience}
- Word Count: {content_brief.target_word_count}
- Content Angle: {content_brief.content_angle}

BRAND: {brand_profile.name}
KEYWORD: {keyword}

Generate:
1. URL slug (lowercase, hyphens)
2. Meta title (50-60 chars, keyword included)
3. Meta description (150-160 chars)
4. H1 heading
5. Detailed outline with sections (each with heading, heading_type, phases for content, estimated_words)

Return ONLY a valid JSON object (no markdown, no prose) with keys: slug, meta_title, meta_description, h1, sections"""

    llm = LLMService()
    raw = await llm.call(
        model="anthropic/claude-haiku-4-5-20251001",  # Faster model for structured output
        prompt=prompt,
        response_format="json",
        # A detailed outline (8-10 sections, each with phases + word targets) for
        # a 1500-3000 word article overruns 1500 tokens; 4000 fits with margin.
        max_tokens=4000,
        temperature=0.3
    )
    
    data = safe_json_parse(raw)
    return MetaAndOutline(
        slug=data.get("slug", keyword.lower().replace(" ", "-")),
        meta_title=data.get("meta_title", f"{keyword} - {brand_profile.name}"),
        meta_description=data.get("meta_description", f"Complete guide to {keyword}"),
        h1=data.get("h1", keyword),
        sections=data.get("sections", [])
    )

_DEFAULT_OUTLINE_HEADINGS = [
    "Introduction",
    "Key Considerations",
    "Practical Tips",
    "Common Mistakes to Avoid",
    "Conclusion",
]


def _outline_section(heading: str, *, heading_type: str = "h2",
                     phases: list | None = None, estimated_words: int = 300) -> "ValidatedSection":
    return ValidatedSection(
        index=0,  # re-indexed by the caller below
        heading=heading,
        heading_type=heading_type,
        phases=phases or ["Introduce topic", "Provide details", "Conclude"],
        estimated_words=estimated_words,
    )


def parse_and_validate_outline(
    outline_data: dict,
    fallback_headings: list[str] | None = None,
) -> ValidatedOutline:
    """Parse + validate the outline, degrading gracefully instead of crashing.

    The LLM occasionally returns an empty/unparseable outline (e.g. a truncated
    response). Rather than failing the whole article, this skips malformed
    sections and, if none survive, builds a minimal outline from
    ``fallback_headings`` (derived from the brief / SERP by the caller) and
    finally a generic default. Only the wording degrades — the pipeline proceeds.
    """
    sections: list[ValidatedSection] = []
    for section in (outline_data.get("sections") or []):
        if isinstance(section, dict):
            heading = (section.get("heading") or "").strip()
            if not heading:
                continue
            sections.append(_outline_section(
                heading,
                heading_type=section.get("heading_type", "h2"),
                phases=section.get("phases", ["Introduce topic", "Provide details", "Conclude"]),
                estimated_words=section.get("estimated_words", 300),
            ))
        elif isinstance(section, str) and section.strip():
            # Tolerate a bare-string heading.
            sections.append(_outline_section(section.strip()))

    if not sections:
        headings = [h.strip() for h in (fallback_headings or []) if isinstance(h, str) and h.strip()]
        if not headings:
            headings = list(_DEFAULT_OUTLINE_HEADINGS)
        logger.warning(
            "Outline had no usable sections; falling back to %d derived headings", len(headings)
        )
        sections = [_outline_section(h) for h in headings]

    # Re-index sequentially so downstream batching/positioning is consistent.
    for i, section in enumerate(sections):
        section.index = i

    return ValidatedOutline(sections=sections)

async def generate_introduction(
    content_brief: ContentBrief,
    brand_profile: BrandProfile,
    keyword: str,
    sub_keywords: List[str] = None
) -> str:
    """Track 1 · intro - AI generates introduction (300–500w HTML)"""
    
    sub_keywords = sub_keywords or []
    sub_keywords_str = f"- Sub-keywords to include naturally (1-2 times each): {', '.join(sub_keywords[:3])}" if sub_keywords else ""
    
    banned_block = f"NEVER use these phrases: {', '.join(brand_profile.banned_phrases)}\n" if brand_profile.banned_phrases else ""
    site_url = brand_profile.site_url or ""
    brand_link = f'<a href="{site_url}">{brand_profile.name}</a>' if site_url else brand_profile.name

    prompt = f"""Write an engaging introduction for a blog article.

CONTENT BRIEF:
- Goal: {content_brief.goal}
- Content Angle: {content_brief.content_angle}
- Target Audience: {content_brief.target_audience}

BRAND VOICE:
- Tone: {brand_profile.tone_rules}
- Unique Angle: {brand_profile.unique_angle}
{banned_block}
KEYWORD OPTIMIZATION:
- Main Keyword: {keyword}
- Include main keyword 2-3 times naturally (targeting 2% density in full article)
{sub_keywords_str}

Write a 300-500 word introduction that:
1. Hooks the reader immediately with a concrete scenario, stat, or pain point the audience faces
2. Introduces the topic naturally with the keyword appearing in the first 100 words
3. Mentions {brand_profile.name} once naturally, linked: {brand_link}
4. Sets expectations for what they'll learn
5. Matches the brand voice and tone
6. Naturally integrates sub-keywords without forcing them

Return clean HTML using only <p>, <strong>, <em>, <a> tags. No heading tags."""
    
    llm = LLMService()
    return await llm.call(
        model=get_settings().extraction_model,
        prompt=prompt,
        response_format="text",
        max_tokens=800,
        temperature=0.6
    )

async def generate_body_sections(
    outline: ValidatedOutline,
    content_brief: ContentBrief,
    brand_profile: BrandProfile,
    keyword: str = None,
    sub_keywords: List[str] = None,
    brand_knowledge: str = ""
) -> List[GeneratedSection]:
    """Track 2 · body - Split sections → Loop per section"""

    sub_keywords = sub_keywords or []
    # Use a tighter grounding budget per section since this prompt runs once per
    # section (~8-10x); the shared string was already retrieved once per article.
    knowledge_block = _brand_knowledge_block(brand_knowledge[:2400] if brand_knowledge else "")

    async def generate_single_section(section: ValidatedSection) -> GeneratedSection:
        # Distribute sub-keywords across sections
        section_sub_keywords = sub_keywords[section.index:section.index+3] if sub_keywords else []
        sub_keywords_str = f"- Sub-keywords to include naturally: {', '.join(section_sub_keywords)}" if section_sub_keywords else ""
        banned_block = f"NEVER use these phrases: {', '.join(brand_profile.banned_phrases)}\n" if brand_profile.banned_phrases else ""
        site_url = brand_profile.site_url or ""

        prompt = f"""Write a comprehensive section for a blog article.

SECTION DETAILS:
- Heading: {section.heading}
- Phases to cover: {', '.join(section.phases)}
- Target length: {section.estimated_words} words
- Section {section.index + 1} of {len(outline.sections)}

CONTENT BRIEF:
- Goal: {content_brief.goal}
- Content Angle: {content_brief.content_angle}
- Target Audience: {content_brief.target_audience}

BRAND VOICE:
- Brand: {brand_profile.name} ({brand_profile.one_liner})
- Tone: {brand_profile.tone_rules}
- Unique Angle: {brand_profile.unique_angle}
{banned_block}{knowledge_block}
KEYWORD OPTIMIZATION:
- Main Keyword: {keyword if keyword else 'N/A'}
- Include main keyword 2-4 times naturally (targeting 2% density overall)
{sub_keywords_str}
- Aim for 0.5-1% density for sub-keywords

Write engaging, informative content that:
1. Thoroughly covers all phases mentioned with concrete examples and numbers
2. Uses practical, actionable advice
3. Maintains the brand voice and tone
4. Is scannable with subheadings where helpful
5. References {brand_profile.name} at most once if it fits naturally{'; link it to ' + site_url if site_url else ''}
6. Integrates keywords naturally without stuffing

Return clean HTML using <h2>,<h3>,<p>,<strong>,<ul>,<ol>,<a> tags. No meta-commentary."""
        
        llm = LLMService()
        html_content = await llm.call(
            model=get_settings().extraction_model,
            prompt=prompt,
            response_format="text",
            max_tokens=1200,
            temperature=0.6
        )
        
        # Clean fences + collect
        cleaned_content = clean_markdown_fences(html_content)
        word_count = count_words_in_html(cleaned_content)
        
        return GeneratedSection(
            index=section.index,
            heading=section.heading,
            heading_type=section.heading_type,
            content=cleaned_content,
            word_count=word_count
        )
    
    # Generate all sections in parallel (batches of 3)
    batch_size = 3
    all_sections = []
    
    for i in range(0, len(outline.sections), batch_size):
        batch = outline.sections[i:i + batch_size]
        batch_results = await asyncio.gather(*[
            generate_single_section(section) for section in batch
        ])
        all_sections.extend(batch_results)
    
    # Sort by index to maintain order
    return sorted(all_sections, key=lambda s: s.index)

async def generate_table_of_contents(sections: List[GeneratedSection]) -> str:
    """AI · Table of Contents (Structural — no client fragments)"""
    
    section_data = [
        {"heading": s.heading, "level": s.heading_type}
        for s in sections
    ]
    
    prompt = f"""Generate a table of contents for an article.

SECTIONS:
{json.dumps(section_data, indent=2)}

Create a clean, scannable table of contents that:
1. Uses proper HTML list structure
2. Includes anchor links (#section-1, #section-2, etc.)
3. Shows the content hierarchy clearly
4. Is styled for easy scanning

Return clean HTML with ordered list structure."""
    
    llm = LLMService()
    return await llm.call(
        model=get_settings().extraction_model,
        prompt=prompt,
        response_format="text",
        max_tokens=500,
        temperature=0.3
    )

async def generate_conclusion(
    content_brief: ContentBrief,
    brand_profile: BrandProfile,
    sections: List[GeneratedSection],
    keyword: str = None,
    sub_keywords: List[str] = None
) -> str:
    """AI · Conclusion (Takeaways + CTA)"""
    
    key_takeaways = [s.heading for s in sections]
    sub_keywords = sub_keywords or []
    sub_keywords_str = f"- Sub-keywords to include naturally: {', '.join(sub_keywords[:2])}" if sub_keywords else ""
    
    site_url = brand_profile.site_url or ""
    site_link_rule = f"- Include at least one link to {site_url}" if site_url else ""

    prompt = f"""Write a compelling conclusion for the blog article.

KEY SECTIONS COVERED:
{', '.join(key_takeaways)}

CONTENT BRIEF:
- Goal: {content_brief.goal}
- Target Audience: {content_brief.target_audience}

BRAND CONTEXT:
- Brand: {brand_profile.name}
- Unique Angle: {brand_profile.unique_angle}
- CTAs: {', '.join(brand_profile.ctas)}
{site_link_rule}

KEYWORD OPTIMIZATION:
- Main Keyword: {keyword if keyword else 'N/A'}
- Include main keyword 1-2 times naturally
{sub_keywords_str}

Write a 300-450 word conclusion that:
1. Gives 5-7 concrete, action-oriented key takeaways as a bulleted list
2. Reinforces the main value proposition tying to {brand_profile.unique_angle}
3. Includes a strong, specific CTA from: {', '.join(brand_profile.ctas)}
4. Naturally includes the main keyword 1-2 times
5. Integrates sub-keywords without forcing them

Return clean HTML using only <p>,<strong>,<ul>,<li>,<a> tags."""
    
    llm = LLMService()
    return await llm.call(
        model=get_settings().extraction_model,
        prompt=prompt,
        response_format="text",
        max_tokens=600,
        temperature=0.6
    )

async def generate_faq_section(
    keyword: str,
    sub_keywords: List[str],
    content_brief: ContentBrief,
    brand_profile: BrandProfile,
    sections: List[GeneratedSection] = None
) -> str:
    """Generate FAQ section with 5-7 questions including keyword optimization"""
    
    sections_context = ""
    if sections:
        section_headings = [s.heading for s in sections]
        sections_context = f"- Article sections covered: {', '.join(section_headings)}"
    
    prompt = f"""Generate a comprehensive FAQ section for this blog article.

MAIN TOPIC: {keyword}
SUB-TOPICS/KEYWORDS: {', '.join(sub_keywords[:10])}

CONTENT CONTEXT:
- Goal: {content_brief.goal}
- Target Audience: {content_brief.target_audience}
- Content Angle: {content_brief.content_angle}
{sections_context}

BRAND VOICE:
- Tone: {brand_profile.tone_rules}
- Brand: {brand_profile.name}

REQUIREMENTS:
1. Generate 6-8 frequently asked questions
2. Each question should address real user concerns
3. Include the main keyword "{keyword}" naturally in 2-3 questions
4. Include sub-keywords naturally across different Q&As
5. Each answer should be 100-150 words, informative and actionable
6. Maintain {brand_profile.tone_rules} tone throughout
7. Use schema.org FAQ markup structure

Format as clean HTML with proper FAQ schema markup:
<div itemscope itemtype="https://schema.org/FAQPage">
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">Question here?</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <div itemprop="text">
        <p>Answer here...</p>
      </div>
    </div>
  </div>
  <!-- Repeat for each Q&A -->
</div>

Return the complete FAQ section in HTML with schema markup."""
    
    llm = LLMService()
    return await llm.call(
        model=get_settings().extraction_model,
        prompt=prompt,
        response_format="text",
        max_tokens=2000,
        temperature=0.6
    )

async def generate_brand_value_section(
    keyword: str,
    brand_profile: BrandProfile,
    content_brief: ContentBrief,
    brand_knowledge: str = ""
) -> str:
    """Generate 'How [Brand] helps you in this' section"""

    proof_points = getattr(brand_profile, "proof_points", None) or []
    proof_line = f"- Proof Points: {', '.join(proof_points)}\n" if proof_points else ""
    knowledge_block = _brand_knowledge_block(brand_knowledge)
    prompt = f"""Write a compelling section explaining how {brand_profile.name} specifically helps with {keyword}.

BRAND CONTEXT:
- Brand: {brand_profile.name}
- One-liner: {brand_profile.one_liner}
- Industry: {brand_profile.industry or 'General'}
- Unique Angle: {brand_profile.unique_angle}
- Tone: {brand_profile.tone_rules}
- CTAs: {', '.join(brand_profile.ctas)}
{proof_line}{knowledge_block}
CONTENT CONTEXT:
- Topic: {keyword}
- Goal: {content_brief.goal}
- Target Audience: {content_brief.target_audience}

Write a section that:
1. Has the heading "How {brand_profile.name} Helps You With {keyword.title()}"
2. Explains specific ways the brand addresses the topic/challenges
3. Highlights unique features, services, or advantages
4. Shows practical benefits for the target audience
5. Maintains the brand's tone and voice
6. Includes a subtle call-to-action
7. Is 200-300 words

Return clean HTML with proper heading and paragraph structure."""
    
    llm = LLMService()
    return await llm.call(
        model=get_settings().extraction_model,
        prompt=prompt,
        response_format="text",
        max_tokens=600,
        temperature=0.6
    )

# ---------------------------------------------------------------------------
# Link Strategy and Backlinking System
# ---------------------------------------------------------------------------

def prepare_link_strategy(
    brand_profile: BrandProfile,
    serp_data: SerpAnalysisData,
    target_keyword: str
) -> LinkStrategy:
    """Prepare comprehensive linking strategy from brand profile and SERP data"""
    
    # Internal links from brand profile
    internal_links = []
    for link_data in brand_profile.internal_links:
        if isinstance(link_data, dict) and link_data.get("url"):
            internal_links.append(LinkData(
                url=link_data.get("url", ""),
                anchor_text=link_data.get("anchor_text", ""),
                link_type="internal",
                description=link_data.get("description", ""),
                rel_attributes="",  # Internal links don't need rel attributes
                priority=link_data.get("priority", "medium"),
                keywords=link_data.get("keywords", []),
                target_blank=False  # Keep users on site
            ))
    
    # Source citations from SERP competitor data
    source_citations = []
    
    # Extract competitor URLs as potential sources
    if hasattr(serp_data, 'serp_metadata') and serp_data.serp_metadata:
        metadata = serp_data.serp_metadata
        if isinstance(metadata, dict) and 'top_competitors' in metadata:
            for i, comp in enumerate(metadata['top_competitors'][:3]):  # Top 3 competitors
                if isinstance(comp, dict) and comp.get('url'):
                    source_citations.append(SourceCitation(
                        title=comp.get('title', f'Industry Analysis #{i+1}'),
                        url=comp['url'],
                        publication=comp.get('domain', 'Industry Source'),
                        relevance_score=max(0.1, 1.0 - (i * 0.2)),  # Decreasing relevance by rank
                        trust_level="medium"
                    ))
    
    # Product/service links from brand CTAs and website
    product_links = []
    if brand_profile.site_url:
        # Create product links based on CTAs
        for cta in brand_profile.ctas[:3]:  # Max 3 CTAs
            if cta and len(cta.strip()) > 0:
                product_links.append(LinkData(
                    url=brand_profile.site_url,
                    anchor_text=cta,
                    link_type="product",
                    description=f"Link to {brand_profile.name} - {cta}",
                    rel_attributes="",  # Own product links
                    priority="high",
                    keywords=[target_keyword.lower()],
                    target_blank=False
                ))
    
    # External references for credibility (industry authorities)
    external_references = []
    authority_sources = get_authority_sources_by_topic(target_keyword)
    for source in authority_sources:
        external_references.append(LinkData(
            url=source['url'],
            anchor_text=source['anchor_text'],
            link_type="external",
            description=source['description'],
            rel_attributes="noopener nofollow",  # External links
            priority="medium",
            keywords=source.get('keywords', []),
            target_blank=True
        ))
    
    return LinkStrategy(
        internal_links=internal_links,
        source_citations=source_citations,
        product_links=product_links,
        external_references=external_references,
        max_links_per_section=3,
        require_disclosures=True
    )

def get_authority_sources_by_topic(keyword: str) -> List[dict]:
    """Get authoritative sources based on keyword topic for credible external links"""
    
    keyword_lower = keyword.lower()
    sources = []
    
    # Tech/AI related keywords
    if any(term in keyword_lower for term in ['ai', 'artificial intelligence', 'machine learning', 'technology', 'software', 'automation']):
        sources.extend([
            {
                "url": "https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai",
                "anchor_text": "McKinsey Global Institute AI research",
                "description": "Authoritative AI industry research",
                "keywords": ["ai", "artificial intelligence", "research"]
            },
            {
                "url": "https://www.gartner.com/en/information-technology/glossary/artificial-intelligence",
                "anchor_text": "Gartner's AI insights",
                "description": "Industry standard AI analysis",
                "keywords": ["ai", "technology", "industry analysis"]
            }
        ])
    
    # Marketing related keywords  
    if any(term in keyword_lower for term in ['marketing', 'digital marketing', 'seo', 'content marketing', 'social media']):
        sources.extend([
            {
                "url": "https://blog.hubspot.com/marketing",
                "anchor_text": "HubSpot Marketing insights",
                "description": "Leading marketing research and trends",
                "keywords": ["marketing", "digital marketing", "trends"]
            },
            {
                "url": "https://moz.com/beginners-guide-to-seo",
                "anchor_text": "Moz SEO research",
                "description": "Comprehensive SEO best practices",
                "keywords": ["seo", "search optimization", "guide"]
            }
        ])
    
    # Business/productivity keywords
    if any(term in keyword_lower for term in ['business', 'productivity', 'workflow', 'efficiency', 'strategy']):
        sources.extend([
            {
                "url": "https://hbr.org/topic/productivity",
                "anchor_text": "Harvard Business Review productivity research",
                "description": "Academic business and productivity insights",
                "keywords": ["business", "productivity", "research"]
            },
            {
                "url": "https://www.mckinsey.com/business-functions/operations/our-insights",
                "anchor_text": "McKinsey Operations insights",
                "description": "Business operations and efficiency research",
                "keywords": ["business", "operations", "efficiency"]
            }
        ])
    
    # Financial/economics keywords
    if any(term in keyword_lower for term in ['finance', 'investment', 'economics', 'cost', 'roi', 'revenue']):
        sources.extend([
            {
                "url": "https://www.investopedia.com",
                "anchor_text": "Investopedia financial analysis",
                "description": "Comprehensive financial education resource",
                "keywords": ["finance", "investment", "analysis"]
            }
        ])
    
    # Return top 2-3 most relevant sources to avoid over-linking
    return sources[:3]

async def insert_contextual_links(
    content: str,
    link_strategy: LinkStrategy,
    section_index: int = 0,
    content_type: str = "body"
) -> tuple[str, List[LinkData]]:
    """AI-powered contextual link insertion into content"""
    
    # Determine which links to use for this section
    available_links = []
    
    if content_type == "introduction":
        # Introduction: 1 authority link, 1 internal link
        available_links.extend(link_strategy.external_references[:1])
        available_links.extend(link_strategy.internal_links[:1])
    elif content_type == "body":
        # Body sections: Mix of internal, external, and sources
        available_links.extend(link_strategy.internal_links[section_index:section_index+1])
        available_links.extend(link_strategy.external_references[section_index:section_index+1])
        available_links.extend(link_strategy.source_citations[section_index:section_index+1])
    elif content_type == "conclusion":
        # Conclusion: Product links + 1 authority
        available_links.extend(link_strategy.product_links[:2])
        available_links.extend(link_strategy.external_references[:1])
    elif content_type == "brand_value":
        # Brand value section: All product links
        available_links.extend(link_strategy.product_links)
    
    if not available_links:
        return content, []
    
    # Use AI to insert links contextually
    links_data = []
    for link in available_links[:link_strategy.max_links_per_section]:
        if isinstance(link, SourceCitation):
            link_data = LinkData(
                url=link.url,
                anchor_text=link.title,
                link_type="source",
                rel_attributes="noopener nofollow",
                target_blank=True
            )
        else:
            link_data = link
        
        links_data.append(link_data)
    
    # AI prompt for contextual link insertion
    prompt = f"""Insert {len(links_data)} contextually relevant links into this content.

CONTENT TO ENHANCE:
{content}

LINKS TO INSERT:
{json.dumps([{
    "url": link.url,
    "anchor_text": link.anchor_text,
    "type": link.link_type
} for link in links_data], indent=2)}

INSTRUCTIONS:
1. Find natural places in the text where these links would add value
2. Modify existing sentences or add new sentences that naturally incorporate the links
3. Use the provided anchor text but adapt it to fit grammatically
4. Don't force links - only insert where they enhance the content
5. Maintain the original tone and flow
6. Insert links as HTML: <a href="url" rel="attributes" target="_blank">anchor text</a>

Return the enhanced content with links naturally integrated."""

    try:
        llm = LLMService()
        enhanced_content = await llm.call(
            model=get_settings().extraction_model,
            prompt=prompt,
            response_format="text",
            max_tokens=2000,
            temperature=0.4
        )
        
        return enhanced_content, links_data
        
    except Exception as e:
        logger.warning(f"Link insertion failed: {e}, returning original content")
        return content, []

def format_link_html(link: LinkData) -> str:
    """Format a link as proper HTML with all attributes"""
    
    rel_attr = f' rel="{link.rel_attributes}"' if link.rel_attributes else ""
    target_attr = ' target="_blank"' if link.target_blank else ""
    
    return f'<a href="{link.url}"{rel_attr}{target_attr}>{link.anchor_text}</a>'

def generate_link_disclosures(links: List[LinkData]) -> List[str]:
    """Generate required disclosure text for affiliate/sponsored links"""
    
    disclosures = []
    has_affiliate = any(link.link_type == "affiliate" for link in links)
    has_sponsored = any("sponsored" in link.rel_attributes for link in links)
    
    if has_affiliate:
        disclosures.append("*This post contains affiliate links. We may earn a commission at no extra cost to you.")
    
    if has_sponsored:
        disclosures.append("*Some links in this content are sponsored partnerships.")
    
    return disclosures

# ---------------------------------------------------------------------------
# Link Validation and Compliance
# ---------------------------------------------------------------------------

async def validate_links(links: List[LinkData]) -> List[LinkData]:
    """Validate links for accessibility and compliance"""
    
    validated_links = []
    
    for link in links:
        try:
            # Basic URL validation
            if not link.url or not link.url.startswith(('http://', 'https://')):
                logger.warning(f"Invalid URL format: {link.url}")
                continue
            
            # Check for required rel attributes based on link type
            if link.link_type == "external" and "nofollow" not in link.rel_attributes:
                link.rel_attributes = "noopener nofollow"
            elif link.link_type == "affiliate" and "sponsored" not in link.rel_attributes:
                link.rel_attributes = "sponsored noopener"
            
            # Ensure anchor text is not empty
            if not link.anchor_text or len(link.anchor_text.strip()) < 2:
                logger.warning(f"Invalid anchor text for {link.url}")
                continue
            
            validated_links.append(link)
            
        except Exception as e:
            logger.warning(f"Link validation failed for {link.url}: {e}")
            continue
    
    logger.info(f"Link validation: {len(validated_links)}/{len(links)} links passed validation")
    return validated_links

def validate_link_density(content: str, max_density: float = 0.03) -> bool:
    """Check if link density is within acceptable range (max 3% recommended)"""
    
    import re
    
    # Count total words
    text_only = re.sub(r'<[^>]+>', ' ', content)
    total_words = len(text_only.split())
    
    # Count links
    link_count = len(re.findall(r'<a\s+[^>]*href', content, re.IGNORECASE))
    
    if total_words == 0:
        return True
    
    density = link_count / total_words
    is_valid = density <= max_density
    
    if not is_valid:
        logger.warning(f"Link density too high: {density:.3f} ({link_count} links in {total_words} words)")
    
    return is_valid

def merge_content_by_position(
    introduction: str,
    table_of_contents: str,
    body_sections: List[GeneratedSection],
    conclusion: str,
    brand_value_section: str = None,
    faq_section: str = None
) -> AssembledContent:
    """Merge (intro · TOC · conclusion) by position"""
    
    # Sort sections by index
    sorted_sections = sorted(body_sections, key=lambda s: s.index)
    
    # Build section HTML
    sections_html = []
    for section in sorted_sections:
        section_html = f"""
        <{section.heading_type} id="section-{section.index + 1}">{section.heading}</{section.heading_type}>
        {section.content}
        """
        sections_html.append(section_html.strip())
    
    body_html = "\n\n".join(sections_html)
    
    # Add brand value and FAQ to word count if present
    brand_value_word_count = count_words_in_html(brand_value_section) if brand_value_section else 0
    faq_word_count = count_words_in_html(faq_section) if faq_section else 0
    
    return AssembledContent(
        introduction=introduction,
        table_of_contents=table_of_contents,
        body=body_html,
        conclusion=conclusion,
        brand_value_section=brand_value_section,
        faq_section=faq_section,
        total_word_count=sum(s.word_count for s in body_sections) + brand_value_word_count + faq_word_count
    )

def assemble_article_html(assembled_content: AssembledContent, meta: MetaAndOutline) -> FinalArticle:
    """Assemble article HTML + word count - Sort sections by index → concatenate inside <article>"""
    
    brand_value_html = f"""
        <div class="brand-value-section">
            {assembled_content.brand_value_section}
        </div>""" if assembled_content.brand_value_section else ""
    
    faq_html = f"""
        <div class="faq-section">
            <h2>Frequently Asked Questions</h2>
            {assembled_content.faq_section}
        </div>""" if assembled_content.faq_section else ""
    
    full_html = f"""
    <article class="generated-content">
        <header>
            <h1>{meta.h1}</h1>
        </header>
        
        <div class="introduction">
            {assembled_content.introduction}
        </div>
        
        <div class="table-of-contents">
            {assembled_content.table_of_contents}
        </div>
        
        <div class="article-body">
            {assembled_content.body}
        </div>
        
        <div class="conclusion">
            {assembled_content.conclusion}
        </div>
        {brand_value_html}
        {faq_html}
    </article>
    """.strip()
    
    return FinalArticle(
        meta_title=meta.meta_title,
        meta_description=meta.meta_description,
        slug=meta.slug,
        html_content=full_html,
        word_count=assembled_content.total_word_count
    )

def assemble_article_html_with_links(
    assembled_content: AssembledContent,
    meta: MetaAndOutline,
    links_added: List[LinkData],
    sources_cited: List[SourceCitation],
    link_disclosures: List[str]
) -> FinalArticle:
    """Assemble article HTML with link tracking and disclosures"""
    
    brand_value_html = f"""
        <div class="brand-value-section">
            {assembled_content.brand_value_section}
        </div>""" if assembled_content.brand_value_section else ""
    
    faq_html = f"""
        <div class="faq-section">
            <h2>Frequently Asked Questions</h2>
            {assembled_content.faq_section}
        </div>""" if assembled_content.faq_section else ""
    
    # Add disclosure section if needed
    disclosure_html = ""
    if link_disclosures:
        disclosure_html = f"""
        <div class="link-disclosures">
            <hr>
            {'<br>'.join(link_disclosures)}
        </div>"""
    
    full_html = f"""
    <article class="generated-content">
        <header>
            <h1>{meta.h1}</h1>
        </header>
        
        <div class="introduction">
            {assembled_content.introduction}
        </div>
        
        <div class="table-of-contents">
            {assembled_content.table_of_contents}
        </div>
        
        <div class="article-body">
            {assembled_content.body}
        </div>
        
        <div class="conclusion">
            {assembled_content.conclusion}
        </div>
        {brand_value_html}
        {faq_html}
        {disclosure_html}
    </article>
    """.strip()
    
    return FinalArticle(
        meta_title=meta.meta_title,
        meta_description=meta.meta_description,
        slug=meta.slug,
        html_content=full_html,
        word_count=assembled_content.total_word_count,
        links_added=links_added,
        sources_cited=sources_cited,
        link_disclosures=link_disclosures
    )

async def save_content_draft(
    job: Job,
    article: FinalArticle,
    db: Session
) -> BlogDraft:
    """Save to blog_drafts table · Stage = Draft"""

    # When triggered through the full pipeline chain from the calendar,
    # blog_job_id is the original BlogJob.id (same as the keyword_research job_id).
    # Fall back to job.id for standalone content generation runs.
    payload = job.input_payload or {}
    blog_job_id = payload.get("blog_job_id", job.id)

    # Update or create blog job for UI integration
    blog_job = db.query(BlogJob).filter(BlogJob.id == blog_job_id).first()
    if not blog_job:
        blog_job = BlogJob(
            id=blog_job_id,
            org_id=job.org_id,
            brand_id=job.brand_id,
            created_by=payload.get("created_by", "system"),
            keyword=payload.get("keyword", "Generated Content"),
            status="WRITING",
        )
        db.add(blog_job)

    # Compute real scores from the generated content
    keyword = payload.get("keyword", "")
    seo_score = _calc_seo_score(article.html_content, keyword, article.meta_description)
    aeo_score = _calc_aeo_score_from_html(article.html_content)
    virality_score = _calc_virality_score(article.word_count, seo_score, aeo_score)

    # Create or update draft — linked to blog_job_id so BlogSchedule can find it
    existing_draft = db.query(BlogDraft).filter(BlogDraft.job_id == blog_job_id).first()
    if existing_draft:
        existing_draft.title = article.meta_title
        existing_draft.meta_description = article.meta_description
        existing_draft.html_content = article.html_content
        existing_draft.word_count = article.word_count
        existing_draft.seo_score = seo_score
        existing_draft.aeo_score = aeo_score
        existing_draft.virality_score = virality_score
        draft = existing_draft
    else:
        draft = BlogDraft(
            job_id=blog_job_id,
            title=article.meta_title,
            meta_description=article.meta_description,
            html_content=article.html_content,
            word_count=article.word_count,
            seo_score=seo_score,
            aeo_score=aeo_score,
            virality_score=virality_score,
            approved=False,
        )
        db.add(draft)
    
    # Update job stage
    job.stage = JOB_STAGE_DRAFT
    job.status = "PROCESSING"  # Continue to image generation
    
    db.commit()
    return draft

# Utility functions
def safe_json_parse(raw_json: str) -> dict:
    """Parse JSON from an LLM response, tolerating markdown fences and prose.

    Tries, in order: a direct parse, a fenced ```json … ``` block, and the
    largest ``{ … }`` span (which survives leading/trailing prose or a partial
    fence). Logs the FULL raw payload on failure so a truncated response (hit
    max_tokens) is distinguishable from prose-wrapping when diagnosing.
    """
    if not isinstance(raw_json, str):
        return {}

    cleaned = raw_json.strip()
    candidates = [cleaned]

    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence:
        candidates.append(fence.group(1).strip())

    first, last = cleaned.find("{"), cleaned.rfind("}")
    if first != -1 and last > first:
        candidates.append(cleaned[first:last + 1])

    for candidate in candidates:
        try:
            result = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(result, dict):
            return result

    logger.warning("Failed to parse JSON from LLM response (%d chars): %s", len(raw_json), raw_json)
    return {}

def clean_markdown_fences(content: str) -> str:
    """Remove markdown code fences from content"""
    if content.startswith("```"):
        lines = content.split('\n')
        if len(lines) > 2:
            return '\n'.join(lines[1:-1])
    return content

def count_words_in_html(html_content: str) -> int:
    """Count words in HTML content (rough estimate)"""
    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # Count words
    words = text.split()
    return len([w for w in words if w.strip()])

def calculate_keyword_density(content: str, keyword: str) -> float:
    """Calculate keyword density as a percentage"""
    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', content).lower()
    # Count total words
    words = text.split()
    total_words = len([w for w in words if w.strip()])
    
    if total_words == 0:
        return 0.0
    
    # Count keyword occurrences (case-insensitive)
    keyword_lower = keyword.lower()
    keyword_count = text.count(keyword_lower)
    
    # Calculate density
    density = (keyword_count / total_words) * 100
    return round(density, 2)

def analyze_content_seo_metrics(content: str, main_keyword: str, sub_keywords: List[str]) -> Dict[str, any]:
    """Analyze SEO metrics for the generated content"""
    metrics = {
        "total_words": count_words_in_html(content),
        "main_keyword": {
            "keyword": main_keyword,
            "density": calculate_keyword_density(content, main_keyword),
            "target": 2.0,
            "status": "optimized"
        },
        "sub_keywords": []
    }
    
    # Check if main keyword density is within target range
    if metrics["main_keyword"]["density"] < 1.5:
        metrics["main_keyword"]["status"] = "under-optimized"
    elif metrics["main_keyword"]["density"] > 2.5:
        metrics["main_keyword"]["status"] = "over-optimized"
    
    # Analyze sub-keywords
    for sub_kw in sub_keywords[:10]:  # Top 10 sub-keywords
        density = calculate_keyword_density(content, sub_kw)
        status = "optimized"
        if density < 0.3:
            status = "under-optimized"
        elif density > 1.5:
            status = "over-optimized"
            
        metrics["sub_keywords"].append({
            "keyword": sub_kw,
            "density": density,
            "target": "0.5-1.0",
            "status": status
        })
    
    return metrics

# Image generation functions
async def generate_image_prompt(
    article: FinalArticle,
    brand_profile: BrandProfile
) -> str:
    """AI · reads article + brand profile → image prompt"""
    
    prompt = f"""Create a featured blog image prompt for {brand_profile.name} ({brand_profile.one_liner}).
Article Meta Title: {article.meta_title}

Return JSON with EXACTLY these keys:
- Object: main foreground element (draw from: {brand_profile.image_subject_hints or 'professional clean imagery'})
- Background: scene/environment that fits the topic
- Subject: what the image communicates conceptually
- Emphasisers: palette {brand_profile.image_palette or 'modern color scheme'}; clean typography
- Camera: suggested shot type (wide / close-up / overhead / etc.)
- Complete_Prompt: cohesive final prompt under 1400 chars; NO identifiable real people; avoid stock clichés

Return JSON only."""

    llm = LLMService()
    return await llm.call(
        model="anthropic/claude-haiku-4-5-20251001",
        prompt=prompt,
        response_format="json",
        max_tokens=400,
        temperature=0.7
    )

async def store_image_in_bucket(image_url: str, bucket_name: str, file_name: str) -> str:
    """Store image from URL to cloud storage bucket"""
    # For now, return the original URL
    # In production, you would download and upload to your storage
    logger.info(f"Image storage: {image_url} -> {bucket_name}/{file_name}")
    return image_url

async def generate_featured_image(
    article: FinalArticle,
    brand_profile: BrandProfile,
    job: Job,
    db: Session
) -> Optional[str]:
    """Complete image generation workflow with defensive fallbacks"""
    
    try:
        logger.info(f"Starting image generation for job {job.id}")
        
        # Generate image prompt — returns JSON per spec AI #9
        image_prompt_raw = await generate_image_prompt(article, brand_profile)
        image_prompt_data = safe_json_parse(image_prompt_raw) if isinstance(image_prompt_raw, str) else image_prompt_raw
        if isinstance(image_prompt_data, dict):
            complete_prompt = image_prompt_data.get("Complete_Prompt") or image_prompt_data.get("complete_prompt", "")
        else:
            complete_prompt = str(image_prompt_raw)
        logger.info(f"Generated image prompt (Complete_Prompt): {complete_prompt[:120]}...")

        # Generate with Leonardo
        leonardo = LeonardoService()
        raw_image_url = await leonardo.generate_image(complete_prompt)
        logger.info(f"Leonardo generated image: {raw_image_url}")
        
        # Composite with Placid if template configured
        final_image_url = raw_image_url
        if brand_profile.placid_template_id:
            try:
                placid = PlacidService()
                final_image_url = await placid.composite_branded_template(
                    brand_profile.placid_template_id,
                    raw_image_url,
                    article.meta_title,
                    brand_profile
                )
                logger.info(f"Placid composed image: {final_image_url}")
            except Exception as e:
                logger.warning(f"Placid composition failed, using raw image: {e}")
                final_image_url = raw_image_url
        
        # Store in brand's bucket
        stored_url = await store_image_in_bucket(
            final_image_url,
            brand_profile.image_output_bucket or "default-images",
            f"{job.id}-featured.jpg"
        )
        
        logger.info(f"Image generation completed for job {job.id}: {stored_url}")
        return stored_url
        
    except Exception as e:
        logger.error(f"Image generation failed for job {job.id}: {e}")
        # Defensive fallback - log & keep article usable
        return None

# Main Pipeline 3 orchestrator
async def run_content_generation_pipeline(db: Session, job_id: str) -> None:
    """Main orchestrator - handles complete Pipeline 3 flow"""
    
    job = db.query(Job).filter(Job.id == job_id).one_or_none()
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    try:
        logger.info(f"Starting content generation pipeline for job {job_id}")
        
        # Check if this job was triggered from a SERP analysis job
        serp_job_id = job.input_payload.get("serp_analysis_job_id") if job.input_payload else None
        
        # 01. Load SERP analysis
        serp_data = await load_serp_analysis(job_id, job.brand_id, db, serp_job_id)
        logger.info(f"Loaded SERP data: {len(serp_data.keywords)} keywords, {len(serp_data.competitor_gaps)} gaps")
        
        # 02. Get brand profile
        brand_profile = db.query(BrandProfile).filter(
            BrandProfile.brand_id == job.brand_id
        ).first()
        
        if not brand_profile:
            raise ValueError(f"Brand profile not found for brand {job.brand_id}")
        
        target_keyword = job.input_payload.get("keyword", "content topic")
        logger.info(f"Target keyword: {target_keyword}")
        
        # Extract sub-keywords from SERP data for distribution
        # Keywords are now tuples: (keyword, score, volume, difficulty)
        sub_keywords = [kw[0] for kw in serp_data.keywords[:15] if kw[0] != target_keyword]  # Top 15 sub-keywords
        logger.info(f"Extracted {len(sub_keywords)} sub-keywords for optimization")

        # 02b. Retrieve brand knowledge (RAG) ONCE per article to ground generation.
        # Additive: empty string when keys/index/chunks are unavailable.
        from app.services.retrieval import retrieve_brand_grounding
        brand_knowledge = await retrieve_brand_grounding(job.brand_id, target_keyword, db, top_k=6)
        logger.info(f"Brand grounding retrieved: {len(brand_knowledge)} chars")

        # Log keyword intelligence if available
        if serp_data.keywords:
            top_kw = serp_data.keywords[0]
            if len(top_kw) > 2 and top_kw[2]:  # Has volume data
                logger.info(f"Top keyword '{top_kw[0]}' - Volume: {top_kw[2]}, Difficulty: {top_kw[3]}")
        
        # 03. Generate content brief
        logger.info("Generating content brief...")
        content_brief = await generate_content_brief(serp_data, brand_profile, target_keyword, brand_knowledge)
        logger.info(f"Content brief generated: {content_brief.goal}")
        
        # 04. Generate meta & outline
        logger.info("Generating meta and outline...")
        meta_outline = await generate_meta_and_outline(content_brief, brand_profile, target_keyword)
        logger.info(f"Meta and outline generated: {meta_outline.meta_title}")
        
        # 05. Parse & validate outline. Supply fallback headings (from the brief,
        # then SERP gaps/keywords) so a truncated/empty LLM outline degrades to a
        # usable structure instead of crashing the whole article.
        fallback_headings: list[str] = []
        for s in (content_brief.sections or []):
            if isinstance(s, dict):
                fallback_headings.append(s.get("heading") or s.get("title") or s.get("name") or "")
            elif isinstance(s, str):
                fallback_headings.append(s)
        fallback_headings += list(serp_data.competitor_gaps or [])[:6]
        validated_outline = parse_and_validate_outline(meta_outline.model_dump(), fallback_headings)
        logger.info(f"Outline validated: {len(validated_outline.sections)} sections")
        
        # 06. Prepare link strategy
        logger.info("Preparing link strategy...")
        link_strategy = prepare_link_strategy(brand_profile, serp_data, target_keyword)
        logger.info(f"Link strategy prepared: {len(link_strategy.internal_links)} internal, {len(link_strategy.external_references)} external, {len(link_strategy.product_links)} product links")

        # 07. Parallel content generation with keyword optimization
        logger.info("Starting parallel content generation with keyword optimization...")
        intro_task = generate_introduction(content_brief, brand_profile, target_keyword, sub_keywords)
        body_task = generate_body_sections(validated_outline, content_brief, brand_profile, target_keyword, sub_keywords, brand_knowledge)
        
        introduction, body_sections = await asyncio.gather(intro_task, body_task)
        logger.info(f"Generated introduction and {len(body_sections)} body sections with keyword optimization")
        
        # 07. Generate TOC, conclusion, brand value section, and FAQ
        logger.info("Generating TOC, conclusion, brand value section, and FAQ...")
        toc_task = generate_table_of_contents(body_sections)
        conclusion_task = generate_conclusion(content_brief, brand_profile, body_sections, target_keyword, sub_keywords)
        brand_value_task = generate_brand_value_section(target_keyword, brand_profile, content_brief, brand_knowledge)
        faq_task = generate_faq_section(target_keyword, sub_keywords, content_brief, brand_profile, body_sections)
        
        toc, conclusion, brand_value_section, faq_section = await asyncio.gather(toc_task, conclusion_task, brand_value_task, faq_task)
        logger.info("TOC, conclusion, brand value section, and FAQ generated")
        
        # 08. Insert contextual links into content
        logger.info("Inserting contextual links...")
        all_links_added = []
        all_sources_cited = []
        
        # Insert links in introduction
        enhanced_intro, intro_links = await insert_contextual_links(
            introduction, link_strategy, 0, "introduction"
        )
        all_links_added.extend(intro_links)
        
        # Insert links in body sections
        enhanced_body_sections = []
        for i, section in enumerate(body_sections):
            enhanced_content, section_links = await insert_contextual_links(
                section.content, link_strategy, i, "body"
            )
            enhanced_section = GeneratedSection(
                index=section.index,
                heading=section.heading,
                heading_type=section.heading_type,
                content=enhanced_content,
                word_count=count_words_in_html(enhanced_content)
            )
            enhanced_body_sections.append(enhanced_section)
            all_links_added.extend(section_links)
        
        # Insert links in conclusion
        enhanced_conclusion, conclusion_links = await insert_contextual_links(
            conclusion, link_strategy, 0, "conclusion"
        )
        all_links_added.extend(conclusion_links)
        
        # Insert links in brand value section
        enhanced_brand_value, brand_value_links = await insert_contextual_links(
            brand_value_section, link_strategy, 0, "brand_value"
        )
        all_links_added.extend(brand_value_links)
        
        # Add source citations to sources_cited list
        all_sources_cited.extend(link_strategy.source_citations)
        
        logger.info(f"Links inserted: {len(all_links_added)} links across all sections")
        
        # Validate all links
        all_links_added = await validate_links(all_links_added)
        logger.info(f"Link validation completed: {len(all_links_added)} valid links")
        
        # 09. Merge enhanced content with brand value section and FAQ
        assembled_content = merge_content_by_position(
            enhanced_intro, toc, enhanced_body_sections, enhanced_conclusion, enhanced_brand_value, faq_section
        )
        logger.info(f"Enhanced content assembled: {assembled_content.total_word_count} words")
        
        # 10. Generate link disclosures and assemble final article
        link_disclosures = generate_link_disclosures(all_links_added)
        logger.info(f"Generated {len(link_disclosures)} link disclosures")
        
        final_article = assemble_article_html_with_links(
            assembled_content, meta_outline, all_links_added, all_sources_cited, link_disclosures
        )
        logger.info(f"Final article assembled with links: {final_article.meta_title}")
        
        # Analyze SEO metrics for the generated content
        seo_metrics = analyze_content_seo_metrics(final_article.html_content, target_keyword, sub_keywords)
        logger.info(f"SEO Metrics - Main keyword '{target_keyword}' density: {seo_metrics['main_keyword']['density']}% (target: 2%)")
        logger.info(f"SEO Metrics - Sub-keywords analyzed: {len(seo_metrics['sub_keywords'])}")
        
        # 10. Save draft
        draft = await save_content_draft(job, final_article, db)
        logger.info(f"Draft saved with ID: {draft.id}")
        
        # 11. Generate featured image (non-blocking)
        logger.info("Starting image generation...")
        image_url = await generate_featured_image(final_article, brand_profile, job, db)
        
        if image_url:
            draft.featured_image_url = image_url
            logger.info(f"Featured image generated: {image_url}")
        else:
            logger.warning("Image generation failed, article will be published without featured image")
        
        job.stage = JOB_STAGE_COMPLETE
        job.status = "SUCCEEDED"

        # Resolve the correct BlogJob: use blog_job_id from payload when available
        # (set when triggered via full pipeline chain from the calendar).
        resolved_blog_job_id = (job.input_payload or {}).get("blog_job_id", job_id)
        blog_job = db.query(BlogJob).filter(BlogJob.id == resolved_blog_job_id).first()
        if blog_job:
            blog_job.status = "PENDING_REVIEW"

        db.commit()
        
        logger.info(f"Content generation completed successfully for job {job_id}")
        
    except Exception as e:
        logger.exception(f"Content generation failed for job {job_id}")
        job.status = "FAILED"
        job.error_message = str(e)
        db.commit()
        raise