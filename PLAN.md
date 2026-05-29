# 100xAI Platform — Consolidated Execution Plan

**Last updated:** 2026-05-26  
**Target deadline discussed:** June 10, 2026  
**Audience:** Engineers + product (Shubham, Priyam, team)

This document merges architecture notes, Phase 1 meeting decisions, spreadsheets, Pillar/HTML flowcharts, and follow-up chats into one actionable plan � plus **open questions** required before execution.

---

## 1. Product vision

**Elevator pitch:** �HubSpot + Hootsuite + Jasper + Zapier + AI Brand Brain� � scoped for **incremental shipping**.

**Differentiator (architecture doc):** Persistent brand memory + cross-platform consistency + feedback loops � not generic copy-paste LLM outputs.

---

## 2. Agreed constraints & context

| Item | Decision / assumption |
|------|------------------------|
| **Timeline pressure** | ~15 working days ? **June 10** milestone |
| **Team** | **2 full-stack engineers** (intensive schedule); founder/product makes tradeoffs |
| **Day-zero users** | **10 existing clients** onboarding |
| **Tenancy** | Multi-tenant; **multi-brand per org/user where applicable**; **single user per brand** (no shared seat on same brand unless you change this) |
| **Customer type** | In-house marketing teams + **100xAI admin** onboarding individuals |
| **Region / language** | **India** focus; **English** for Phase 1 content |
| **Stack (aligned decisions)** | **FastAPI** monolith (single deployable app), **PostgreSQL**, **Pinecone** (vectors), **Redis** + workers for async jobs |
| **LLM** | **Claude** (and/or other models) via **OpenRouter** or similar � no hard-coded provider keys in code |
| **Social / messaging** | **Unipile** for LinkedIn (posting, scheduling, DMs per direction below); **WhatsApp** for outreach via **API** (e.g. **VAPI** / WhatsApp Business API � TBD) |
| **Website ? product** | **Phase 1 meeting:** no automated Shopify/WordPress/Webflow **connectors** first � **schedule a call** for website connectivity. **Later chat:** blogs should eventually publish to **client platform** (Shopify / WordPress / Webflow / custom) � **conflict to resolve** (see Open Questions). |
| **Security posture** | OAuth/token encryption, RBAC, audit logs from the start; tests on critical paths |
| **Analytics** | Dashboard + calendar are **must-haves**; **GA4** may be placeholder or deferred (see Open Questions) |
| **Budget** | LLM/API costs to be finalized with team |

---

## 3. Phase 1 scope (May 26, 2026 meeting � aligned items)

These are **confirmed** priorities for the **June 10** milestone unless superseded by your latest messages (below).

### 3.1 Onboarding & brand understanding

- **Two paths:** 100xAI reaches out OR client self-signups ? either way ends in **scheduled call** checklist for website/technical setup.
- **Connector deferral:** No building Shopify/WordPress-specific auto-publish integrations **in Phase 1** if that blocks the date � operational handoff via **call** (explicit meeting decision).
- **Brand persona (DNA):**
  - **Primary:** Crawl client **website URL** ? extract **HTML/markdown** ? AI (**Anthropic/Claude** pipeline) produces a **structured brand artifact** (tone, persona, guardrails, audience, messaging�).
  - **Fallback:** **Manual form + document upload**; optional **custom AI agent** if crawl insufficient.
  - **RAG:** Chunks embedded and retrieved for generation (see infra: Postgres + Pinecone).

### 3.2 Core product pillars for Phase 1 (meeting)

1. **Blogs:** SEO + **AEO** oriented content for **client website outcome** (see publish path open questions).
2. **SEO / AEO:** Engine lives **in your tool**; �analytics first� mentality in spreadsheets + meeting dashboard notes.
3. **LinkedIn:** **Engagement** scope in meeting explicitly included **ICP commenting** and **first DM** (not �post-only� originally).
4. **WhatsApp:** Mentioned as **future** / secondary in spreadsheet (**VAPI**); your latest ask includes **WhatsApp API for outreach** � treat as **scope expansion** vs June 10 unless prioritized (Open Questions).

### 3.3 Dashboard & ops

- **Content calendar**
- **Dashboard:** visibility into content pipeline, SEO/AEO-related signals, LinkedIn activity, and **website traffic** when available (GA4 / Search Console � TBD)

