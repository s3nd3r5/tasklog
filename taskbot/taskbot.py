"""
Copyright (c) 2020 s3nd3r5
This source is subject to MIT license.
See LICENSE or go to https://opensource.org/licenses/MIT for full license details.
"""
import time
import logging
import configparser
import uuid
import discord
from discord.ext import commands
import psycopg2
from psycopg2.extras import register_uuid

## constants
sql_insert="""
INSERT INTO tasks (task_id, task_type, created_by, source, task_body)
VALUES(%s, %s, %s, %s, %s)
""".strip()

sql_queue="""
SELECT created_at, task_type, created_by, task_body
FROM tasks
WHERE completed = false
ORDER BY created_at ASC
""".strip()

sql_list="""
SELECT created_at, task_type, task_body
FROM tasks
WHERE completed = %s AND created_by = %s
ORDER BY created_at ASC
""".strip()

insert_success='INSERT 0 1'

timeFmt='%Y-%m-%dT%H:%M'

## helper functions
def setup_prefixes(config):
    # setup prefixes, trim extra whitespace
    prefixes = [p.strip() for p in config['prefixes'].split(',')]
    if config.getboolean('append_whitespace'):
        prefixes_with_spaces = []
        for p in prefixes:
            prefixes_with_spaces.append('{} '.format(p.rstrip()))
        return prefixes_with_spaces
    else:
        return prefixes

def setup_aliases(config, types):
    alias_map = dict()
    for t in types:
        if t in config:
            t_aliases = config[t]
            if len(t_aliases) > 0:
                aliases = [a.strip().lower() for a in t_aliases.split(',')]
                for a in aliases:
                    # only one type per alias
                    # if multiconfig it's latest is greatest!
                    # todo: check and throw error?
                    alias_map[a] = t

    return alias_map

# the task command requires the types up front
# so we need the configured types AND their aliases
# then the command will basically remap them!
def setup_task_command_aliases(tasks, aliases):
    return tasks + list(aliases.keys())

def db_connect(config, max_retries=3):
    retries = 1
    while retries <= max_retries:
        try:
            return psycopg2.connect(
                    host=config['host'],
                    dbname=config['dbname'],
                    user=config['user'],
                    password=config['password'])
        except psycopg2.Error as e:
            retries += 1
            if retries > max_retries:
                logging.critical('Could not connect to database in %s retries', retries-1)
                raise e
            time.sleep(1 * retries) # wait longer per retry
    raise RuntimeError("Unable to connect to database")

## utils
logging.basicConfig(format='%(asctime)s - [%(levelname)s]\t%(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
        level=logging.INFO)
config = configparser.ConfigParser()
config.read_file(open('/secrets/tasklog.cfg'))
register_uuid() # allow DB to use UUIDs

## variables
prefixes = setup_prefixes(config['taskbot'])
# setup task types - lowercase and strip whitespace
task_types = [t.strip().lower() for t in config['tasklog']['task_types'].split(',')]
task_aliases = setup_aliases(config['aliases'], task_types)
task_command_aliases = setup_task_command_aliases(task_types, task_aliases)
# Setup intents
intents = discord.Intents()
intents.message_content=True
intents.messages=True
intents.reactions=True
intents.guilds=True

bot = commands.Bot(command_prefix=prefixes, description=config['taskbot']['description'], intents=intents)
conn = db_connect(config['db'])

## bot setup
@bot.event
async def on_ready():
    logging.info("Logged in as %s - %s and listening on: %s", bot.user.name, bot.user.id, ','.join(prefixes)) 

@bot.command(help='Shows the current open tasks', brief='Show open task queue')
async def queue(ctx):
    try:
        cursor = conn.cursor()
        cursor.execute(sql_queue)
        res = cursor.fetchall()
        msg = "# - {:<16} | {:<8}\t{:<10}\tRequest\n".format("Date", "Type", "User")
        for i, r in enumerate(res):
            msg = ("{}{} - {} | {:<8}\t{:<10}\t{}\n"
                .format(msg, i, r[0].strftime(timeFmt), r[1], r[2], r[3]))
        return await ctx.send("__Request Queue__\n```\n{msg}```".format(msg=msg))
    except:
        logger.error("Unable to list task queue", exc_info=True)
        return await ctx.send("Failed to list task queue. Please reach out to @{} to notify admins"
                .format(bot.user.name))
    finally:
        cursor.close()

@bot.command(brief='List your requested tasks',
        help='List your requested tasks. Or only the completed tasks with the completed flag set')
async def list(ctx, completed=False):
    created_by = ctx.author.name
    try:
        cursor = conn.cursor()
        cursor.execute(sql_list, (completed, created_by))
        res = cursor.fetchall()
        msg = "# - {:<16} | {:<8}\tRequest\n".format("Date", "Type")
        for i, r in enumerate(res):
            msg = ("{}{} - {} | {:<8}\t{}\n"
                .format(msg, i, r[0].strftime(timeFmt), r[1], r[2]))
        completed_msg = "Completed" if completed else "Current"
        return await ctx.send("__{user}'s {status} Queue__\n```\n{msg}```"
                .format(user=created_by,
                    status=completed_msg,
                    msg=msg))
    except:
        return await ctx.send("Failed to list task queue. Please reach out to @{} to notify admis"
                .format(bot.user.name))
    finally:
        cursor.close()

@bot.command(name='<task_type>',
        rest_is_raw=True,
        aliases=task_command_aliases,
        brief='Submit a task request',
        help=('Submit a task by specifying one of the task types and a task body. Suppored types: {}'
            .format(','.join(task_command_aliases))))
async def _request(ctx, *body):
    task_type = ctx.invoked_with.lower()
    if not task_type in task_command_aliases:
        return await ctx.send("Invalid task type: {}, valid types are: `{}`"
                .format(task_type, ','.join(task_types)))

    # get aliased type from task
    # if not a configured task type
    if task_type not in task_types and task_type in task_aliases:
        task_type = task_aliases[task_type]
    elif task_type not in task_types and task_type not in task_aliases:
        return await ctx.send("Invalid task type: {}, valid types are: `{}`"
            .format(task_type, ','.join(task_types)))

    created_by = ctx.author.name
    task_body = ' '.join(body)
    source = ('discord/{gid}/{cid}/{gname}/{cname}'
                .format(gid=ctx.guild.id, gname=ctx.guild.name,
                    cid=ctx.message.channel.id, cname=ctx.message.channel.name))
    try:
        cursor = conn.cursor()
        cursor.execute(sql_insert, (uuid.uuid4(), task_type, created_by, source, task_body))
        conn.commit()
        if cursor.statusmessage == insert_success:
            return await ctx.message.add_reaction('👍')
        else:
            return await ctx.send('Failed to store task, please reach out to @{} to notify admins'
                            .format(bot.user.name))
    except:
        logging.error('Unable to insert task: {} {} {} {}'
                    .format(task_type, created_by, source, task_body), exc_info=True)
        return await ctx.send("Failed to capture task. Please reach out to @{} to notify admins"
                .format(bot.user.name))
    finally:
        cursor.close()

@bot.event
async def on_command_error(ctx, error):
    await ctx.message.add_reaction('🙅') # https://emojipedia.org/man-gesturing-no/
    logging.debug('Invalid command: %s', ctx.message.content)
    await ctx.send("Probable invalid task type - try: `{}` otherwise use the help command.".format(task_command_aliases))

## run
token = config['taskbot']['token']

if not token:
    logging.critical("Invalid/empty token")
else:
    bot.run(token)
