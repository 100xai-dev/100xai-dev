"use client";

import { useScheduler } from "@/lib/scheduler/context";

export default function SettingsPage() {
  const { brand } = useScheduler();
  const handle = brand.domain.split(".")[0];

  return (
    <div className="page-pad" style={{ maxWidth: 680 }}>
      <div className="panel-box">
        <h3>Connected accounts</h3>
        <div className="ph">Channels Schedulr can publish to</div>
        <div className="up-item"><div className="uic" style={{ background: "var(--blog)" }}>B</div><div className="ub"><div className="t">{brand.name} Blog · Shopify</div><div className="m">Connected · auto-publish on</div></div><div className="lstatus scheduled">ACTIVE</div></div>
        <div className="up-item"><div className="uic" style={{ background: "var(--li)" }}>in</div><div className="ub"><div className="t">{brand.name} · LinkedIn Page</div><div className="m">Connected via Unipile</div></div><div className="lstatus scheduled">ACTIVE</div></div>
        <div className="up-item"><div className="uic" style={{ background: "var(--ig)" }}>ig</div><div className="ub"><div className="t">@{handle} · Instagram</div><div className="m">Connected via Zernio</div></div><div className="lstatus scheduled">ACTIVE</div></div>
      </div>
      <div className="panel-box" style={{ marginTop: 18 }}>
        <h3>Approval flow</h3>
        <div className="ph">How posts get reviewed before publishing</div>
        <div className="up-item"><div className="uic" style={{ background: "var(--success)" }}>✓</div><div className="ub"><div className="t">WhatsApp group approval</div><div className="m">Drafts sent to client group · gated publishing</div></div><div className="lstatus scheduled">ON</div></div>
      </div>
    </div>
  );
}