### 3.4 Roles

- **Admin:** 100xAI team
- **Client:** individuals onboarded per brand / org structure you define

### 3.5 Sync & deliverables

- **Daily (or M/W/F) sync** after **10 PM** (per meeting)
- **Action:** Share **brand persona prompt document** (Priyam) so engineering can version prompts in repo

---

## 4. Expanded scope from later messages (reconcile with Phase 1)

| Topic | What you added | Impact |
|--------|----------------|--------|
| **Blog publish target** | Live on **Shopify / WordPress / Webflow / custom** | High � requires APIs, auth per platform, or human publish workflow |
| **LinkedIn** | **Post scheduling** �right now� | Add Unipile posting + schedule + media handling |
| **Vectors** | **Pinecone + Postgres** | Dual store: relational in PG, embeddings in Pinecone with metadata (`brand_id`, etc.) |
| **WhatsApp outreach** | API-based marketing | New channel: templates, opt-in, BSP/Meta policy, VAPI vs direct Cloud API |

**Rule of thumb for planning:** June 10 needs a **written �Definition of Done�** that either **includes** or **explicitly defers** each row above.

---

## 5. Technical architecture (working target)

```
[ Next.js + Tailwind + ShadCN ]  ?  [ FastAPI monolith ]
                                        ?
                    ?????????????????????????????????????????
                    ?                   ?                   ?
              PostgreSQL            Pinecone           Redis (queues)
           (source of truth)     (vector search)    (crawl, gen, publish)
                    ?
              Encrypted tokens, audit logs, job state machine
                    ?
        External: OpenRouter/LLM, Unipile, SEO APIs (optional),
                  crawl (Firecrawl/Crawl4AI/Puppeteer),
                  WhatsApp Business API / VAPI (Phase TBD)
```

- **Async by default** for crawl, long blog generation, image steps, outbound sends � avoid blocking HTTP requests for minutes.

---

## 6. Modules & execution pillars

### 6.1 Brand DNA (�extractor / copier / generator�)

**Goal:** Turn raw inputs ? **frozen brand profile** consumed by all generators.

**Inputs:** Website crawl (? pages policy TBD), uploads, manual form, optional pasted examples.

**Outputs:** Structured JSON artifact + human-editable UI + versioning (optional).

**Stores:** Postgres row per brand + Pinecone chunks with metadata filter by `brand_id`.

**Open:** Exact JSON schema, prompt source file, and whether �copy voice from example posts� is automatic or upload-only.

---

### 6.2 Blogs + SEO + AEO (AI-powered)

**SEO (classic search):** Keyword intent, structure, meta, internal linking hints, optional live volume/difficulty via **DataForSEO or similar** (if not ready ? stub checklist still passes �SEO-shaped� output).

**AEO (answer engines):** Direct-answer block, clear entities, FAQs, structured sections; optional JSON-LD strategy for client CMS (when publish path exists).

**Generation flow (conceptual � can align with Pillar doc �8 where applicable):**

1. Aggregate research context (SERP/competitor analysis if API available).
2. Content brief ? outline (`sections[]`) ? validate JSON.
3. Fan-out sections with `section_index` ? assemble `<article>` + word count.
4. Non-blocking featured image pipeline if in scope (Leonardo + Placid or simplified).
5. Human review ? **publish or export**.

**Stores:** Jobs with stages (`NEW` ? `KEYWORD` ? `CONTENT` ? `DRAFT` ? �) if doing full pillar; simplified job model acceptable for June 10 if scoped.

---

### 6.3 LinkedIn (posting + DM)

- **Posting + scheduling:** Unipile; calendar integration; statuses `draft ? approved ? scheduled ? published`; LinkedIn **text + image** if required (Open Question).
- **DM + comment (meeting Phase 1):** Generate drafts ? **human approval mandatory** ? send via Unipile; audit trail.
- **Discovery:** Paste URL first; automated ICP feed = stretch.

---

### 6.4 WhatsApp (outreach / marketing)

Likely stacks:

- **Meta WhatsApp Cloud API** (direct) or **BSP** partner
- **VAPI** or similar voice/automation layered for campaigns (per spreadsheet whisper)

Needs: **opt-in**, template messages, per-country rules, rate limits, **no cold spam** policy.

