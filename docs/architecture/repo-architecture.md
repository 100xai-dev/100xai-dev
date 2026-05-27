# Repo Architecture

The repo is structured around stable product boundaries instead of implementation phases.

## Applications

- `apps/web`: browser UI for onboarding, approvals, calendar, dashboard, and integration setup.
- `apps/api`: FastAPI monolith. Owns tenancy, persistence, auth, job orchestration, provider adapters, and audit logs.
- `apps/worker`: background process entrypoint for crawl, generation, publish, metrics, and outbound jobs.

## Packages

- `packages/prompts`: prompt files and examples. This lets non-code contributors own generation behavior without editing application code.
- `packages/shared-schemas`: JSON schemas shared between prompts, backend validation, and future frontend form generation.

## Future-Proof Boundaries

- CMS publishing should go through adapter interfaces. WordPress can ship first while Shopify, Webflow, and custom CMS adapters use the same contract.
- External providers should stay behind integration clients. Business workflows should not call provider SDKs directly.
- Brand DNA is the central memory object. Every content, image, outreach, and publishing workflow should consume it through a typed schema.
- Long-running work should run as jobs, not blocking HTTP requests.

