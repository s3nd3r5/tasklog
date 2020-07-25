CREATE SCHEMA IF NOT EXISTS testing;

CREATE TABLE IF NOT EXISTS testing.tasks (
  task_id     serial not null PRIMARY KEY,
  task_type   varchar(255) not null,
  created_by  varchar(255) not null,
  source      varchar(255) not null,
  created_at  timestamp with time zone not null default now(),
  task_body   TEXT,
  completed   boolean default false
);

ALTER ROLE tasklog SET search_path = testing;
  