**Default recommendation:** define **Phase 1.5** unless you narrow to �one template + manual trigger� for June 10.

---

## 7. Suggested milestone breakdown (June 10)

| Week | Focus |
|------|--------|
| **Days 1�3** | Auth, brands, admin, crawl + persona job, Pinecone ingest, Redis workers |
| **Days 4�7** | Blog job v1 (SEO/AEO shape), review UI, export |
| **Days 8�10** | Unipile: connect, post, schedule, DM/comment with approval |
| **Days 11�12** | Calendar + dashboard aggregates |
| **Days 13�14** | 10-client dry run, security, tests |
| **Day 15 / June 10** | Demo freeze, P0 only |

**WhatsApp** only fits June 10 if scoped to **single approved use-case** (Open Questions).

---

## 8. Out of scope / Phase 2+ (unless you promote)

- Full HubSpot/Salesforce CRM sync
- Multi-agent orchestration, auto-comment at scale without approval
- Instagram / Meta / Pinterest / X **repurposing** (spreadsheet: secondary)
- Best-time ML, full insight engine (�42% more engagement� auto-narratives)
- Billing/Stripe (schema flag only OK for early phase)

---

## 9. Open questions � **required to execute**

Answer these in one pass (copy section 9.1 at bottom). Without answers, engineering will guess and June 10 risk goes up.

### 9.1 Blogs + SEO + AEO

1. **June 10 definition:** Is the blog **finished** when it is (A) **approved HTML in app + export**, (B) **published to at least one CMS automatically**, or (C) **published after every call manually**? we are giving option to aprove the blog not to edit it , it disapproved , start from the begining . Finished when blog is published in atleast one cms 
2. **If auto-publish:** Which **one** platform is **first** for June 10 (WordPress / Shopify / Webflow / other)? �All four� is usually not one milestone. will work on all simultaneaously 
3. **Keyword model:** One  **seed keyword ? one article per job**, or **batch many keywords** in one job?  explain 

4. **Pillar depth:** Full **DataForSEO + Apify** pipeline on June 10, or **stub SEO research** + strong on-page SEO/AEO from LLM + checklist? Full depth
5. **DataForSEO (or alternative):** Account + budget **live by** which date? If �no,� confirm **stub OK**. 10th june live date 
6. **AEO deliverables:** Minimum set = direct answer + FAQ + what else (schema, `llms.txt`, comparison tables)?dk
7. **Article storage:** Single merged HTML vs separate fields (intro, TOC, body, conclusion) � what does the **first CMS** need? Explain why did you think of seprate field HTML for storage ?
8. **Images:** Featured image required on June 10? If yes: **Leonardo + Placid** or simplified (stock / upload only)? Yes it will generated using leonardo +placid or any other models
9. **Competitor / SERP retention:** Store full text vs summaries only; retention days?explain in detail and laymenn terms
10. **Regulated content:** Any YMYL clients in the 10 � extra legal checks? the regulations will be defined by banned keywords and all that described . ai should strictly follow the templates
### 9.2 Brand DNA (extractor / copier / generator)

11. **Persona prompt doc:** Received from Priyam? If **N**, who signs off on v1 prompts before client-facing use? will recieve soon , hold this 
12. **Crawl scope:** Exact **max pages** (you mentioned 5�10) and **which paths** (home, about, blog index, last N posts, etc.)?
13. **Crawl tool:** Firecrawl vs Crawl4AI vs Puppeteer � **which is production for June 10**? first a custom agent will look for basic info like html , dom , urls and ai agent scrapes in detail
14. **�Copier� meaning:** Copy **voice from uploaded examples** only, or also **clone structure** from competitor URLs (ethical boundary)? no ethical boundary , its alll aboyt getting conpetetive advantage 
15. **Persona edits:** After AI generation, can clients edit **all** fields or only some (lock guardrails)?no wediting 
16. **Vector lifecycle:** On brand delete, **Pinecone delete-by-metadata** required for compliance � confirm. dont understand 

### 9.3 LinkedIn (posting + DM)

