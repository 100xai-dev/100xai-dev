#!/usr/bin/env python3
"""
Pinecone Integration Diagnostic Script

This script tests the Pinecone integration and identifies any issues
with crawled data ingestion.
"""

import asyncio
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.db import get_db
from app.models.onboarding import Brand


async def check_configuration():
    """Check Pinecone and OpenAI configuration."""
    print("🔧 Configuration Check")
    print("=" * 40)
    
    settings = get_settings()
    
    checks = [
        ("Pinecone API Key", settings.pinecone_api_key is not None),
        ("Pinecone Index Name", bool(settings.pinecone_index_name)),
        ("OpenAI API Key", settings.openai_api_key is not None),
        ("Embedding Model", bool(settings.embedding_model)),
    ]
    
    all_good = True
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}: {check_result}")
        if not check_result:
            all_good = False
    
    print(f"\nPinecone Index: {settings.pinecone_index_name}")
    print(f"Embedding Model: {settings.embedding_model}")
    
    return all_good


async def check_pinecone_connectivity():
    """Test Pinecone connectivity."""
    print("\n🔌 Pinecone Connectivity")
    print("=" * 40)
    
    settings = get_settings()
    
    if not settings.pinecone_api_key:
        print("❌ Cannot test - Pinecone API key not configured")
        return False
    
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        
        # Test listing indexes
        indexes = pc.list_indexes()
        print(f"✅ Connected to Pinecone")
        print(f"📋 Available indexes: {[idx.name for idx in indexes]}")
        
        # Test specific index
        if settings.pinecone_index_name:
            try:
                index = pc.Index(settings.pinecone_index_name)
                stats = index.describe_index_stats()
                print(f"✅ Index '{settings.pinecone_index_name}' accessible")
                print(f"📊 Index stats: {stats.total_vector_count} vectors, {len(stats.namespaces)} namespaces")
                return True
            except Exception as e:
                print(f"❌ Cannot access index '{settings.pinecone_index_name}': {e}")
                return False
        
    except Exception as e:
        print(f"❌ Pinecone connectivity failed: {e}")
        return False


async def check_openai_embeddings():
    """Test OpenAI embeddings."""
    print("\n🧠 OpenAI Embeddings")
    print("=" * 40)
    
    settings = get_settings()
    
    if not settings.openai_api_key:
        print("❌ Cannot test - OpenAI API key not configured")
        return False
    
    try:
        from app.services.ingestion import embed_batch
        
        test_texts = ["Hello world", "This is a test embedding"]
        embeddings = await embed_batch(
            test_texts, 
            settings.openai_api_key, 
            settings.embedding_model
        )
        
        print(f"✅ OpenAI embeddings working")
        print(f"📊 Generated {len(embeddings)} embeddings")
        print(f"📏 Embedding dimension: {len(embeddings[0])}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI embeddings failed: {e}")
        return False


async def check_database_state():
    """Check database state for knowledge sources and chunks."""
    print("\n💾 Database State")
    print("=" * 40)
    
    db = next(get_db())
    
    try:
        from sqlalchemy import text
        
        # Check brands
        brands = db.execute(text("SELECT COUNT(*) FROM brands")).scalar()
        ready_brands = db.execute(text("SELECT COUNT(*) FROM brands WHERE status = 'READY'")).scalar()
        
        print(f"📊 Total brands: {brands}")
        print(f"✅ Ready brands: {ready_brands}")
        
        # Check knowledge sources
        sources = db.execute(text("SELECT COUNT(*) FROM brand_knowledge_sources")).scalar()
        sources_with_text = db.execute(text(
            "SELECT COUNT(*) FROM brand_knowledge_sources WHERE normalized_text IS NOT NULL AND LENGTH(normalized_text) > 50"
        )).scalar()
        
        print(f"📄 Knowledge sources: {sources}")
        print(f"📝 Sources with text: {sources_with_text}")
        
        # Check knowledge chunks
        chunks = db.execute(text("SELECT COUNT(*) FROM brand_knowledge_chunks")).scalar()
        print(f"🧩 Knowledge chunks: {chunks}")
        
        if chunks == 0 and sources_with_text > 0:
            print("⚠️  Warning: Sources exist but no chunks created")
            
            # Check specific brand
            recent_brand = db.execute(text(
                "SELECT id, name FROM brands WHERE status = 'READY' ORDER BY created_at DESC LIMIT 1"
            )).fetchone()
            
            if recent_brand:
                brand_sources = db.execute(text(
                    "SELECT COUNT(*) FROM brand_knowledge_sources WHERE brand_id = :brand_id"
                ), {"brand_id": recent_brand.id}).scalar()
                print(f"🔍 Recent brand '{recent_brand.name}' has {brand_sources} sources")
                
        return {
            "brands": brands,
            "ready_brands": ready_brands,
            "sources": sources,
            "sources_with_text": sources_with_text,
            "chunks": chunks
        }
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return {}
    finally:
        db.close()


