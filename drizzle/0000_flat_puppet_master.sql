CREATE TABLE `aliases` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`alias` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
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
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`relation` text NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`article_id`) REFERENCES `articles`(`id`) ON UPDATE no action ON DELETE no action
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
	`run_id` text,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`run_id`) REFERENCES `runs`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `awards` (
	`id` text PRIMARY KEY NOT NULL,
	`award_name` text NOT NULL,
	`category` text NOT NULL,
	`year` integer NOT NULL,
	`person_id` text,
	`title_id` text,
	`outcome` text NOT NULL,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`person_id`) REFERENCES `people`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`title_id`) REFERENCES `titles`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `collaborations` (
	`id` text PRIMARY KEY NOT NULL,
	`person_a_id` text NOT NULL,
	`person_b_id` text NOT NULL,
	`title_id` text,
	`relationship` text NOT NULL,
	`year_start` integer,
	`year_end` integer,
	`project_count` integer,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`person_a_id`) REFERENCES `people`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`person_b_id`) REFERENCES `people`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`title_id`) REFERENCES `titles`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `companies` (
	`id` text PRIMARY KEY NOT NULL,
	`source_id` text NOT NULL,
	`external_id` text,
	`name` text NOT NULL,
	`canonical_name` text NOT NULL,
	`company_type` text NOT NULL,
	`parent_company_id` text,
	`status` text DEFAULT 'active' NOT NULL,
	`license_class` text NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`parent_company_id`) REFERENCES `companies`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `company_relations` (
	`id` text PRIMARY KEY NOT NULL,
	`company_a_id` text NOT NULL,
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`relationship` text NOT NULL,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`company_a_id`) REFERENCES `companies`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `contacts` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`contact_type` text NOT NULL,
	`contact_value` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `credits` (
	`id` text PRIMARY KEY NOT NULL,
	`person_id` text NOT NULL,
	`title_id` text NOT NULL,
	`company_id` text,
	`role` text NOT NULL,
	`credit_category` text,
	`season` integer,
	`episodes` integer,
	`year_start` integer,
	`year_end` integer,
	`network` text,
	`billing` integer,
	`room_position` text,
	`contract_type` text,
	`active` integer DEFAULT 1 NOT NULL,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`person_id`) REFERENCES `people`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`title_id`) REFERENCES `titles`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`company_id`) REFERENCES `companies`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `deals` (
	`id` text PRIMARY KEY NOT NULL,
	`deal_type` text NOT NULL,
	`person_id` text,
	`company_id` text,
	`title_id` text,
	`counterparty_id` text,
	`status` text DEFAULT 'negotiating' NOT NULL,
	`compensation_min` integer,
	`compensation_max` integer,
	`backend_points` real,
	`option_periods` integer,
	`exclusivity` text,
	`territory` text,
	`date_signed` text,
	`date_start` text,
	`date_end` text,
	`credit_obligations` text,
	`notes` text,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`person_id`) REFERENCES `people`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`company_id`) REFERENCES `companies`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`title_id`) REFERENCES `titles`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`counterparty_id`) REFERENCES `companies`(`id`) ON UPDATE no action ON DELETE no action
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
	`canonical_id` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `entity_match_decisions` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_a_id` text NOT NULL,
	`entity_b_id` text NOT NULL,
	`entity_type` text NOT NULL,
	`decision` text NOT NULL,
	`confidence` real,
	`reason` text NOT NULL,
	`decided_by` text NOT NULL,
	`decided_at` text NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`entity_a_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`entity_b_id`) REFERENCES `entities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `entity_taggings` (
	`id` text PRIMARY KEY NOT NULL,
	`tag_id` text NOT NULL,
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`tag_id`) REFERENCES `tags`(`id`) ON UPDATE no action ON DELETE no action,
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
CREATE TABLE `links` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`url` text NOT NULL,
	`link_type` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `people` (
	`id` text PRIMARY KEY NOT NULL,
	`source_id` text NOT NULL,
	`external_id` text,
	`name` text NOT NULL,
	`canonical_name` text NOT NULL,
	`bio` text,
	`birth_year` integer,
	`death_year` integer,
	`primary_profession` text,
	`wga_status` text,
	`sag_status` text,
	`status` text DEFAULT 'active' NOT NULL,
	`license_class` text NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
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
	`department` text,
	`title` text,
	`email` text,
	`phone` text,
	`primary_rep` integer DEFAULT 0 NOT NULL,
	`co_rep` integer DEFAULT 0 NOT NULL,
	`date_start` text,
	`date_end` text,
	`active` integer DEFAULT 1 NOT NULL,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`client_id`) REFERENCES `people`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`rep_id`) REFERENCES `people`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`rep_company_id`) REFERENCES `companies`(`id`) ON UPDATE no action ON DELETE no action
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
CREATE TABLE `staged_facts` (
	`id` text PRIMARY KEY NOT NULL,
	`fact_type` text NOT NULL,
	`entity_refs_json` text NOT NULL,
	`payload_json` text NOT NULL,
	`status` text DEFAULT 'pending' NOT NULL,
	`materialized_table` text,
	`materialized_row_id` text,
	`source_id` text NOT NULL,
	`document_id` text,
	`extraction_id` text,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`document_id`) REFERENCES `raw_records`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`extraction_id`) REFERENCES `extraction_results`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `submissions` (
	`id` text PRIMARY KEY NOT NULL,
	`submitted_by_person` text,
	`submitted_by_company` text,
	`submitted_to_person` text,
	`submitted_to_company` text,
	`opportunity_title_id` text,
	`role` text,
	`material_type` text,
	`purpose` text,
	`received_at` text,
	`outcome` text,
	`outcome_date` text,
	`notes` text,
	`document_id` text,
	`extraction_id` text,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`submitted_by_person`) REFERENCES `people`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`submitted_by_company`) REFERENCES `companies`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`submitted_to_person`) REFERENCES `people`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`submitted_to_company`) REFERENCES `companies`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`opportunity_title_id`) REFERENCES `titles`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`document_id`) REFERENCES `raw_records`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`extraction_id`) REFERENCES `extraction_results`(`id`) ON UPDATE no action ON DELETE no action
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
CREATE TABLE `titles` (
	`id` text PRIMARY KEY NOT NULL,
	`source_id` text NOT NULL,
	`external_id` text,
	`title` text NOT NULL,
	`canonical_name` text NOT NULL,
	`format` text NOT NULL,
	`genre` text,
	`network` text,
	`season_count` integer,
	`episode_count` integer,
	`logline` text,
	`synopsis` text,
	`status` text DEFAULT 'development' NOT NULL,
	`premiere_date` text,
	`announced_date` text,
	`license_class` text NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
