# Domain Boundaries

## Core Domains

- `auth`: users, roles, sessions, tenant scoping.
- `brands`: organizations, brands, onboarding state.
- `brand_dna`: structured brand memory and generation status.
- `knowledge_base`: source documents, chunks, embeddings, Pinecone metadata.
- `crawler`: website, sitemap, rendered-page, and SERP page extraction.
- `keywords`: seed keywords, expansion, scoring, and brand-fit filtering.
- `serp`: search results, competitor summaries, and retained metadata.
- `blog_jobs`: content pipeline from keyword to approved article.
- `images`: featured image prompt, generation, storage, and CMS attachment.
- `publishing`: CMS adapters and publish records.
- `linkedin`: posts, comments, DMs, approvals, Unipile calls, metrics.
- `whatsapp`: campaigns, recipients, consent gates, VAPI calls, tracked links.
- `dashboard`: operational status and summary metrics.
- `calendar`: scheduled content across blogs, LinkedIn, and WhatsApp.
- `audit`: immutable records for approval, send, publish, and token events.

## Rule

External provider details stay inside `integrations`. Product workflows call domain services, and domain services call integration clients.
