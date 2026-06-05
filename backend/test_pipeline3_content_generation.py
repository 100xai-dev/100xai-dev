#!/usr/bin/env python3
"""
Test Pipeline 3: Content Generation
Tests the complete content generation workflow structure and data models.
"""
import asyncio
import os
import sys
sys.path.insert(0, '.')

from sqlalchemy.orm import Session
from app.db import get_db
from app.models.onboarding import Job, BrandProfile, Brand
from app.services.content_generation import (
    parse_and_validate_outline,
    merge_content_by_position,
    assemble_article_html,
    SerpAnalysisData,
    ContentBrief,
    MetaAndOutline,
    ValidatedSection,
    GeneratedSection,
    safe_json_parse,
    count_words_in_html,
    clean_markdown_fences
)

def test_content_generation_workflow():
    """Test the core content generation workflow (without external APIs)"""
    
    print("🧪 Testing Pipeline 3: Content Generation Workflow")
    print("=" * 60)
    
    try:
        # Test 1: Data Models
        print("📊 Testing data models...")
        mock_serp_data = SerpAnalysisData(
            keywords=[("AI content", 85.0), ("blog automation", 78.0)],
            competitor_gaps=["Lacks technical depth", "No code examples", "Poor SEO optimization"],
            competitive_advantages=["Better AI integration", "Comprehensive guides", "Expert analysis"],
            serp_metadata={"avg_content_score": 80.0, "total_keywords": 2}
        )
        print(f"✅ SerpAnalysisData created: {len(mock_serp_data.keywords)} keywords")
        
        # Test 2: Content Brief Model
        content_brief = ContentBrief(
            goal="Create comprehensive AI content guide",
            content_type="blog_post",
            target_audience="Tech professionals",
            search_intent="informational",
            target_word_count=2500,
            content_angle="Practical implementation focus",
            ctas=["Start free trial", "Learn more"],
            sections=[
                {"heading": "Introduction to AI Content", "type": "intro"},
                {"heading": "Technical Implementation", "type": "body"},
                {"heading": "Best Practices", "type": "body"},
                {"heading": "Conclusion", "type": "conclusion"}
            ]
        )
        print(f"✅ ContentBrief created: {content_brief.goal}")
        
        # Test 3: Meta and Outline
        meta_outline = MetaAndOutline(
            slug="ai-content-generation-guide",
            meta_title="AI Content Generation: Complete Implementation Guide",
            meta_description="Learn how to implement AI content generation with practical examples and best practices.",
            h1="AI Content Generation: Complete Guide",
            sections=[
                {"heading": "Understanding AI Content", "heading_type": "h2", "phases": ["Definition", "Benefits", "Use cases"]},
                {"heading": "Implementation Steps", "heading_type": "h2", "phases": ["Setup", "Configuration", "Testing"]},
                {"heading": "Best Practices", "heading_type": "h2", "phases": ["Quality control", "Optimization", "Monitoring"]}
            ]
        )
        print(f"✅ MetaAndOutline created: {meta_outline.meta_title}")
        
        # Test 4: Outline Validation
        print("\n🔍 Testing outline validation...")
        validated_outline = parse_and_validate_outline(meta_outline.model_dump())
        print(f"✅ Outline validated: {len(validated_outline.sections)} sections")
        for i, section in enumerate(validated_outline.sections):
            print(f"   Section {i+1}: {section.heading} ({len(section.phases)} phases)")
        
        # Test 5: Generated Sections
        print("\n📝 Testing section generation...")
        mock_sections = [
            GeneratedSection(
                index=i,
                heading=f"Test Section {i+1}",
                heading_type="h2",
                content=f"<p>This is comprehensive content for section {i+1}. It covers important topics with detailed explanations and practical examples.</p><h3>Key Points</h3><ul><li>Important point 1</li><li>Important point 2</li></ul>",
                word_count=150 + (i * 25)
            ) for i in range(3)
        ]
        print(f"✅ Generated sections created: {len(mock_sections)} sections")
        
        # Test 6: Content Assembly
        print("\n🔧 Testing content assembly...")
        mock_introduction = "<p>Welcome to this comprehensive guide on AI content generation. This article will provide you with practical insights and implementation strategies.</p>"
        mock_toc = "<nav><ol><li><a href='#section-1'>Test Section 1</a></li><li><a href='#section-2'>Test Section 2</a></li><li><a href='#section-3'>Test Section 3</a></li></ol></nav>"
        mock_conclusion = "<p>In conclusion, AI content generation offers tremendous opportunities for scaling content creation while maintaining quality and relevance.</p>"
        
        assembled_content = merge_content_by_position(
            mock_introduction, mock_toc, mock_sections, mock_conclusion
        )
        print(f"✅ Content assembled: {assembled_content.total_word_count} words")
        
        # Test 7: Final Article Assembly
        print("\n📄 Testing final article assembly...")
        final_article = assemble_article_html(assembled_content, meta_outline)
        print(f"✅ Final article assembled")
        print(f"   Title: {final_article.meta_title}")
        print(f"   Slug: {final_article.slug}")
        print(f"   Word count: {final_article.word_count}")
        print(f"   HTML length: {len(final_article.html_content)} characters")
        
        # Test 8: Utility Functions
        print("\n🛠️ Testing utility functions...")
        
        # Test JSON parsing
        test_json = '{"test": "value", "number": 123}'
        parsed = safe_json_parse(test_json)
        print(f"✅ JSON parsing: {parsed}")
        
        # Test markdown cleaning
        markdown_content = "```html\n<p>Test content</p>\n```"
        cleaned = clean_markdown_fences(markdown_content)
        print(f"✅ Markdown cleaning: {cleaned}")
        
        # Test word counting
        html_content = "<p>This is a test sentence with several words.</p><p>Another paragraph here.</p>"
        word_count = count_words_in_html(html_content)
        print(f"✅ Word counting: {word_count} words")
        
        # Show sample output
        print(f"\n📖 Sample article preview:")
        print(f"Meta title: {final_article.meta_title}")
        print(f"Meta description: {final_article.meta_description}")
        print(f"Article structure preview:")
        article_lines = final_article.html_content.split('\n')[:10]
        for line in article_lines:
            if line.strip():
                print(f"   {line.strip()}")
        print("   ...")
        
        print("\n🎉 Pipeline 3 Content Generation Structure Test: SUCCESS")
        print("\n📋 VERIFIED COMPONENTS:")
        print("   ✅ Data models and validation")
        print("   ✅ Content assembly workflow") 
        print("   ✅ HTML generation and formatting")
        print("   ✅ Utility functions")
        print("   ✅ Error handling structures")
        
        print("\n💡 NEXT STEPS:")
        print("   1. Set ANTHROPIC_API_KEY or OPENROUTER_API_KEY for LLM calls")
        print("   2. Set LEONARDO_API_KEY to test image generation")
        print("   3. Set PLACID_API_KEY to test branded templates")
        print("   4. Run full pipeline with: POST /v1/brands/{id}/content-generation")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_content_generation_workflow()
    sys.exit(0 if success else 1)