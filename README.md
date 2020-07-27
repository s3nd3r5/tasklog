# Tasklog

A Discord Bot for taking requests and a Django admin UI for managing their status.

## Setup

Tasklog runs off of a docker-compose.yml and can be launched via `docker-compose up --build -d`

Before each service can run you will need to ensure the expected files are created and in their expected locations.

## Services

### Taskbot

Requires a bot to be created, and a token 
See requirements.txt for dependencies. 

#### Commands

The bot takes in requests via the: `!request` prefix

**Making a request**
`!request [type] [body]` - this will categorize the request by type and capture the rest of the message body. 

**User Commands**
`!request help` - show usage information

`!request queue` - show current requests in the queue

`!request list [completed]` - list your requests, `completed` option will show the completed requests

A complete list of commands can be found at the top of the taskbot.py file 

#### Expected Files

- secrets/tasklog.cfg - a filled out copy of the tasklog.cfg (see taskbot.py for required values)

### Taskui

Flask UI for managing tasks

#### What can you manage?

Right now you can only mark tasks as complete

#### Usage

As of this commit to access navigate to: http://localhost:5000/ to open the main portal

##### Task view

To view open tasks by type you can navigate to: http://localhost:5000/open/<tasktype>

##### Completed (wip)

To view previously completed tasks you can navigate to: http://localhost:5000/completed

This view is not yet complete.

#### Expected files

- secrets/tasklog.cfg - a filled out copy of the tasklog.cfg (see taskui.py for required values)

The values for `taskui` section are flask specific configurations. They will will be copied into their upper-case values
in `app.config`. See flasks documentation to see what configurations can be set, they may require custom code to operate.

### Postgres Db

A postgres instance is what backs the tasklog. 

#### Schema

The schema can be found in `sql/*.sql`

##### Changes

Changes to the database schema should occur as update statmenets in the db sql file. 

To pass in update sql files you can use `docker cp` to pass files into the postgres instance,
which can then be executed via `\i /path/to/file.sql`.

#### Expected Files

 - secrets/pgpass - password file for postgres db

