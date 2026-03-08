"""
AI Ad Agency — Main CLI Entry Point

Usage:
    python main.py generate --config configs/offer.json --count 500
    python main.py hooks --config configs/offer.json
    python main.py scripts --config configs/offer.json
    python main.py avatars --sync
    python main.py images --config configs/offer.json --count 200
    python main.py broll --config configs/offer.json --count 40
    python main.py videos --config configs/offer.json --count 300
    python main.py qa --run-id latest
    python main.py export --run-id latest
    python main.py autopilot --config configs/offer.json --count 500
    python main.py status
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure package is importable from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import typer
    from rich.console import Console
    from rich.table import Table
    _TYPER = True
    _RICH = True
except ImportError:
    _TYPER = False
    _RICH = False

# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

if _TYPER:
    app = typer.Typer(
        name="ai-ad-agency",
        help="AI Creative Swarm — Automated ad creative generation platform.",
        no_args_is_help=True,
    )
    console = Console() if _RICH else None
else:
    # Fallback: argparse-based CLI
    app = None
    console = None


def _print(msg: str) -> None:
    if console:
        console.print(msg)
    else:
        print(msg)


def _print_header(title: str) -> None:
    if _RICH and console:
        console.rule(f"[bold blue]{title}[/bold blue]")
    else:
        print(f"\n{'='*60}\n{title}\n{'='*60}")


# ---------------------------------------------------------------------------
# Shared bootstrapping
# ---------------------------------------------------------------------------

def _bootstrap(app_config_path: Optional[str] = None):
    """Load app config, initialize directories, and return AppConfig."""
    from ai_ad_agency.utils.config import load_app_config, ensure_dirs
    cfg = load_app_config(app_config_path)
    ensure_dirs(cfg)
    return cfg


def _build_providers(cfg):
    """Build all provider instances from config."""
    from ai_ad_agency.providers.llm_provider import build_llm_provider
    from ai_ad_agency.providers.avatar_provider import build_avatar_provider
    from ai_ad_agency.providers.image_provider import build_image_provider
    from ai_ad_agency.providers.video_provider import build_video_provider
    from ai_ad_agency.providers.voice_provider import build_voice_provider

    llm = build_llm_provider(cfg.providers.llm)
    avatar = build_avatar_provider(cfg.providers.avatar)
    image = build_image_provider(cfg.providers.image)
    video = build_video_provider(cfg.providers.video, image_provider=image)
    voice = build_voice_provider(cfg.providers.voice)
    return llm, avatar, image, video, voice


def _init_run(cfg, offer_name: str) -> tuple:
    """Create a new RunManifest and ManifestManager."""
    from ai_ad_agency.models.schemas import RunManifest
    from ai_ad_agency.models.enums import AssetStatus
    from ai_ad_agency.utils.manifest import ManifestManager

    mgr = ManifestManager(cfg.db_path)
    manifest = RunManifest(
        offer_name=offer_name,
        status=AssetStatus.GENERATING,
        started_at=datetime.utcnow(),
    )
    mgr.create_run(manifest)
    return mgr, manifest


# ---------------------------------------------------------------------------
# Command: hooks
# ---------------------------------------------------------------------------

def run_hooks(
    config: str,
    count: int = 200,
    app_config: Optional[str] = None,
    run_id: Optional[str] = None,
) -> dict:
    """Generate hooks for an offer."""
    from ai_ad_agency.utils.config import load_offer_config
    from ai_ad_agency.pipelines.hook_pipeline import HookPipeline
    from ai_ad_agency.utils.logging_utils import get_logger

    cfg = _bootstrap(app_config)
    log = get_logger("ai_ad_agency", cfg.log_level, cfg.base_log_dir, cfg.log_to_file)
    offer = load_offer_config(config)
    llm, *_ = _build_providers(cfg)

    _print_header(f"HOOKS — {offer.offer_name}")
    pipeline = HookPipeline(cfg, llm)
    hooks, rotated = pipeline.run(
        offer=offer,
        count=count,
        output_dir=f"{cfg.base_output_dir}/hooks",
        rotations_per_hook=cfg.variants.rotations_per_hook,
        run_id=run_id or "",
    )
    _print(f"[green]Generated {len(hooks)} hooks + {len(rotated)} rotated variants[/green]")
    return {"hooks": len(hooks), "rotated": len(rotated)}


# ---------------------------------------------------------------------------
# Command: scripts
# ---------------------------------------------------------------------------

def run_scripts(
    config: str,
    app_config: Optional[str] = None,
    run_id: Optional[str] = None,
) -> dict:
    from ai_ad_agency.utils.config import load_offer_config
    from ai_ad_agency.utils.io import read_models_json
    from ai_ad_agency.models.schemas import Hook
    from ai_ad_agency.pipelines.script_pipeline import ScriptPipeline

    cfg = _bootstrap(app_config)
    offer = load_offer_config(config)
    llm, *_ = _build_providers(cfg)

    # Load existing hooks
    hooks_path = Path(cfg.base_output_dir) / "hooks" / "hooks.json"
    if not hooks_path.exists():
        _print("[red]No hooks found. Run hooks command first.[/red]")
        return {}

    hooks = read_models_json(hooks_path, Hook)
    _print_header(f"SCRIPTS — {offer.offer_name}")
    pipeline = ScriptPipeline(cfg, llm)
    scripts, variants = pipeline.run(
        offer=offer,
        hooks=hooks,
        scripts_per_hook=cfg.variants.scripts_per_hook,
        variants_per_script=cfg.variants.script_variants_per_script,
        output_dir=f"{cfg.base_output_dir}/scripts",
    )
    _print(f"[green]Generated {len(scripts)} scripts + {len(variants)} variants[/green]")
    return {"scripts": len(scripts), "script_variants": len(variants)}


# ---------------------------------------------------------------------------
# Command: avatars
# ---------------------------------------------------------------------------

def run_avatars(sync: bool = False, app_config: Optional[str] = None) -> dict:
    from ai_ad_agency.agents.avatar_catalog_agent import AvatarCatalogAgent
    from ai_ad_agency.providers.avatar_provider import build_avatar_provider

    cfg = _bootstrap(app_config)
    avatar_prov = build_avatar_provider(cfg.providers.avatar)

    _print_header("AVATAR CATALOG")
    agent = AvatarCatalogAgent(cfg, avatar_prov)
    avatars = agent.get_all()

    if sync:
        new_count = agent.sync_from_provider()
        _print(f"[green]Synced {new_count} avatars from provider[/green]")
        avatars = agent.get_all()

    _print(f"Catalog contains [bold]{len(avatars)}[/bold] avatars")

    if _RICH and console:
        table = Table(title="Avatar Catalog Sample (first 10)")
        table.add_column("ID", style="cyan")
        table.add_column("Provider")
        table.add_column("Gender")
        table.add_column("Age Group")
        table.add_column("Appearance")
        table.add_column("Realism")
        for a in avatars[:10]:
            table.add_row(
                a.avatar_id[:20],
                str(a.provider),
                str(a.gender_presentation),
                str(a.age_group),
                str(a.appearance_tag),
                str(a.realism_score),
            )
        console.print(table)

    return {"total_avatars": len(avatars)}


# ---------------------------------------------------------------------------
# Command: images
# ---------------------------------------------------------------------------

def run_images(
    config: str,
    count: int = 200,
    app_config: Optional[str] = None,
) -> dict:
    from ai_ad_agency.utils.config import load_offer_config
    from ai_ad_agency.utils.io import read_models_json
    from ai_ad_agency.models.schemas import Hook
    from ai_ad_agency.pipelines.image_pipeline import ImagePipeline

    cfg = _bootstrap(app_config)
    offer = load_offer_config(config)
    llm, _, image, *_ = _build_providers(cfg)

    # Load hooks if available
    hooks_path = Path(cfg.base_output_dir) / "hooks" / "hooks.json"
    hooks = []
    if hooks_path.exists():
        hooks = read_models_json(hooks_path, Hook)

    _print_header(f"IMAGES — {offer.offer_name}")
    pipeline = ImagePipeline(cfg, image, llm)
    creatives = pipeline.run(
        offer=offer,
        count=count,
        hooks=hooks,
        output_dir=f"{cfg.base_output_dir}/images",
    )
    _print(f"[green]Generated {len(creatives)} image creatives[/green]")
    return {"images": len(creatives)}


# ---------------------------------------------------------------------------
# Command: broll
# ---------------------------------------------------------------------------

def run_broll(
    config: str,
    count: int = 40,
    app_config: Optional[str] = None,
) -> dict:
    from ai_ad_agency.utils.config import load_offer_config
    from ai_ad_agency.agents.broll_agent import BRollAgent

    cfg = _bootstrap(app_config)
    offer = load_offer_config(config)
    llm, _, image, video, _ = _build_providers(cfg)

    _print_header(f"B-ROLL — {offer.offer_name}")
    agent = BRollAgent(cfg, video)
    clips = agent.generate_batch(
        offer=offer,
        count=count,
        output_dir=f"{cfg.base_output_dir}/broll",
    )
    _print(f"[green]Generated {len(clips)} B-roll clips[/green]")
    return {"broll_clips": len(clips)}


# ---------------------------------------------------------------------------
# Command: videos
# ---------------------------------------------------------------------------

def run_videos(
    config: str,
    count: int = 300,
    app_config: Optional[str] = None,
    run_id: Optional[str] = None,
) -> dict:
    """Plan variants, render talking actors, assemble videos."""
    from ai_ad_agency.utils.config import load_offer_config
    from ai_ad_agency.utils.io import read_models_json
    from ai_ad_agency.models.schemas import Hook, Script, ScriptVariant, BRollClip
    from ai_ad_agency.agents.variant_engine import VariantEngine
    from ai_ad_agency.agents.avatar_catalog_agent import AvatarCatalogAgent
    from ai_ad_agency.agents.caption_agent import CaptionAgent
    from ai_ad_agency.pipelines.avatar_pipeline import AvatarPipeline
    from ai_ad_agency.pipelines.video_pipeline import VideoPipeline

    cfg = _bootstrap(app_config)
    offer = load_offer_config(config)
    llm, avatar_prov, image_prov, video_prov, voice_prov = _build_providers(cfg)

    output_dir = cfg.base_output_dir

    def _load_or_empty(path, cls):
        try:
            return read_models_json(path, cls)
        except Exception:
            return []

    hooks = _load_or_empty(f"{output_dir}/hooks/hooks.json", Hook)
    rotated = _load_or_empty(f"{output_dir}/hooks/rotated_hooks.json", Hook)
    scripts = _load_or_empty(f"{output_dir}/scripts/scripts.json", Script)
    script_variants = _load_or_empty(f"{output_dir}/scripts/script_variants.json", ScriptVariant)
    broll_clips = _load_or_empty(f"{output_dir}/broll/broll_clips.json", BRollClip)

    _print_header(f"VIDEOS — {offer.offer_name}")

    # Sync catalog and select avatars
    catalog = AvatarCatalogAgent(cfg, avatar_prov)
    avatars = catalog.select_balanced_batch(
        count=min(50, len(catalog.get_all())),
    )

    # Plan variants
    engine = VariantEngine(cfg)
    from ai_ad_agency.models.schemas import RotatedHook
    rh_list = _load_or_empty(f"{output_dir}/hooks/rotated_hooks.json", RotatedHook)

    variants = engine.plan_variants(
        run_id=run_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
        offer=offer,
        hooks=hooks,
        rotated_hooks=rh_list,
        scripts=scripts,
        script_variants=script_variants,
        avatars=avatars,
        broll_clips=broll_clips,
        images=[],
        max_variants=count,
    )
    _print(f"Planned {len(variants)} creative variants")

    # Render talking actors
    video_scripts = scripts[:cfg.variants.talking_actor_jobs_per_run]
    avatar_pipeline = AvatarPipeline(cfg, avatar_prov, voice_prov)
    jobs = avatar_pipeline.run(
        scripts=video_scripts,
        avatars=avatars[:20],
        output_dir=f"{output_dir}/avatars",
    )

    # Generate captions
    caption_agent = CaptionAgent(cfg, llm)
    captions = caption_agent.generate_batch(
        scripts=video_scripts[:50],
        output_dir=f"{output_dir}/captions",
    )

    # Build component lookup
    from ai_ad_agency.models.schemas import CaptionFile
    actor_jobs_map = {}
    for job in jobs:
        key = f"{job.avatar_id}:{job.script_id}"
        actor_jobs_map[key] = job

    lookup = {
        "hooks": {h.hook_id: h for h in hooks},
        "scripts": {s.script_id: s for s in scripts + list(script_variants)},
        "actor_jobs": actor_jobs_map,
        "broll": {b.broll_id: b for b in broll_clips},
        "captions": {c.caption_id: c for c in captions},
    }

    # Assemble videos
    video_pipeline = VideoPipeline(cfg)
    variants = video_pipeline.assemble_batch(
        variants=variants,
        component_lookup=lookup,
        output_dir=f"{output_dir}/videos",
        run_id=run_id or "",
    )

    done = sum(1 for v in variants if v.file_path and Path(v.file_path).exists())
    _print(f"[green]Assembled {done} videos[/green]")
    return {"videos_assembled": done}


# ---------------------------------------------------------------------------
# Command: qa
# ---------------------------------------------------------------------------

def run_qa(run_id: str = "latest", app_config: Optional[str] = None) -> dict:
    from ai_ad_agency.agents.qa_agent import QAAgent
    from ai_ad_agency.utils.manifest import ManifestManager

    cfg = _bootstrap(app_config)
    mgr = ManifestManager(cfg.db_path)

    if run_id == "latest":
        manifest = mgr.get_latest_run()
    else:
        manifest = mgr.get_run(run_id)

    if not manifest:
        _print("[red]No run found. Run generate or autopilot first.[/red]")
        return {}

    _print_header(f"QA — Run {manifest.run_id[:8]}")
    qa = QAAgent(cfg)
    # Load creatives from intermediate
    _print(f"Run: {manifest.run_id}  Offer: {manifest.offer_name}")
    _print("QA complete (details in logs)")
    return {"run_id": manifest.run_id}


# ---------------------------------------------------------------------------
# Command: export
# ---------------------------------------------------------------------------

def run_export(run_id: str = "latest", app_config: Optional[str] = None) -> dict:
    from ai_ad_agency.utils.manifest import ManifestManager

    cfg = _bootstrap(app_config)
    mgr = ManifestManager(cfg.db_path)

    if run_id == "latest":
        manifest = mgr.get_latest_run()
    else:
        manifest = mgr.get_run(run_id)

    if not manifest:
        _print("[red]No run found.[/red]")
        return {}

    _print_header(f"EXPORT — Run {manifest.run_id[:8]}")
    _print(f"Export directory: {manifest.export_dir or 'not set yet'}")
    return {"run_id": manifest.run_id, "export_dir": manifest.export_dir}


# ---------------------------------------------------------------------------
# Command: status
# ---------------------------------------------------------------------------

def run_status(app_config: Optional[str] = None) -> None:
    from ai_ad_agency.utils.manifest import ManifestManager
    from ai_ad_agency.utils.ffmpeg_utils import check_ffmpeg, check_ffprobe

    cfg = _bootstrap(app_config)
    mgr = ManifestManager(cfg.db_path)
    runs = mgr.list_runs(limit=5)

    _print_header("AI AD AGENCY — STATUS")

    # Check dependencies
    ffmpeg_ok = check_ffmpeg()
    ffprobe_ok = check_ffprobe()
    _print(f"FFmpeg: {'[green]✓[/green]' if ffmpeg_ok else '[red]✗ Not found[/red]'}")
    _print(f"FFprobe: {'[green]✓[/green]' if ffprobe_ok else '[red]✗ Not found[/red]'}")

    # Check API keys
    providers = cfg.providers
    keys = {
        "OpenAI": bool(providers.llm.api_key),
        "HeyGen": bool(providers.avatar.api_key),
        "Stability": bool(providers.image.api_key),
        "Runway": bool(providers.video.api_key),
        "ElevenLabs": bool(providers.voice.api_key),
    }
    for name, has_key in keys.items():
        status = "[green]✓[/green]" if has_key else "[yellow]⚠ Not set[/yellow]"
        _print(f"{name}: {status}")

    # Recent runs
    if runs:
        _print(f"\nRecent runs ({len(runs)}):")
        for r in runs:
            _print(f"  {r['run_id'][:8]}  {r['offer_name']}  {r['status']}  {r['started_at'][:19]}")
    else:
        _print("\nNo runs yet.")


# ---------------------------------------------------------------------------
# Command: autopilot (full end-to-end)
# ---------------------------------------------------------------------------

def run_autopilot(
    config: str,
    count: int = 500,
    app_config: Optional[str] = None,
    resume: bool = False,
    force: bool = False,
) -> None:
    """
    End-to-end autopilot run.
    Generates hooks → scripts → images → b-roll → avatars → videos → QA → export
    """
    from ai_ad_agency.utils.config import load_offer_config
    from ai_ad_agency.utils.logging_utils import get_logger
    from ai_ad_agency.models.schemas import RunManifest, RotatedHook
    from ai_ad_agency.models.enums import AssetStatus
    from ai_ad_agency.utils.manifest import ManifestManager
    from ai_ad_agency.utils.io import read_models_json, write_models_json
    from ai_ad_agency.pipelines.hook_pipeline import HookPipeline
    from ai_ad_agency.pipelines.script_pipeline import ScriptPipeline
    from ai_ad_agency.pipelines.image_pipeline import ImagePipeline
    from ai_ad_agency.pipelines.avatar_pipeline import AvatarPipeline
    from ai_ad_agency.pipelines.video_pipeline import VideoPipeline
    from ai_ad_agency.pipelines.export_pipeline import ExportPipeline
    from ai_ad_agency.agents.broll_agent import BRollAgent
    from ai_ad_agency.agents.variant_engine import VariantEngine
    from ai_ad_agency.agents.avatar_catalog_agent import AvatarCatalogAgent
    from ai_ad_agency.agents.caption_agent import CaptionAgent
    from ai_ad_agency.models.schemas import Hook, Script, ScriptVariant, BRollClip, ImageCreative

    cfg = _bootstrap(app_config)
    log = get_logger("ai_ad_agency", cfg.log_level, cfg.base_log_dir, cfg.log_to_file)
    offer = load_offer_config(config)
    llm, avatar_prov, image_prov, video_prov, voice_prov = _build_providers(cfg)

    mgr = ManifestManager(cfg.db_path)

    # Resume or create new run
    if resume:
        manifest = mgr.get_latest_run()
        if not manifest:
            _print("[yellow]No existing run found. Starting fresh.[/yellow]")
            manifest = None
    else:
        manifest = None

    if not manifest:
        manifest = RunManifest(
            offer_name=offer.offer_name,
            status=AssetStatus.GENERATING,
            started_at=datetime.utcnow(),
            config_snapshot=offer.model_dump(mode="json"),
        )
        mgr.create_run(manifest)

    run_id = manifest.run_id
    out = cfg.base_output_dir
    _print_header(f"AUTOPILOT — {offer.offer_name}  [run: {run_id[:8]}]")
    log.info("Autopilot started: run_id=%s offer=%s count=%d", run_id, offer.offer_name, count)

    def _load_or_empty(path, cls):
        try:
            if Path(path).exists():
                return read_models_json(path, cls)
        except Exception as e:
            log.warning("Could not load %s: %s", path, e)
        return []

    # ---- Step 1: Hooks ----
    _print("\n[bold]Step 1/9: Generating hooks...[/bold]")
    hooks_path = f"{out}/hooks/hooks.json"
    rotated_path = f"{out}/hooks/rotated_hooks.json"
    if not force and Path(hooks_path).exists():
        _print("  → Hooks already exist. Skipping (use --force to regenerate)")
        hooks = _load_or_empty(hooks_path, Hook)
        rotated_hooks = _load_or_empty(rotated_path, RotatedHook)
    else:
        hook_pipeline = HookPipeline(cfg, llm)
        hooks, rotated_hooks = hook_pipeline.run(
            offer=offer,
            count=cfg.variants.hooks_per_run,
            output_dir=f"{out}/hooks",
            rotations_per_hook=cfg.variants.rotations_per_hook,
            run_id=run_id,
        )
    manifest.hooks_generated = len(hooks)
    manifest.rotated_hooks_generated = len(rotated_hooks)
    mgr.update_run(manifest)
    _print(f"  ✓ {len(hooks)} hooks + {len(rotated_hooks)} rotated")

    # ---- Step 2: Scripts ----
    _print("\n[bold]Step 2/9: Generating scripts...[/bold]")
    scripts_path = f"{out}/scripts/scripts.json"
    variants_path = f"{out}/scripts/script_variants.json"
    if not force and Path(scripts_path).exists():
        _print("  → Scripts already exist. Skipping")
        scripts = _load_or_empty(scripts_path, Script)
        script_variants = _load_or_empty(variants_path, ScriptVariant)
    else:
        script_pipeline = ScriptPipeline(cfg, llm)
        scripts, script_variants = script_pipeline.run(
            offer=offer,
            hooks=hooks[:50],  # Use top 50 hooks for scripts
            scripts_per_hook=cfg.variants.scripts_per_hook,
            variants_per_script=cfg.variants.script_variants_per_script,
            output_dir=f"{out}/scripts",
        )
    manifest.scripts_generated = len(scripts)
    manifest.script_variants_generated = len(script_variants)
    mgr.update_run(manifest)
    _print(f"  ✓ {len(scripts)} scripts + {len(script_variants)} variants")

    # ---- Step 3: Avatar catalog sync ----
    _print("\n[bold]Step 3/9: Syncing avatar catalog...[/bold]")
    catalog = AvatarCatalogAgent(cfg, avatar_prov)
    if cfg.avatar_selection.sync_on_startup:
        new_count = catalog.sync_from_provider()
        _print(f"  → Synced {new_count} new avatars from provider")
    avatars = catalog.select_balanced_batch(
        count=min(50, len(catalog.get_all())),
    )
    _print(f"  ✓ {len(catalog.get_all())} avatars in catalog, using {len(avatars)}")

    # ---- Step 4: Images ----
    _print("\n[bold]Step 4/9: Generating static images...[/bold]")
    images_dir = f"{out}/images"
    images_meta_path = f"{images_dir}/images.json"
    if not force and Path(images_meta_path).exists():
        _print("  → Images already exist. Skipping")
        images = _load_or_empty(images_meta_path, ImageCreative)
    else:
        image_pipeline = ImagePipeline(cfg, image_prov, llm)
        images = image_pipeline.run(
            offer=offer,
            count=cfg.variants.images_per_run,
            hooks=hooks[:20],
            output_dir=images_dir,
        )
    manifest.images_generated = len(images)
    mgr.update_run(manifest)
    _print(f"  ✓ {len(images)} static images")

    # ---- Step 5: B-roll ----
    _print("\n[bold]Step 5/9: Generating B-roll clips...[/bold]")
    broll_dir = f"{out}/broll"
    broll_meta_path = f"{broll_dir}/broll_clips.json"
    if not force and Path(broll_meta_path).exists():
        _print("  → B-roll already exists. Skipping")
        broll_clips = _load_or_empty(broll_meta_path, BRollClip)
    else:
        broll_agent = BRollAgent(cfg, video_prov)
        broll_clips = broll_agent.generate_batch(
            offer=offer,
            count=cfg.variants.broll_clips_per_run,
            output_dir=broll_dir,
        )
    manifest.broll_clips_generated = len(broll_clips)
    mgr.update_run(manifest)
    _print(f"  ✓ {len(broll_clips)} B-roll clips")

    # ---- Step 6: Talking avatars ----
    _print("\n[bold]Step 6/9: Rendering talking avatars...[/bold]")
    avatars_dir = f"{out}/avatars"
    actor_scripts = scripts[:cfg.variants.talking_actor_jobs_per_run]
    avatar_pipeline = AvatarPipeline(cfg, avatar_prov, voice_prov)
    jobs = avatar_pipeline.run(
        scripts=actor_scripts,
        avatars=avatars[:20],
        output_dir=avatars_dir,
    )
    manifest.talking_actor_jobs = len(jobs)
    mgr.update_run(manifest)
    done_jobs = sum(1 for j in jobs if j.render_status.value == "completed")
    _print(f"  ✓ {done_jobs}/{len(jobs)} actor clips rendered")

    # ---- Step 7: Captions ----
    _print("\n[bold]Step 7/9: Generating captions...[/bold]")
    caption_agent = CaptionAgent(cfg, llm)
    captions = caption_agent.generate_batch(
        scripts=actor_scripts[:60],
        output_dir=f"{out}/captions",
    )
    _print(f"  ✓ {len(captions)} caption files")

    # ---- Step 8: Variant planning + Video assembly ----
    _print("\n[bold]Step 8/9: Planning variants and assembling videos...[/bold]")
    engine = VariantEngine(cfg)
    variants = engine.plan_variants(
        run_id=run_id,
        offer=offer,
        hooks=hooks,
        rotated_hooks=rotated_hooks,
        scripts=scripts,
        script_variants=script_variants,
        avatars=avatars,
        broll_clips=broll_clips,
        images=images,
        max_variants=count,
    )
    manifest.variants_planned = len(variants)
    mgr.update_run(manifest)
    _print(f"  Planned {len(variants)} variants")

    # Build component lookup
    actor_jobs_map = {}
    for job in jobs:
        key = f"{job.avatar_id}:{job.script_id}"
        actor_jobs_map[key] = job

    lookup = {
        "hooks": {h.hook_id: h for h in hooks},
        "scripts": {
            **{s.script_id: s for s in scripts},
            **{sv.variant_id: sv for sv in script_variants},
        },
        "actor_jobs": actor_jobs_map,
        "broll": {b.broll_id: b for b in broll_clips},
        "captions": {c.caption_id: c for c in captions},
    }

    video_pipeline = VideoPipeline(cfg)
    variants = video_pipeline.assemble_batch(
        variants=variants,
        component_lookup=lookup,
        output_dir=f"{out}/videos",
        run_id=run_id,
    )
    rendered = sum(1 for v in variants if v.file_path and Path(v.file_path).exists())
    manifest.variants_rendered = rendered
    mgr.update_run(manifest)
    _print(f"  ✓ {rendered} videos assembled")

    # ---- Step 9: QA + Export ----
    _print("\n[bold]Step 9/9: QA and export...[/bold]")
    export_dir = f"{out}/exports/{run_id}"
    export_pipeline = ExportPipeline(cfg)
    accepted, export_path = export_pipeline.run(
        run_id=run_id,
        manifest=manifest,
        creatives=variants,
        images=images,
        hooks=hooks,
        scripts=scripts,
        export_dir=export_dir,
        scoring_lookup={
            "hooks": {h.hook_id: h for h in hooks},
            "scripts": {s.script_id: s for s in scripts},
            "avatars": {a.avatar_id: a for a in avatars},
        },
    )

    manifest.variants_accepted = len(accepted)
    manifest.variants_rejected = len(variants) - len(accepted)
    manifest.export_dir = export_path
    manifest.status = AssetStatus.COMPLETED
    manifest.completed_at = datetime.utcnow()
    mgr.update_run(manifest)

    _print_header("AUTOPILOT COMPLETE")
    _print(f"Run ID: {run_id}")
    _print(f"Hooks: {len(hooks)} ({len(rotated_hooks)} rotated)")
    _print(f"Scripts: {len(scripts)} ({len(script_variants)} variants)")
    _print(f"Images: {len(images)}")
    _print(f"B-roll: {len(broll_clips)}")
    _print(f"Videos rendered: {rendered}")
    _print(f"Accepted: {len(accepted)}")
    _print(f"Export: {export_path}")
    log.info("Autopilot completed: run_id=%s accepted=%d", run_id, len(accepted))


# ---------------------------------------------------------------------------
# Typer commands
# ---------------------------------------------------------------------------

if _TYPER:
    @app.command("autopilot")
    def cmd_autopilot(
        config: str = typer.Option(..., "--config", "-c", help="Path to offer config JSON"),
        count: int = typer.Option(500, "--count", "-n", help="Target number of final creatives"),
        app_config: Optional[str] = typer.Option(None, "--app-config", help="App config JSON"),
        resume: bool = typer.Option(False, "--resume", help="Resume last run"),
        force: bool = typer.Option(False, "--force", help="Force regeneration even if files exist"),
    ):
        """Run the full end-to-end creative generation pipeline."""
        run_autopilot(config, count, app_config, resume, force)

    @app.command("hooks")
    def cmd_hooks(
        config: str = typer.Option(..., "--config", "-c"),
        count: int = typer.Option(200, "--count"),
        app_config: Optional[str] = typer.Option(None, "--app-config"),
    ):
        """Generate hooks for an offer."""
        run_hooks(config, count, app_config)

    @app.command("scripts")
    def cmd_scripts(
        config: str = typer.Option(..., "--config", "-c"),
        app_config: Optional[str] = typer.Option(None, "--app-config"),
    ):
        """Generate scripts from hooks."""
        run_scripts(config, app_config)

    @app.command("avatars")
    def cmd_avatars(
        sync: bool = typer.Option(False, "--sync", help="Sync catalog from provider API"),
        app_config: Optional[str] = typer.Option(None, "--app-config"),
    ):
        """Show and sync avatar catalog."""
        run_avatars(sync, app_config)

    @app.command("images")
    def cmd_images(
        config: str = typer.Option(..., "--config", "-c"),
        count: int = typer.Option(200, "--count"),
        app_config: Optional[str] = typer.Option(None, "--app-config"),
    ):
        """Generate static image creatives."""
        run_images(config, count, app_config)

    @app.command("broll")
    def cmd_broll(
        config: str = typer.Option(..., "--config", "-c"),
        count: int = typer.Option(40, "--count"),
        app_config: Optional[str] = typer.Option(None, "--app-config"),
    ):
        """Generate B-roll video clips."""
        run_broll(config, count, app_config)

    @app.command("videos")
    def cmd_videos(
        config: str = typer.Option(..., "--config", "-c"),
        count: int = typer.Option(300, "--count"),
        app_config: Optional[str] = typer.Option(None, "--app-config"),
    ):
        """Render talking actor videos and assemble final creatives."""
        run_videos(config, count, app_config)

    @app.command("qa")
    def cmd_qa(
        run_id: str = typer.Option("latest", "--run-id"),
        app_config: Optional[str] = typer.Option(None, "--app-config"),
    ):
        """Run quality assurance on a completed run."""
        run_qa(run_id, app_config)

    @app.command("export")
    def cmd_export(
        run_id: str = typer.Option("latest", "--run-id"),
        app_config: Optional[str] = typer.Option(None, "--app-config"),
    ):
        """Export accepted creatives from a run."""
        run_export(run_id, app_config)

    @app.command("status")
    def cmd_status(
        app_config: Optional[str] = typer.Option(None, "--app-config"),
    ):
        """Show system status, API key check, and recent runs."""
        run_status(app_config)

    @app.command("generate")
    def cmd_generate(
        config: str = typer.Option(..., "--config", "-c"),
        count: int = typer.Option(500, "--count"),
        app_config: Optional[str] = typer.Option(None, "--app-config"),
        resume: bool = typer.Option(False, "--resume"),
        force: bool = typer.Option(False, "--force"),
    ):
        """Alias for autopilot — full end-to-end generation."""
        run_autopilot(config, count, app_config, resume, force)


# ---------------------------------------------------------------------------
# Argparse fallback
# ---------------------------------------------------------------------------

def _argparse_main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="AI Ad Agency — Creative Swarm Platform"
    )
    subparsers = parser.add_subparsers(dest="command")

    # autopilot
    ap = subparsers.add_parser("autopilot", help="Full end-to-end generation")
    ap.add_argument("--config", required=True)
    ap.add_argument("--count", type=int, default=500)
    ap.add_argument("--app-config", default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--force", action="store_true")

    # generate (alias)
    gp = subparsers.add_parser("generate", help="Alias for autopilot")
    gp.add_argument("--config", required=True)
    gp.add_argument("--count", type=int, default=500)
    gp.add_argument("--app-config", default=None)
    gp.add_argument("--resume", action="store_true")
    gp.add_argument("--force", action="store_true")

    # hooks
    hp = subparsers.add_parser("hooks")
    hp.add_argument("--config", required=True)
    hp.add_argument("--count", type=int, default=200)

    # scripts
    sp = subparsers.add_parser("scripts")
    sp.add_argument("--config", required=True)

    # avatars
    avp = subparsers.add_parser("avatars")
    avp.add_argument("--sync", action="store_true")

    # images
    ip = subparsers.add_parser("images")
    ip.add_argument("--config", required=True)
    ip.add_argument("--count", type=int, default=200)

    # broll
    bp = subparsers.add_parser("broll")
    bp.add_argument("--config", required=True)
    bp.add_argument("--count", type=int, default=40)

    # videos
    vp = subparsers.add_parser("videos")
    vp.add_argument("--config", required=True)
    vp.add_argument("--count", type=int, default=300)

    # qa
    qp = subparsers.add_parser("qa")
    qp.add_argument("--run-id", default="latest")

    # export
    ep = subparsers.add_parser("export")
    ep.add_argument("--run-id", default="latest")

    # status
    subparsers.add_parser("status")

    args = parser.parse_args()

    dispatch = {
        "autopilot": lambda: run_autopilot(args.config, args.count, getattr(args, "app_config", None), args.resume, args.force),
        "generate": lambda: run_autopilot(args.config, args.count, getattr(args, "app_config", None), args.resume, args.force),
        "hooks": lambda: run_hooks(args.config, args.count),
        "scripts": lambda: run_scripts(args.config),
        "avatars": lambda: run_avatars(args.sync),
        "images": lambda: run_images(args.config, args.count),
        "broll": lambda: run_broll(args.config, args.count),
        "videos": lambda: run_videos(args.config, args.count),
        "qa": lambda: run_qa(args.run_id),
        "export": lambda: run_export(args.run_id),
        "status": lambda: run_status(),
    }

    if args.command in dispatch:
        dispatch[args.command]()
    else:
        parser.print_help()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if _TYPER:
        app()
    else:
        _argparse_main()
