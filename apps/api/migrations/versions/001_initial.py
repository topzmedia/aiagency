"""Initial migration - create all tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(320), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # --- searches ---
    op.create_table(
        "searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_query", sa.Text(), nullable=False),
        sa.Column("normalized_query_json", postgresql.JSON(), nullable=True),
        sa.Column("region", sa.String(10), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("platforms", postgresql.JSON(), nullable=True),
        sa.Column("include_filters_json", postgresql.JSON(), nullable=True),
        sa.Column("exclude_filters_json", postgresql.JSON(), nullable=True),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("max_results", sa.Integer(), server_default="50", nullable=False),
        sa.Column("confidence_threshold", sa.Float(), server_default="0.3", nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("queued", "processing", "completed", "failed", name="search_status", create_type=True),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("progress_percent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_candidates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_analyzed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_results", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_searches_user_id", "searches", ["user_id"])
    op.create_index("ix_searches_status", "searches", ["status"])

    # --- candidate_videos ---
    op.create_table(
        "candidate_videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("external_id", sa.String(512), nullable=True),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("creator_handle", sa.String(256), nullable=True),
        sa.Column("creator_name", sa.String(256), nullable=True),
        sa.Column("caption_text", sa.Text(), nullable=True),
        sa.Column("hashtags_json", postgresql.JSON(), nullable=True),
        sa.Column("publish_date", sa.DateTime(), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("region_hint", sa.String(10), nullable=True),
        sa.Column("thumbnail_path", sa.Text(), nullable=True),
        sa.Column("local_media_path", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), server_default="{}", nullable=False),
        sa.Column("ingestion_source", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_candidate_videos_external_id", "candidate_videos", ["external_id"])
    op.create_index("ix_candidate_videos_platform", "candidate_videos", ["platform"])
    op.create_index("ix_candidate_videos_ingestion_source", "candidate_videos", ["ingestion_source"])

    # --- duplicate_groups ---
    op.create_table(
        "duplicate_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("group_key", sa.String(256), nullable=False, unique=True),
        sa.Column(
            "representative_candidate_video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_videos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_duplicate_groups_group_key", "duplicate_groups", ["group_key"])

    # --- video_assets ---
    op.create_table(
        "video_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "candidate_video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_type",
            postgresql.ENUM("video", "thumbnail", "audio", name="asset_type", create_type=True),
            nullable=False,
        ),
        sa.Column("storage_provider", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_video_assets_candidate_video_id", "video_assets", ["candidate_video_id"])

    # --- video_analyses ---
    op.create_table(
        "video_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "candidate_video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_videos.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "processing", "completed", "failed", name="analysis_status", create_type=True),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("scene_segments_json", postgresql.JSON(), nullable=True),
        sa.Column("objects_json", postgresql.JSON(), nullable=True),
        sa.Column("scenes_json", postgresql.JSON(), nullable=True),
        sa.Column("actions_json", postgresql.JSON(), nullable=True),
        sa.Column("ocr_text_json", postgresql.JSON(), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("transcript_chunks_json", postgresql.JSON(), nullable=True),
        sa.Column("audio_events_json", postgresql.JSON(), nullable=True),
        sa.Column("embeddings_json_metadata", postgresql.JSON(), nullable=True),
        sa.Column("quality_flags_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_video_analyses_candidate_video_id", "video_analyses", ["candidate_video_id"])

    # --- result_rankings ---
    op.create_table(
        "result_rankings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "search_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("searches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("rank_position", sa.Integer(), nullable=False),
        sa.Column("accepted", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("reason_codes_json", postgresql.JSON(), nullable=True),
        sa.Column("score_breakdown_json", postgresql.JSON(), nullable=True),
        sa.Column("matched_segments_json", postgresql.JSON(), nullable=True),
        sa.Column(
            "duplicate_group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("duplicate_groups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_result_rankings_search_id", "result_rankings", ["search_id"])
    op.create_index("ix_result_rankings_candidate_video_id", "result_rankings", ["candidate_video_id"])
    op.create_index("ix_result_rankings_duplicate_group_id", "result_rankings", ["duplicate_group_id"])

    # --- user_feedbacks ---
    op.create_table(
        "user_feedbacks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "search_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("searches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "label",
            postgresql.ENUM("very_relevant", "somewhat_relevant", "irrelevant", name="feedback_label", create_type=True),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_feedbacks_user_id", "user_feedbacks", ["user_id"])
    op.create_index("ix_user_feedbacks_search_id", "user_feedbacks", ["search_id"])
    op.create_index("ix_user_feedbacks_candidate_video_id", "user_feedbacks", ["candidate_video_id"])

    # --- collections ---
    op.create_table(
        "collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_collections_user_id", "collections", ["user_id"])

    # --- collection_items ---
    op.create_table(
        "collection_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "collection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_collection_items_collection_id", "collection_items", ["collection_id"])
    op.create_index("ix_collection_items_candidate_video_id", "collection_items", ["candidate_video_id"])

    # --- ingestion_jobs ---
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_type", sa.String(128), nullable=False),
        sa.Column("source_config_json", postgresql.JSON(), server_default="{}", nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("queued", "processing", "completed", "failed", name="ingestion_status", create_type=True),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("total_records", sa.Integer(), server_default="0", nullable=False),
        sa.Column("imported_records", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rejected_records", sa.Integer(), server_default="0", nullable=False),
        sa.Column("log_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ingestion_jobs_source_type", "ingestion_jobs", ["source_type"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])

    # --- content_embeddings ---
    op.create_table(
        "content_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "candidate_video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "embedding_type",
            postgresql.ENUM("caption", "transcript", "ocr", "frame", name="embedding_type", create_type=True),
            nullable=False,
        ),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_content_embeddings_candidate_video_id", "content_embeddings", ["candidate_video_id"])

    # Add vector column using raw SQL (pgvector)
    op.execute("ALTER TABLE content_embeddings ADD COLUMN embedding vector(384) NOT NULL")
    # Create HNSW index for cosine similarity search
    op.execute(
        "CREATE INDEX ix_content_embeddings_embedding_hnsw ON content_embeddings "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_table("content_embeddings")
    op.drop_table("ingestion_jobs")
    op.drop_table("collection_items")
    op.drop_table("collections")
    op.drop_table("user_feedbacks")
    op.drop_table("result_rankings")
    op.drop_table("video_analyses")
    op.drop_table("video_assets")
    op.drop_table("duplicate_groups")
    op.drop_table("candidate_videos")
    op.drop_table("searches")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS search_status")
    op.execute("DROP TYPE IF EXISTS asset_type")
    op.execute("DROP TYPE IF EXISTS analysis_status")
    op.execute("DROP TYPE IF EXISTS feedback_label")
    op.execute("DROP TYPE IF EXISTS ingestion_status")
    op.execute("DROP TYPE IF EXISTS embedding_type")

    op.execute("DROP EXTENSION IF EXISTS vector")
