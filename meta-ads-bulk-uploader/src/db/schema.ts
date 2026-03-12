import {
  pgTable,
  uuid,
  text,
  timestamp,
  jsonb,
  integer,
  pgEnum,
} from "drizzle-orm/pg-core";

export const uploadStatusEnum = pgEnum("upload_status", [
  "pending",
  "validating",
  "uploading",
  "completed",
  "failed",
]);

export const adStatusEnum = pgEnum("ad_status", [
  "pending",
  "submitted",
  "active",
  "rejected",
  "failed",
]);

export const campaigns = pgTable("campaigns", {
  id: uuid("id").defaultRandom().primaryKey(),
  name: text("name").notNull(),
  metaAccountId: text("meta_account_id"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const uploadBatches = pgTable("upload_batches", {
  id: uuid("id").defaultRandom().primaryKey(),
  campaignId: uuid("campaign_id")
    .references(() => campaigns.id)
    .notNull(),
  fileName: text("file_name").notNull(),
  status: uploadStatusEnum("status").default("pending").notNull(),
  totalAds: integer("total_ads").default(0).notNull(),
  successCount: integer("success_count").default(0).notNull(),
  failureCount: integer("failure_count").default(0).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const ads = pgTable("ads", {
  id: uuid("id").defaultRandom().primaryKey(),
  batchId: uuid("batch_id")
    .references(() => uploadBatches.id)
    .notNull(),
  name: text("name").notNull(),
  headline: text("headline"),
  primaryText: text("primary_text"),
  description: text("description"),
  callToAction: text("call_to_action"),
  linkUrl: text("link_url"),
  imageUrl: text("image_url"),
  videoUrl: text("video_url"),
  status: adStatusEnum("status").default("pending").notNull(),
  metaAdId: text("meta_ad_id"),
  metaResponse: jsonb("meta_response"),
  errorMessage: text("error_message"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});
