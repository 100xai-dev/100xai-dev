from app.models import BrandKnowledgeSource
from app.schemas.brand_profile import BrandProfileContent


def materialize_manual_sources(brand_id: str, profile: BrandProfileContent) -> list[BrandKnowledgeSource]:
    sources = [
        BrandKnowledgeSource(
            brand_id=brand_id,
            source_type="manual_form_field",
            title="Tone Rules",
            raw_text=profile.tone_rules,
            normalized_text=profile.tone_rules,
            metadata_json={"field": "tone_rules"},
            word_count=len(profile.tone_rules.split()),
        ),
        BrandKnowledgeSource(
            brand_id=brand_id,
            source_type="manual_form_field",
            title="Unique Angle",
            raw_text=profile.unique_angle,
            normalized_text=profile.unique_angle,
            metadata_json={"field": "unique_angle"},
            word_count=len(profile.unique_angle.split()),
        ),
        BrandKnowledgeSource(
            brand_id=brand_id,
            source_type="manual_form_field",
            title="One-Liner",
            raw_text=profile.one_liner,
            normalized_text=profile.one_liner,
            metadata_json={"field": "one_liner"},
            word_count=len(profile.one_liner.split()),
        ),
    ]

    for index, persona in enumerate(profile.audience_personas):
        if len(persona) >= 20:
            sources.append(
                BrandKnowledgeSource(
                    brand_id=brand_id,
                    source_type="manual_form_field",
                    title=f"Audience Persona {index + 1}",
                    raw_text=persona,
                    normalized_text=persona,
                    metadata_json={"field": "audience_personas", "index": index},
                    word_count=len(persona.split()),
                )
            )

    for index, proof in enumerate(profile.proof_points):
        if len(proof) >= 20:
            sources.append(
                BrandKnowledgeSource(
                    brand_id=brand_id,
                    source_type="manual_form_field",
                    title=f"Proof Point {index + 1}",
                    raw_text=proof,
                    normalized_text=proof,
                    metadata_json={"field": "proof_points", "index": index},
                    word_count=len(proof.split()),
                )
            )

    if profile.messaging_guardrails:
        joined = "\n".join(f"- {guardrail}" for guardrail in profile.messaging_guardrails)
        sources.append(
            BrandKnowledgeSource(
                brand_id=brand_id,
                source_type="manual_form_field",
                title="Messaging Guardrails",
                raw_text=joined,
                normalized_text=joined,
                metadata_json={"field": "messaging_guardrails"},
                word_count=len(joined.split()),
            )
        )

    return sources

