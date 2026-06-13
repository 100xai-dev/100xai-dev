export const metadata = {
  title: "Terms & Conditions — 100xAI",
};

// Keep this version string in sync with backend CURRENT_TERMS_VERSION.
const TERMS_VERSION = "2026-06-09";

export default function TermsPage() {
  return (
    <div className="auth-shell">
      <div className="card stack" style={{ maxWidth: "720px", margin: "0 auto" }}>
        <div>
          <div className="meta" style={{ color: "var(--accent)", letterSpacing: "0.15em" }}>
            100xAI // LEGAL
          </div>
          <h2 style={{ marginTop: "8px" }}>Terms &amp; Conditions</h2>
          <p className="meta">Version {TERMS_VERSION}</p>
        </div>

        <section className="stack" style={{ gap: "12px" }}>
          <p>
            These Terms &amp; Conditions govern your use of the 100xAI platform. By creating an
            account or using the service, you agree to be bound by these terms.
          </p>
          <h3>1. Use of the service</h3>
          <p>
            You agree to use 100xAI only for lawful purposes and in accordance with these terms. You
            are responsible for all activity that occurs under your account and organization.
          </p>
          <h3>2. Content &amp; ownership</h3>
          <p>
            You retain ownership of the brand materials you provide. Content generated through the
            platform is provided for your use, subject to your compliance with these terms.
          </p>
          <h3>3. Billing</h3>
          <p>
            Paid plans are billed via Razorpay on a recurring basis until cancelled. Plan limits and
            pricing are described on the billing page and may change with notice.
          </p>
          <h3>4. Termination</h3>
          <p>
            We may suspend or terminate access for violations of these terms. You may cancel your
            subscription at any time from the billing page.
          </p>
          <h3>5. Changes to these terms</h3>
          <p>
            We may update these terms from time to time. When we do, the version is incremented and
            you will be asked to re-accept the updated terms on your next sign-in.
          </p>
          <p className="meta">
            This is placeholder legal copy — replace it with your finalized Terms &amp; Conditions.
          </p>
        </section>
      </div>
    </div>
  );
}
