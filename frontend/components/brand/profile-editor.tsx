"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { patchProfile } from "@/lib/api";
import type { BrandProfileFull } from "@/lib/types";

function toCsv(values: string[] | null | undefined): string {
  return (values ?? []).join(", ");
}

function csvToArray(value: string): string[] {
  return value
    .split(",")
    .map((token) => token.trim())
    .filter(Boolean);
}

function arrEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

const STRING_FIELDS = ["one_liner", "tone_rules", "unique_angle"] as const;
const NULLABLE_STRING_FIELDS = [
  "image_palette",
  "image_subject_hints",
  "visual_direction",
  "logo_url",
] as const;
const CSV_FIELDS = [
  "allowed_topics",
  "audience_personas",
  "ctas",
  "disallowed_topics",
  "banned_phrases",
  "proof_points",
  "messaging_guardrails",
  "compliance_keywords",
] as const;

export function ProfileEditor({ profile }: { profile: BrandProfileFull }) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  function buildDiff(formData: FormData): Record<string, unknown> {
    const diff: Record<string, unknown> = {};
    for (const field of STRING_FIELDS) {
      const next = String(formData.get(field) ?? "").trim();
      if (next && next !== (profile[field] ?? "")) {
        diff[field] = next;
      }
    }
    for (const field of NULLABLE_STRING_FIELDS) {
      const raw = String(formData.get(field) ?? "").trim();
      const next = raw === "" ? null : raw;
      const current = profile[field] ?? null;
      if (next !== current) {
        diff[field] = next;
      }
    }
    for (const field of CSV_FIELDS) {
      const raw = formData.get(field);
      // If the field was not rendered (shouldn't happen), skip rather than wipe.
      if (raw === null) continue;
      const next = csvToArray(String(raw));
      const current = (profile[field] ?? []) as string[];
      if (!arrEqual(next, current)) {
        diff[field] = next;
      }
    }
    return diff;
  }

  async function onSubmit(formData: FormData) {
    const payload = buildDiff(formData);
    try {
      setPending(true);
      setError("");
      setMessage("");
      if (Object.keys(payload).length === 0) {
        setMessage("No changes to save.");
        return;
      }
      await patchProfile(profile.brand_id, payload);
      setMessage("Profile updated.");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to patch profile.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form action={onSubmit} className="card stack">
      <h3>[COGNITIVE_IDENTITY_EDITOR]</h3>
      <p className="meta">Editing is live only during PENDING_REVIEW. Save updates before locking.</p>
      <label>
        One liner
        <textarea defaultValue={profile.one_liner} name="one_liner" required />
      </label>
      <label>
        Tone rules
        <textarea defaultValue={profile.tone_rules} name="tone_rules" required />
      </label>
      <label>
        Unique angle
        <textarea defaultValue={profile.unique_angle} name="unique_angle" required />
      </label>
      <label>
        Allowed topics
        <input defaultValue={toCsv(profile.allowed_topics)} name="allowed_topics" />
      </label>
      <label>
        Audience personas
        <input defaultValue={toCsv(profile.audience_personas)} name="audience_personas" />
      </label>
      <label>
        CTAs
        <input defaultValue={toCsv(profile.ctas)} name="ctas" />
      </label>
      <label>
        Disallowed topics
        <input defaultValue={toCsv(profile.disallowed_topics)} name="disallowed_topics" />
      </label>
      <label>
        Banned phrases
        <input defaultValue={toCsv(profile.banned_phrases)} name="banned_phrases" />
      </label>
      <label>
        Proof points
        <input defaultValue={toCsv(profile.proof_points)} name="proof_points" />
      </label>
      <label>
        Messaging guardrails
        <input defaultValue={toCsv(profile.messaging_guardrails)} name="messaging_guardrails" />
      </label>
      <label>
        Compliance keywords
        <input defaultValue={toCsv(profile.compliance_keywords)} name="compliance_keywords" />
      </label>
      <label>
        Image palette
        <input defaultValue={profile.image_palette ?? ""} name="image_palette" />
      </label>
      <label>
        Image subject hints
        <textarea defaultValue={profile.image_subject_hints ?? ""} name="image_subject_hints" />
      </label>
      <label>
        Visual direction
        <textarea defaultValue={profile.visual_direction ?? ""} name="visual_direction" />
      </label>
      <label>
        Logo URL
        <input
          type="url"
          defaultValue={profile.logo_url ?? ""}
          name="logo_url"
          placeholder="https://yourbrand.com/logo.png"
        />
      </label>
      <button disabled={pending} type="submit">
        {pending ? "Saving..." : "Save profile"}
      </button>
      {message ? <p className="text-success" role="status" aria-live="polite">{message}</p> : null}
      {error ? <p className="text-danger" role="alert" aria-live="assertive">{error}</p> : null}
    </form>
  );
}
