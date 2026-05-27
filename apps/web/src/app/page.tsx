const pipelineItems = [
  "Brand onboarding",
  "Brand DNA",
  "Crawler jobs",
  "Blog engine",
  "Image generation",
  "Publishing",
  "LinkedIn",
  "WhatsApp",
  "Dashboard"
];

export default function Home() {
  return (
    <main className="shell">
      <section className="header">
        <p className="eyebrow">100xAI Platform</p>
        <h1>Brand intelligence, content production, and distribution in one operating system.</h1>
        <p className="summary">
          This scaffold is ready for the first implementation slice: onboarding a brand, creating
          crawl jobs, generating Brand DNA, and storing reusable brand memory.
        </p>
      </section>

      <section className="grid" aria-label="Product modules">
        {pipelineItems.map((item) => (
          <div className="module" key={item}>
            {item}
          </div>
        ))}
      </section>
    </main>
  );
}
