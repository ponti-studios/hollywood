CREATE TABLE `article_content` (
	`id` text PRIMARY KEY NOT NULL,
	`article_id` text NOT NULL,
	`source_id` text NOT NULL,
	`content_kind` text NOT NULL,
	`text` text NOT NULL,
	`raw_record_id` text,
	`content_hash` text NOT NULL,
	`license_class` text NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`article_id`) REFERENCES `articles`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`raw_record_id`) REFERENCES `raw_records`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `article_entities` (
	`id` text PRIMARY KEY NOT NULL,
	`article_id` text NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`relation` text NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`article_id`) REFERENCES `articles`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`entity_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `articles` (
	`id` text PRIMARY KEY NOT NULL,
	`source_id` text NOT NULL,
	`canonical_url` text,
	`url` text NOT NULL,
	`title` text,
	`author` text,
	`published_at` text,
	`summary` text,
	`feed_guid` text,
	`license_class` text NOT NULL,
	`run_id` text NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`run_id`) REFERENCES `runs`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `collaborations` (
	`id` text PRIMARY KEY NOT NULL,
	`person_a_id` text NOT NULL,
	`person_b_id` text NOT NULL,
	`title_id` text,
	`relationship` text NOT NULL,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`person_a_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`person_b_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`title_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `credits` (
	`id` text PRIMARY KEY NOT NULL,
	`person_id` text NOT NULL,
	`title_id` text NOT NULL,
	`company_id` text,
	`source_id` text NOT NULL,
	`role` text NOT NULL,
	`credit_type` text NOT NULL,
	`billing` integer,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`person_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`title_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`company_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `deals` (
	`id` text PRIMARY KEY NOT NULL,
	`person_id` text,
	`company_id` text,
	`title_id` text,
	`deal_type` text NOT NULL,
	`status` text DEFAULT 'machine_extracted' NOT NULL,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`person_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`company_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`title_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `entities` (
	`id` text PRIMARY KEY NOT NULL,
	`source_id` text NOT NULL,
	`external_id` text,
	`entity_type` text NOT NULL,
	`name` text NOT NULL,
	`canonical_name` text NOT NULL,
	`bio` text,
	`position` text,
	`title_type` text,
	`format` text,
	`company_type` text,
	`status` text DEFAULT 'active' NOT NULL,
	`license_class` text NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `entity_aliases` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`alias` text NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`entity_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `entity_contacts` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`contact_type` text NOT NULL,
	`contact_value` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`entity_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `entity_links` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`url` text NOT NULL,
	`link_type` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`entity_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `entity_merges` (
	`id` text PRIMARY KEY NOT NULL,
	`surviving_id` text NOT NULL,
	`merged_id` text NOT NULL,
	`reason` text NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`surviving_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`merged_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `entity_taggings` (
	`id` text PRIMARY KEY NOT NULL,
	`tag_id` text NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`tag_id`) REFERENCES `tags`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`entity_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_fact_id`) REFERENCES `source_facts`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `extraction_results` (
	`id` text PRIMARY KEY NOT NULL,
	`document_id` text NOT NULL,
	`job_id` text,
	`schema_version` text NOT NULL,
	`prompt_version` text NOT NULL,
	`model_name` text NOT NULL,
	`status` text NOT NULL,
	`raw_json` text DEFAULT '' NOT NULL,
	`result_json` text NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`document_id`) REFERENCES `raw_records`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`job_id`) REFERENCES `runs`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `merge_candidates` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_a_id` text NOT NULL,
	`entity_b_id` text NOT NULL,
	`reason` text NOT NULL,
	`status` text DEFAULT 'needs_review' NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`entity_a_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`entity_b_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `raw_records` (
	`id` text PRIMARY KEY NOT NULL,
	`run_id` text,
	`source_id` text NOT NULL,
	`source_kind` text NOT NULL,
	`payload_type` text NOT NULL,
	`content_path` text NOT NULL,
	`content_hash` text NOT NULL,
	`content_type` text,
	`source_url` text,
	`canonical_url` text,
	`fetched_at` text NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`run_id`) REFERENCES `runs`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `representation` (
	`id` text PRIMARY KEY NOT NULL,
	`client_id` text NOT NULL,
	`rep_id` text NOT NULL,
	`rep_company_id` text,
	`rep_type` text NOT NULL,
	`title` text,
	`email` text,
	`phone` text,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`client_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`rep_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`rep_company_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `runs` (
	`id` text PRIMARY KEY NOT NULL,
	`source_id` text NOT NULL,
	`run_kind` text NOT NULL,
	`status` text NOT NULL,
	`options_json` text,
	`summary_json` text,
	`error_text` text,
	`started_at` text NOT NULL,
	`completed_at` text
);
--> statement-breakpoint
CREATE TABLE `source_facts` (
	`id` text PRIMARY KEY NOT NULL,
	`source_table` text NOT NULL,
	`source_row_id` text NOT NULL,
	`document_id` text,
	`extraction_id` text,
	`json_path` text,
	`source_text` text,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`confidence` text DEFAULT 'machine_extracted' NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`document_id`) REFERENCES `raw_records`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`extraction_id`) REFERENCES `extraction_results`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `submissions` (
	`id` text PRIMARY KEY NOT NULL,
	`document_id` text NOT NULL,
	`extraction_id` text NOT NULL,
	`submitted_by_person_id` text,
	`submitted_by_company_id` text,
	`submitted_to_person_id` text,
	`submitted_to_company_id` text,
	`opportunity_title_id` text,
	`purpose` text,
	`received_at` text,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`document_id`) REFERENCES `raw_records`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`extraction_id`) REFERENCES `extraction_results`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`submitted_by_person_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`submitted_by_company_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`submitted_to_person_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`submitted_to_company_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`opportunity_title_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `tags` (
	`id` text PRIMARY KEY NOT NULL,
	`tag` text NOT NULL,
	`normalized_tag` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `tags_normalized_tag_unique` ON `tags` (`normalized_tag`);--> statement-breakpoint
CREATE TABLE `title_companies` (
	`id` text PRIMARY KEY NOT NULL,
	`title_id` text NOT NULL,
	`company_id` text NOT NULL,
	`source_id` text NOT NULL,
	`relationship` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`title_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`company_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
