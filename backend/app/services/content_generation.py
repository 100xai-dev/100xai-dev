# app/services/content_generation.py
import asyncio
import json
import logging
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

logger = logging.getLogger(__name__)

# Job stage constants for Pipeline 3
JOB_STAGE_CONTENT = "CONTENT"
JOB_STAGE_DRAFT = "DRAFT"
JOB_STAGE_IMAGE = "IMAGE"
JOB_STAGE_COMPLETE = "COMPLETE"

# Content generation data models
class SerpAnalysisData(BaseModel):
    keywords: List[tuple[str, Optional[float]]]
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
    total_word_count: int

class FinalArticle(BaseModel):
    meta_title: str
    meta_description: str
    slug: str
    html_content: str
    word_count: int

# Core content generation functions
async def load_serp_analysis(job_id: str, brand_id: str, db: Session) -> SerpAnalysisData:
    """Load + aggregate SERP analysis from Pipeline 2"""
    serp_analyses = db.query(SerpAnalysis).filter(
        SerpAnalysis.brand_id == brand_id,
        SerpAnalysis.job_id == job_id  # Link to Pipeline 2 job
    ).all()
    
    competitor_analyses = []
    for serp in serp_analyses:
        competitors = db.query(CompetitorAnalysis).filter(
            CompetitorAnalysis.serp_analysis_id == serp.id
        ).all()
        competitor_analyses.extend(competitors)
    
    return SerpAnalysisData(
        keywords=[(s.keyword_text, s.content_gap_score) for s in serp_analyses],
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
        if comp.competitive_advantages:
            if isinstance(comp.competitive_advantages, list):
                advantages.extend(comp.competitive_advantages)
            elif isinstance(comp.competitive_advantages, str):
                advantages.append(comp.competitive_advantages)
    return advantages[:5]  # Top 5 advantages

def compile_serp_metadata(serp_analyses: List[SerpAnalysis]) -> Dict:
    """Compile SERP metadata for content generation"""
    return {
        "avg_content_score": sum(s.content_gap_score or 0 for s in serp_analyses) / max(len(serp_analyses), 1),
        "total_keywords": len(serp_analyses),
        "analyzed_urls": [s.target_url for s in serp_analyses if s.target_url],
        "analysis_date": max(s.created_at for s in serp_analyses) if serp_analyses else None
    }

async def generate_content_brief(
    serp_data: SerpAnalysisData,
    brand_profile: BrandProfile,
    target_keyword: str
) -> ContentBrief:
    """AI · reads brand profile + serp data → content brief"""
    
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

Generate a content brief with:
1. Content goal and type
2. Target audience
3. Search intent
4. Target word count (1500-3000)
5. Unique content angle
6. Call-to-action suggestions
7. Article outline with sections

Return as JSON with keys: goal, type, audience, intent, word_count, angle, ctas, sections"""
    
    llm = LLMService()
    raw = await llm.call(
        model=get_settings().extraction_model,
        prompt=prompt,
        response_format="json",
        max_tokens=2000,
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

Return as JSON with keys: slug, meta_title, meta_description, h1, sections"""
    
    llm = LLMService()
    raw = await llm.call(
        model="anthropic/claude-haiku-4-5-20251001",  # Faster model for structured output
        prompt=prompt,
        response_format="json",
        max_tokens=1500,
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

def parse_and_validate_outline(outline_data: dict) -> ValidatedOutline:
    """Parse + validate outline - Safe JSON parse; assert sections non-empty"""
    
    if not outline_data.get("sections") or len(outline_data["sections"]) == 0:
        raise ValueError("Outline must contain at least one section")
    
    validated_sections = []
    for i, section in enumerate(outline_data["sections"]):
        if not section.get("heading"):
            raise ValueError(f"Section {i} missing heading")
        
        validated_sections.append(ValidatedSection(
            index=i,
            heading=section["heading"],
            heading_type=section.get("heading_type", "h2"),
            phases=section.get("phases", ["Introduce topic", "Provide details", "Conclude"]),
            estimated_words=section.get("estimated_words", 300)
        ))
    
    return ValidatedOutline(sections=validated_sections)

async def generate_introduction(
    content_brief: ContentBrief,
    brand_profile: BrandProfile,
    keyword: str
) -> str:
    """Track 1 · intro - AI generates introduction (300–500w HTML)"""
    
    prompt = f"""Write an engaging introduction for a blog article.

CONTENT BRIEF:
- Goal: {content_brief.goal}
- Content Angle: {content_brief.content_angle}
- Target Audience: {content_brief.target_audience}

BRAND VOICE:
- Tone: {brand_profile.tone_rules}
- Unique Angle: {brand_profile.unique_angle}

KEYWORD: {keyword}

Write a 300-500 word introduction that:
1. Hooks the reader immediately
2. Introduces the topic naturally with the keyword
3. Sets expectations for what they'll learn
4. Matches the brand voice and tone
5. Creates curiosity to read more

Return clean HTML (paragraphs only, no heading tags)."""
    
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
    brand_profile: BrandProfile
) -> List[GeneratedSection]:
    """Track 2 · body - Split sections → Loop per section"""
    
    async def generate_single_section(section: ValidatedSection) -> GeneratedSection:
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
- Tone: {brand_profile.tone_rules}
- Unique Angle: {brand_profile.unique_angle}

Write engaging, informative content that:
1. Thoroughly covers all phases mentioned
2. Uses practical examples and actionable advice
3. Maintains the brand voice and tone
4. Is scannable with subheadings if needed
5. Flows naturally from the previous context

Return clean HTML (no heading tag for the main section title - it will be added separately)."""
        
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
    sections: List[GeneratedSection]
) -> str:
    """AI · Conclusion (Takeaways + CTA)"""
    
    key_takeaways = [s.heading for s in sections]
    
    prompt = f"""Write a compelling conclusion for the blog article.

KEY SECTIONS COVERED:
{', '.join(key_takeaways)}

CONTENT BRIEF:
- Goal: {content_brief.goal}
- Target Audience: {content_brief.target_audience}

BRAND CONTEXT:
- CTAs: {', '.join(brand_profile.ctas)}
- Unique Angle: {brand_profile.unique_angle}
- Brand: {brand_profile.name}

Write a conclusion that:
1. Summarizes key takeaways from the article
2. Reinforces the main value proposition
3. Includes a relevant call-to-action
4. Encourages further engagement
5. Maintains brand voice and tone

Target 200-400 words. Return clean HTML."""
    
    llm = LLMService()
    return await llm.call(
        model=get_settings().extraction_model,
        prompt=prompt,
        response_format="text",
        max_tokens=600,
        temperature=0.6
    )

def merge_content_by_position(
    introduction: str,
    table_of_contents: str,
    body_sections: List[GeneratedSection],
    conclusion: str
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
    
    return AssembledContent(
        introduction=introduction,
        table_of_contents=table_of_contents,
        body=body_html,
        conclusion=conclusion,
        total_word_count=sum(s.word_count for s in body_sections)
    )

def assemble_article_html(assembled_content: AssembledContent, meta: MetaAndOutline) -> FinalArticle:
    """Assemble article HTML + word count - Sort sections by index → concatenate inside <article>"""
    
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
    </article>
    """.strip()
    
    return FinalArticle(
        meta_title=meta.meta_title,
        meta_description=meta.meta_description,
        slug=meta.slug,
        html_content=full_html,
        word_count=assembled_content.total_word_count
    )

async def save_content_draft(
    job: Job,
    article: FinalArticle,
    db: Session
) -> BlogDraft:
    """Save to blog_drafts table · Stage = Draft"""
    
    # Create or update blog job for this content generation
    blog_job = db.query(BlogJob).filter(BlogJob.id == job.id).first()
    if not blog_job:
        # Create new blog job from content generation job
        blog_job = BlogJob(
            id=job.id,
            org_id=job.org_id,
            brand_id=job.brand_id,
            created_by=job.created_by if hasattr(job, 'created_by') else 'system',
            keyword=job.input_payload.get("keyword", "Generated Content"),
            status="PENDING_REVIEW"
        )
        db.add(blog_job)
    
    # Create draft
    draft = BlogDraft(
        job_id=job.id,
        title=article.meta_title,
        meta_description=article.meta_description,
        html_content=article.html_content,
        word_count=article.word_count,
        seo_score=80,  # Default score, can be calculated later
        approved=False
    )
    
    db.add(draft)
    
    # Update job stage
    job.stage = JOB_STAGE_DRAFT
    job.status = "PROCESSING"  # Continue to image generation
    
    db.commit()
    return draft

# Utility functions
def safe_json_parse(raw_json: str) -> dict:
    """Safely parse JSON with fallbacks"""
    try:
        # Clean common LLM artifacts
        cleaned = raw_json.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON: {raw_json[:100]}...")
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

# Image generation functions
async def generate_image_prompt(
    article: FinalArticle,
    brand_profile: BrandProfile
) -> str:
    """AI · reads article + brand profile → image prompt"""
    
    prompt = f"""Generate a detailed image prompt for a featured image.

ARTICLE DETAILS:
- Title: {article.meta_title}
- Content Preview: {article.html_content[:1000]}

BRAND PROFILE:
- Brand: {brand_profile.name}
- Industry: {brand_profile.industry or 'General'}
- Image Subject Hints: {brand_profile.image_subject_hints or 'Professional, clean imagery'}
- Image Palette: {brand_profile.image_palette or 'Modern color scheme'}
- Visual Direction: {brand_profile.visual_direction or 'Professional and engaging'}

Create a detailed prompt for Leonardo AI that:
1. Captures the essence of the article
2. Matches the brand's visual style
3. Is professional and engaging
4. Avoids real people (use abstract concepts, illustrations, objects)
5. Is suitable for blog featured image use

Return only the image prompt text, no additional commentary."""
    
    llm = LLMService()
    return await llm.call(
        model="anthropic/claude-haiku-4-5-20251001",  # Best model for creative prompts
        prompt=prompt,
        response_format="text",
        max_tokens=300,
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
        
        # Generate image prompt
        image_prompt = await generate_image_prompt(article, brand_profile)
        logger.info(f"Generated image prompt: {image_prompt[:100]}...")
        
        # Generate with Leonardo
        leonardo = LeonardoService()
        raw_image_url = await leonardo.generate_image(image_prompt)
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
        
        # 01. Load SERP analysis
        serp_data = await load_serp_analysis(job_id, job.brand_id, db)
        logger.info(f"Loaded SERP data: {len(serp_data.keywords)} keywords, {len(serp_data.competitor_gaps)} gaps")
        
        # 02. Get brand profile
        brand_profile = db.query(BrandProfile).filter(
            BrandProfile.brand_id == job.brand_id
        ).first()
        
        if not brand_profile:
            raise ValueError(f"Brand profile not found for brand {job.brand_id}")
        
        target_keyword = job.input_payload.get("keyword", "content topic")
        logger.info(f"Target keyword: {target_keyword}")
        
        # 03. Generate content brief
        logger.info("Generating content brief...")
        content_brief = await generate_content_brief(serp_data, brand_profile, target_keyword)
        logger.info(f"Content brief generated: {content_brief.goal}")
        
        # 04. Generate meta & outline
        logger.info("Generating meta and outline...")
        meta_outline = await generate_meta_and_outline(content_brief, brand_profile, target_keyword)
        logger.info(f"Meta and outline generated: {meta_outline.meta_title}")
        
        # 05. Parse & validate outline
        validated_outline = parse_and_validate_outline(meta_outline.model_dump())
        logger.info(f"Outline validated: {len(validated_outline.sections)} sections")
        
        # 06. Parallel content generation
        logger.info("Starting parallel content generation...")
        intro_task = generate_introduction(content_brief, brand_profile, target_keyword)
        body_task = generate_body_sections(validated_outline, content_brief, brand_profile)
        
        introduction, body_sections = await asyncio.gather(intro_task, body_task)
        logger.info(f"Generated introduction and {len(body_sections)} body sections")
        
        # 07. Generate TOC and conclusion
        logger.info("Generating TOC and conclusion...")
        toc_task = generate_table_of_contents(body_sections)
        conclusion_task = generate_conclusion(content_brief, brand_profile, body_sections)
        
        toc, conclusion = await asyncio.gather(toc_task, conclusion_task)
        logger.info("TOC and conclusion generated")
        
        # 08. Merge content
        assembled_content = merge_content_by_position(introduction, toc, body_sections, conclusion)
        logger.info(f"Content assembled: {assembled_content.total_word_count} words")
        
        # 09. Assemble final article
        final_article = assemble_article_html(assembled_content, meta_outline)
        logger.info(f"Final article assembled: {final_article.meta_title}")
        
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
        db.commit()
        
        logger.info(f"Content generation completed successfully for job {job_id}")
        
    except Exception as e:
        logger.exception(f"Content generation failed for job {job_id}")
        job.status = "FAILED"
        job.error_message = str(e)
        db.commit()
        raise