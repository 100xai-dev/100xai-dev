"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { submitManualProfile } from "@/lib/api";
import type { BrandProfileContent } from "@/lib/types";

function parseCsvList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ManualProfileForm({ brandId, brandName }: { brandId: string; brandName: string }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function onSubmit(formData: FormData) {
    const payload: BrandProfileContent = {
      name: String(formData.get("name") || brandName),
      site_url: String(formData.get("site_url") || "") || null,
      one_liner: String(formData.get("one_liner") || ""),
      industry: String(formData.get("industry") || "") || null,
      allowed_topics: parseCsvList(String(formData.get("allowed_topics") || "")),
      disallowed_topics: parseCsvList(String(formData.get("disallowed_topics") || "")),
      audience_personas: parseCsvList(String(formData.get("audience_personas") || "")),
      tone_rules: String(formData.get("tone_rules") || ""),
      banned_phrases: parseCsvList(String(formData.get("banned_phrases") || "")),
      unique_angle: String(formData.get("unique_angle") || ""),
      ctas: parseCsvList(String(formData.get("ctas") || "")),
      proof_points: parseCsvList(String(formData.get("proof_points") || "")),
      messaging_guardrails: parseCsvList(String(formData.get("messaging_guardrails") || "")),
      compliance_keywords: parseCsvList(String(formData.get("compliance_keywords") || "")),
      image_subject_hints: String(formData.get("image_subject_hints") || "") || null,
      image_palette: String(formData.get("image_palette") || "") || null,
      visual_direction: String(formData.get("visual_direction") || "") || null,
    };

    if (!payload.one_liner || payload.allowed_topics.length === 0 || payload.audience_personas.length === 0 || payload.ctas.length === 0) {
      setError("Fill one_liner and at least one value for allowed_topics, audience_personas, and ctas.");
      return;
    }

    try {
      setPending(true);
      setError("");
      await submitManualProfile(brandId, payload);
      router.push(`/brands/${brandId}/dna`);
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to submit manual profile.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form action={onSubmit} className="card stack">
      <h2>[MANUAL_COGNITIVE_IDENTITY_FORM]</h2>
      <p className="meta">
        Fill this once in draft state. It creates the initial brand profile for review and approval.
      </p>
      <label>
        Name
        <input defaultValue={brandName} name="name" required />
      </label>
      <label>
        Site URL
        <input name="site_url" type="url" />
      </label>
      <label>
        One liner
        <textarea name="one_liner" required />
      </label>
      <label>
        Industry
        <input name="industry" />
      </label>
      <label>
        Allowed topics (comma separated)
        <input name="allowed_topics" required />
      </label>
      <label>
        Disallowed topics (comma separated)
        <input name="disallowed_topics" />
      </label>
      <label>
        Audience personas (comma separated)
        <input name="audience_personas" required />
      </label>
      <label>
        Tone rules
        <textarea name="tone_rules" required />
      </label>
      <label>
        Banned phrases (comma separated)
        <input name="banned_phrases" />
      </label>
      <label>
        Unique angle
        <textarea name="unique_angle" required />
      </label>
      <label>
        CTAs (comma separated)
        <input name="ctas" required />
      </label>
      <label>
        Proof points (comma separated)
        <input name="proof_points" />
      </label>
      <label>
        Messaging guardrails (comma separated)
        <input name="messaging_guardrails" />
      </label>
      <label>
        Compliance keywords (comma separated)
        <input name="compliance_keywords" />
      </label>
      <label>
        Image subject hints
        <textarea name="image_subject_hints" />
      </label>
      <label>
        Image palette
        <input name="image_palette" />
      </label>
      <label>
        Visual direction
        <textarea name="visual_direction" />
      </label>
      <button disabled={pending} type="submit">
        {pending ? "Submitting..." : "Submit manual profile"}
      </button>
      {error ? <p className="text-danger">{error}</p> : null}
    </form>
  );
}
