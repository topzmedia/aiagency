"""
Variant Engine — the core combinatorial engine.

Assembles planned CreativeVariant records from all available components:
hooks, rotated hooks, scripts, script variants, avatars, B-roll clips, and images.

Does NOT render video — it produces PENDING variant plans which downstream
render/assembly stages consume.
"""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models.enums import AssetStatus, CreativeType
from ..models.schemas import (
    AvatarMetadata,
    BRollClip,
    CreativeVariant,
    Hook,
    ImageCreative,
    RotatedHook,
    Script,
    ScriptVariant,
)
from ..utils.config import AppConfig
from ..utils.dedupe import MetadataDedupe
from ..utils.io import ensure_dir, write_models_json
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("variant_engine")

# ---------------------------------------------------------------------------
# Per-batch quota defaults (can be overridden from config)
# ---------------------------------------------------------------------------

_DEFAULT_MAX_SAME_HOOK = 10
_DEFAULT_MAX_SAME_AVATAR = 8
_DEFAULT_MAX_SAME_SCRIPT = 5
_DEFAULT_BROLL_PACK_SIZE = 3
_DEFAULT_ROTATED_WEIGHT = 0.6   # Probability of using a rotated hook instead of parent


class VariantEngine:
    """Assembles combinatorial creative variant plans from ad components."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Main planning entry point
    # ------------------------------------------------------------------

    def plan_variants(
        self,
        run_id: str,
        offer,                              # OfferConfig — avoid circular import
        hooks: List[Hook],
        rotated_hooks: List[RotatedHook],
        scripts: List[Script],
        script_variants: List[ScriptVariant],
        avatars: List[AvatarMetadata],
        broll_clips: List[BRollClip],
        images: List[ImageCreative],
        max_variants: int = 500,
    ) -> List[CreativeVariant]:
        """
        Generate a list of PENDING CreativeVariant records without rendering.

        Strategy
        --------
        1. Build a hook pool mixing rotated + parent hooks at the configured weight.
        2. Build a script pool mixing scripts + script variants.
        3. Pair hooks × scripts × avatars with shuffle + deduplication.
        4. Apply per-component quotas.
        5. Append image variants (hook + image + CTA).
        6. Cap at max_variants.
        7. Save plan to intermediate/variant_plan_{run_id}.json.

        Returns a list of planned variants with status=PENDING.
        """
        variant_cfg = self.config.variants
        max_same_hook = getattr(variant_cfg, "max_same_hook_in_batch", _DEFAULT_MAX_SAME_HOOK)
        max_same_avatar = getattr(variant_cfg, "max_same_avatar_in_batch", _DEFAULT_MAX_SAME_AVATAR)
        max_same_script = getattr(variant_cfg, "max_same_script_in_batch", _DEFAULT_MAX_SAME_SCRIPT)
        rotated_weight = getattr(variant_cfg, "use_rotated_hooks_weight", _DEFAULT_ROTATED_WEIGHT)
        use_broll_weight = getattr(variant_cfg, "use_broll_weight", 0.7)

        offer_name = getattr(offer, "offer_name", "")

        logger.info(
            "VariantEngine.plan_variants: run_id=%s hooks=%d rotated=%d scripts=%d "
            "variants=%d avatars=%d broll=%d images=%d max=%d",
            run_id, len(hooks), len(rotated_hooks), len(scripts),
            len(script_variants), len(avatars), len(broll_clips), len(images), max_variants,
        )

        # ------------------------------------------------------------------
        # Step 1: Build hook pool with rotated-hook mixing
        # ------------------------------------------------------------------
        hook_pool: List[Tuple[Optional[Hook], Optional[RotatedHook]]] = []

        # Index rotated hooks by parent_hook_id for fast lookup
        rotated_by_parent: Dict[str, List[RotatedHook]] = {}
        for rh in rotated_hooks:
            rotated_by_parent.setdefault(rh.parent_hook_id, []).append(rh)

        for hook in hooks:
            has_rotated = hook.hook_id in rotated_by_parent
            if has_rotated and random.random() < rotated_weight:
                # Pick one rotated variant for this hook
                chosen_rotated = random.choice(rotated_by_parent[hook.hook_id])
                hook_pool.append((hook, chosen_rotated))
            else:
                hook_pool.append((hook, None))

        # Also add orphan rotated hooks whose parent is not in hooks list
        parent_ids_in_hooks = {h.hook_id for h in hooks}
        for rh in rotated_hooks:
            if rh.parent_hook_id not in parent_ids_in_hooks:
                hook_pool.append((None, rh))

        # ------------------------------------------------------------------
        # Step 2: Build script pool
        # ------------------------------------------------------------------
        script_pool: List[Tuple[Optional[Script], Optional[ScriptVariant]]] = []
        for s in scripts:
            script_pool.append((s, None))
        for sv in script_variants:
            script_pool.append((None, sv))

        # ------------------------------------------------------------------
        # Step 3: Shuffle all pools for variety
        # ------------------------------------------------------------------
        random.shuffle(hook_pool)
        random.shuffle(script_pool)
        avatar_pool = list(avatars)
        random.shuffle(avatar_pool)
        broll_pool = list(broll_clips)
        random.shuffle(broll_pool)

        # ------------------------------------------------------------------
        # Step 4: Build VIDEO variants
        # ------------------------------------------------------------------
        dedupe = MetadataDedupe(key_fields=["hook_id", "avatar_id", "script_id"])
        variants: List[CreativeVariant] = []
        counts = self._count_per_component([])  # start empty

        video_budget = max(1, int(max_variants * 0.75))  # 75% video, 25% image
        image_budget = max_variants - video_budget

        if not avatar_pool:
            logger.warning("VariantEngine: no avatars provided — video variants will be skipped")

        if avatar_pool and (hook_pool or script_pool):
            sp_idx = 0
            avatar_idx = 0
            for hp_idx, (hook, rotated_hook) in enumerate(hook_pool):
                if len(variants) >= video_budget:
                    break

                # Derive canonical IDs for quota checks
                effective_hook_id = (
                    rotated_hook.parent_hook_id if rotated_hook else (hook.hook_id if hook else "")
                )
                hook_text = (
                    rotated_hook.text if rotated_hook else (hook.text if hook else "")
                )

                # Get script from pool
                script, script_variant = script_pool[sp_idx % len(script_pool)]
                sp_idx += 1

                script_id = script.script_id if script else (
                    script_variant.parent_script_id if script_variant else ""
                )
                script_variant_id = script_variant.variant_id if script_variant else None

                # Get avatar from pool
                avatar = avatar_pool[avatar_idx % len(avatar_pool)]
                avatar_idx += 1

                # Quota guard
                current_counts = self._count_per_component(variants)
                hook_count = current_counts["hook_id"].get(effective_hook_id, 0)
                avatar_count = current_counts["avatar_id"].get(avatar.avatar_id, 0)
                script_count = current_counts["script_id"].get(script_id, 0)

                if hook_count >= max_same_hook:
                    continue
                if avatar_count >= max_same_avatar:
                    # Try next avatar
                    found = False
                    for av in avatar_pool:
                        av_count = current_counts["avatar_id"].get(av.avatar_id, 0)
                        if av_count < max_same_avatar:
                            avatar = av
                            found = True
                            break
                    if not found:
                        continue
                if script_count >= max_same_script:
                    continue

                # Dedupe check
                record = {
                    "hook_id": effective_hook_id,
                    "avatar_id": avatar.avatar_id,
                    "script_id": script_id,
                }
                if not dedupe.add(record):
                    continue

                # Decide whether to include B-roll
                broll_ids: List[str] = []
                if broll_pool and random.random() < use_broll_weight:
                    broll_ids = self.select_random_broll_pack(broll_pool, count=_DEFAULT_BROLL_PACK_SIZE)

                variant = CreativeVariant(
                    run_id=run_id,
                    creative_type=CreativeType.TALKING_HEAD,
                    hook_id=effective_hook_id if effective_hook_id else None,
                    rotated_hook_id=rotated_hook.rotated_id if rotated_hook else None,
                    script_id=script_id if script_id else None,
                    script_variant_id=script_variant_id,
                    avatar_id=avatar.avatar_id,
                    broll_ids=broll_ids,
                    status=AssetStatus.PENDING,
                    hook_text=hook_text,
                    offer_name=offer_name,
                )
                variants.append(variant)

        # ------------------------------------------------------------------
        # Step 5: Build IMAGE variants
        # ------------------------------------------------------------------
        if images and hook_pool:
            img_dedupe = MetadataDedupe(key_fields=["hook_id", "image_id"])
            img_pool = list(images)
            random.shuffle(img_pool)

            for img_idx, image in enumerate(img_pool):
                if len(variants) >= max_variants:
                    break
                if img_idx >= image_budget:
                    break

                hp_idx = img_idx % len(hook_pool)
                hook, rotated_hook = hook_pool[hp_idx]

                effective_hook_id = (
                    rotated_hook.parent_hook_id if rotated_hook else (hook.hook_id if hook else "")
                )
                hook_text = (
                    rotated_hook.text if rotated_hook else (hook.text if hook else "")
                )

                record = {
                    "hook_id": effective_hook_id,
                    "image_id": image.image_id,
                }
                if not img_dedupe.add(record):
                    continue

                img_variant = CreativeVariant(
                    run_id=run_id,
                    creative_type=CreativeType.STATIC_IMAGE,
                    hook_id=effective_hook_id if effective_hook_id else None,
                    rotated_hook_id=rotated_hook.rotated_id if rotated_hook else None,
                    image_id=image.image_id,
                    status=AssetStatus.PENDING,
                    hook_text=hook_text,
                    offer_name=offer_name,
                )
                variants.append(img_variant)

        # ------------------------------------------------------------------
        # Step 6: Final cap + shuffle
        # ------------------------------------------------------------------
        random.shuffle(variants)
        variants = variants[:max_variants]

        logger.info(
            "VariantEngine: planned %d variants (%d video, %d image) | dedupe_rejected=%d",
            len(variants),
            sum(1 for v in variants if v.creative_type != CreativeType.STATIC_IMAGE),
            sum(1 for v in variants if v.creative_type == CreativeType.STATIC_IMAGE),
            dedupe.rejected,
        )

        # ------------------------------------------------------------------
        # Step 7: Persist plan
        # ------------------------------------------------------------------
        self._save_plan(variants, run_id)

        return variants

    # ------------------------------------------------------------------
    # B-roll pack selection
    # ------------------------------------------------------------------

    def select_random_broll_pack(
        self,
        clips: List[BRollClip],
        count: int = 3,
    ) -> List[str]:
        """
        Select `count` B-roll clip IDs at random (without replacement if possible).
        Returns a list of broll_id strings.
        """
        if not clips:
            return []
        n = min(count, len(clips))
        selected = random.sample(clips, n)
        return [clip.broll_id for clip in selected]

    # ------------------------------------------------------------------
    # Count per component (for quota enforcement)
    # ------------------------------------------------------------------

    def _count_per_component(
        self,
        variants: List[CreativeVariant],
    ) -> Dict[str, Dict[str, int]]:
        """
        Return usage counts keyed by component type and ID.

        Returns:
            {
                "hook_id":   {hook_id: count, ...},
                "avatar_id": {avatar_id: count, ...},
                "script_id": {script_id: count, ...},
            }
        """
        counts: Dict[str, Dict[str, int]] = {
            "hook_id": {},
            "avatar_id": {},
            "script_id": {},
        }
        for v in variants:
            if v.hook_id:
                counts["hook_id"][v.hook_id] = counts["hook_id"].get(v.hook_id, 0) + 1
            if v.avatar_id:
                counts["avatar_id"][v.avatar_id] = counts["avatar_id"].get(v.avatar_id, 0) + 1
            if v.script_id:
                counts["script_id"][v.script_id] = counts["script_id"].get(v.script_id, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_plan(self, variants: List[CreativeVariant], run_id: str) -> None:
        """Persist the variant plan JSON to the intermediate directory."""
        intermediate_dir = Path(self.config.base_data_dir) / "intermediate"
        ensure_dir(intermediate_dir)
        plan_path = intermediate_dir / f"variant_plan_{run_id}.json"
        try:
            write_models_json(variants, plan_path)
            logger.info("VariantEngine: saved variant plan → %s", plan_path)
        except Exception as exc:
            logger.error("VariantEngine: failed to save variant plan: %s", exc)