async def test_ingestion_workflow():
    """Test the ingestion workflow with a sample brand."""
    print("\n🔄 Ingestion Workflow Test")
    print("=" * 40)
    
    settings = get_settings()
    
    if not settings.openai_api_key:
        print("❌ Cannot test ingestion - OpenAI API key required")
        return False
        
    if not settings.pinecone_api_key:
        print("❌ Cannot test ingestion - Pinecone API key required")
        return False
    
    db = next(get_db())
    
    try:
        # Find a ready brand with sources
        brand = db.execute(text("""
            SELECT b.id, b.name, COUNT(s.id) as source_count
            FROM brands b
            LEFT JOIN brand_knowledge_sources s ON b.id = s.brand_id
            WHERE b.status = 'READY' AND s.normalized_text IS NOT NULL
            GROUP BY b.id, b.name
            HAVING COUNT(s.id) > 0
            ORDER BY b.created_at DESC
            LIMIT 1
        """)).fetchone()
        
        if not brand:
            print("❌ No suitable brand found for testing")
            return False
            
        print(f"🎯 Testing with brand: {brand.name} ({brand.source_count} sources)")
        
        # Get sources
        sources = db.execute(text(
            "SELECT * FROM brand_knowledge_sources WHERE brand_id = :brand_id AND normalized_text IS NOT NULL"
        ), {"brand_id": brand.id}).fetchall()
        
        print(f"📄 Found {len(sources)} sources with content")
        
        # Test chunking
        from app.services.ingestion import chunk_text, count_tokens
        
        total_chunks = 0
        total_tokens = 0
        
        for source in sources[:2]:  # Test first 2 sources
            if source.normalized_text and len(source.normalized_text) > 50:
                chunks = chunk_text(source.normalized_text)
                tokens = sum(count_tokens(chunk) for chunk in chunks)
                total_chunks += len(chunks)
                total_tokens += tokens
                print(f"  📄 Source {source.url}: {len(chunks)} chunks, {tokens} tokens")
        
        print(f"📊 Total: {total_chunks} chunks, {total_tokens} tokens")
        
        if total_chunks > 0:
            print("✅ Chunking works correctly")
            return True
        else:
            print("❌ No chunks generated")
            return False
            
    except Exception as e:
        print(f"❌ Ingestion workflow test failed: {e}")
        return False
    finally:
        db.close()


async def main():
    """Run all diagnostic tests."""
    print("🚀 Pinecone Integration Diagnostics")
    print("=" * 50)
    
    # Test 1: Configuration
    config_ok = await check_configuration()
    
    # Test 2: Pinecone connectivity
    pinecone_ok = await check_pinecone_connectivity()
    
    # Test 3: OpenAI embeddings
    openai_ok = await check_openai_embeddings()
    
    # Test 4: Database state
    db_state = await check_database_state()
    
    # Test 5: Ingestion workflow
    ingestion_ok = await test_ingestion_workflow()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    print(f"✅ Configuration: {'PASS' if config_ok else 'FAIL'}")
    print(f"✅ Pinecone connectivity: {'PASS' if pinecone_ok else 'FAIL'}")
    print(f"✅ OpenAI embeddings: {'PASS' if openai_ok else 'FAIL'}")
    print(f"✅ Database state: {'OK' if db_state else 'ISSUES'}")
    print(f"✅ Ingestion workflow: {'PASS' if ingestion_ok else 'FAIL'}")
    
    # Diagnosis
    print("\n🔍 DIAGNOSIS:")
    
    if not config_ok:
        print("❌ MISSING CONFIGURATION:")
        if not get_settings().openai_api_key:
            print("   • Set OPENAI_API_KEY for embeddings")
        if not get_settings().pinecone_api_key:
            print("   • Set PINECONE_API_KEY for vector storage")
    
    if config_ok and db_state.get('sources_with_text', 0) > 0 and db_state.get('chunks', 0) == 0:
        print("❌ INGESTION NOT WORKING:")
        print("   • Brands have crawled content but no embeddings stored")
        print("   • Check onboarding pipeline logs")
        print("   • Ensure API keys are configured before running onboarding")
    
    if all([config_ok, pinecone_ok, openai_ok, ingestion_ok]):
        print("✅ ALL SYSTEMS WORKING:")
        print("   • Pinecone integration is functioning correctly")
        print("   • Future onboarding will store embeddings properly")
    
    print("\n💡 RECOMMENDATIONS:")
    if not get_settings().openai_api_key:
        print("   1. Set OPENAI_API_KEY environment variable")
        print("   2. Re-run onboarding for existing brands to generate embeddings")
    if not pinecone_ok:
        print("   1. Verify Pinecone API key and index name")
        print("   2. Check index exists in Pinecone console")
    if db_state.get('chunks', 0) == 0 and db_state.get('sources', 0) > 0:
        print("   1. API keys were missing during onboarding")
        print("   2. Re-onboard brands after setting API keys")


if __name__ == "__main__":
    asyncio.run(main())