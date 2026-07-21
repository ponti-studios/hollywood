DROP TABLE `awards`;--> statement-breakpoint
DROP TABLE `collaborations`;--> statement-breakpoint
DROP TABLE `deals`;--> statement-breakpoint
DROP TABLE `entities`;--> statement-breakpoint
DROP TABLE `entity_match_decisions`;--> statement-breakpoint
DROP TABLE `source_facts`;--> statement-breakpoint
DROP TABLE `staged_facts`;--> statement-breakpoint
PRAGMA foreign_keys=OFF;--> statement-breakpoint
CREATE TABLE `__new_entity_taggings` (
	`id` text PRIMARY KEY NOT NULL,
	`tag_id` text NOT NULL,
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`source_id` text NOT NULL,
	`trust_state` text DEFAULT 'machine_extracted' NOT NULL,
	`source_fact_id` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`tag_id`) REFERENCES `tags`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
INSERT INTO `__new_entity_taggings`("id", "tag_id", "entity_type", "entity_id", "source_id", "trust_state", "source_fact_id", "created_at") SELECT "id", "tag_id", "entity_type", "entity_id", "source_id", "trust_state", "source_fact_id", "created_at" FROM `entity_taggings`;--> statement-breakpoint
DROP TABLE `entity_taggings`;--> statement-breakpoint
ALTER TABLE `__new_entity_taggings` RENAME TO `entity_taggings`;--> statement-breakpoint
PRAGMA foreign_keys=ON;