17. **June 10 must-have list:** Rank: **(a)** scheduled posts **(b)** DMs **(c)** comments on ICP posts � **all three** or subset? all three
18. **Post format:** Text-only OK or **text + image** required? Carousels/video **out** for June 10? text + image 
19. **Account type:** Post/comment/DM from **personal profile**, **company page**, or **per-client choice**? per client 
20. **Unipile:** Confirm all actions (post, schedule, DM, comment) are **supported and tested** in your tenant; any **Meta/LinkedIn app review** pending?
21. **Approval:** **100% human approve** before any outbound message/post � still true? yes  
22. **Virality score / auto-regenerate** from architecture doc � **in or out** for June 10? in 
23. **ICP discovery:** Paste URL only for June 10, or **feed/search** automation?url + manual form for backup 

### 9.4 WhatsApp (API outreach / marketing)

24. **June 10:** Is WhatsApp **in** or **deferred** to **Phase 1.5**? If **in**, what is the **single** use-case (e.g. �appointment follow-up template after form submit�)? in phase 1 , use case is marketting , sending  updates to community about the news blogs 
25. **Provider:** **WhatsApp Cloud API** direct vs **BSP** vs **VAPI** � which owns **sending**, which owns **conversation design**?Vapi owns all
26. **Templates:** Already approved Meta **message templates** for the 10 clients, or Greenfield?
27. **Opt-in:** Proof of consent (checkbox, webhook, CSV import rules) � who is legally responsible for compliance? it will be handled 
28. **Volume caps** and **quiet hours** (India) � defaults?
29. **Link to blog/LinkedIn:** Should WhatsApp messages **deep-link** to tracked URLs (UTMs) � required? yes 

### 9.5 Analytics & dashboard

30. **GA4 June 10:** **Must be live** per client property, or **placeholder** (�connect on onboarding call�) with manual numbers?connect on onboarding call
31. **Search Console:** In scope June 10? explain what is search console
32. **LinkedIn metrics:** Pull from Unipile into dashboard � required or counts only? yup 

### 9.6 Cross-cutting / delivery

33. **Hosting:** Target region, domain, HTTPS � staging-only OK on June 10?will think later , lets first develop 
34. **Pricing field** in DB only vs Stripe live � June 10? will update later
35. **Success sentence:** One line: �On June 10 we demonstrate __________________________.� explain 

---

## 10. Copy-paste answer block (for you / Priyam)

```
BLOG/SEO/AEO
1. Done = A/B/C: __
2. First auto-publish platform: __ (or none)
3. Keywords: one-per-job / batch
4. Pillar APIs June 10: full / stub
5. SEO API live date or stub OK: __
6. AEO minimum: __
7. HTML shape: merged / split / depends on CMS: __
8. Featured image: Y/N, tool: __
9. SERP storage: __
10. YMYL clients: Y/N

BRAND DNA
11. Persona doc: Y/N
12. Crawl: __ pages, paths: __
13. Crawl tool: __
14. Copier scope: __
15. Editable persona fields: all / partial: __
16. Pinecone delete on brand delete: Y/N

LINKEDIN
17. Rank a/b/c for June 10: __
18. Post format: __
19. Profile type: __
20. Unipile edge cases: __
21. Human approve all: Y/N
22. Virality score: Y/N
23. ICP discovery: paste / auto: __

WHATSAPP
24. June 10 in/out, use-case: __
25. Provider stack: __
26. Templates ready: Y/N
27. Opt-in owner: __
28. Caps/quiet hours: __
29. Tracked links: Y/N

DASHBOARD
30. GA4: live / placeholder
31. GSC: Y/N
32. LI metrics depth: __

DELIVERY
33. Staging OK: Y/N
34. Stripe: Y/N
35. Success line: __
```

---

## 11. Document map in repo

| Asset | Contents |
|--------|-----------|
| `PLAN.md` | This file |
| `AI Brand OS � Developer Friendly End-to-End Architecture Plan.pdf` | 8-layer architecture, phased roadmap |
| `pillar-blog-engine-flowchart.html` | Pillar pipelines, ClientProfile, external APIs |
| `markdown-preview.pdf` | Detailed PRD (image PDF � extract text externally if needed) |
| Meeting May 26 + spreadsheets | Phase 1 focus, onboarding via call, services split |

---

## 12. Next step

1. Fill **�10 answer block**.  
2. Lock **June 10 Definition of Done** to match answers.  
3. Split backlog: **Must (P0)** vs **Stretch (P1)** for WhatsApp and multi-CMS publish.

---

*Generated for 100xAI internal planning � update as decisions land.*
