# Tasklog

A Discord Bot for taking requests and a Django admin UI for managing their status.

## Setup

Tasklog runs off of a docker-compose.yml and can be launched via `docker-compose up --build -d`

Before each service can run you will need to ensure the expected files are created and in their expected locations.

## Services

### Taskbot

Requires a bot to be created, and a token 
See requirements.txt for full list of dependencies.

#### Commands

The bot takes in requests via the: `!request` prefix\* - *the prefix(es) can be configured in the tasklog.cfg*

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

Flask UI for managing tasks.
See requirements.txt for full list of dependencies.

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

# How to run

To run all of the services you must create the folder `secrets` and `volumes` in the workding directory where you're deploying these services.

Make a copy of `tasklog.cfg` and place it in `secrets/`. Fill out the config.

Make a new file `postgres_password` and place it in `secrets/`. This password should match that in `tasklog.cfg`. 

Then you can run `docker-compose --build -up -d`

## I screwed up the DB and need to start over

You can stop and remove everything with: `docker-compose down -v --rmi=all` to make a fresh start and then clear the DB volume with `sudo rm -r secrets/pgdata`

If you get conflicts when restarting the postgres you can clear all the old unattached volumes with: `docker volume prune` and `docker rm $(docker ps -aq)`.

# Powered By / Credits

This project is powered by:

- [docker](https://www.docker.com) via [compose](https://docs.docker.com/compose/) for running all the services
  - [postgreSQL](https://www.postgresql.org) for storage (via container image)
  - [nginx](https://www.nginx.com/) for webservering (wip) (via container image)
- [python](https://www.python.org/) version 3+
  - [discord.py](https://github.com/Rapptz/discord.py) for [discord](https://discord.com) integration (taskbot)
  - [flask](https://flask.palletsprojects.com/en/1.1.x/) for web backend/ui templating (taskui)
  - [psycopg2](https://www.psycopg.org/) to interface with postgreSQL
