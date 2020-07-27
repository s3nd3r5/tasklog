import logging
import configparser
import uuid
import time
from flask import Flask, render_template, url_for, flash, redirect, request
import psycopg2
from psycopg2.extras import execute_batch, register_uuid

# constants
DATE_FMT = '%Y-%m-%dT%H:%M'

SQL_SELECT_OPEN = """
SELECT task_id, created_at, task_type, created_by, task_body
FROM tasks
WHERE completed = false
ORDER BY created_at ASC
""".strip()

SQL_SELECT_BY_TYPE = """
SELECT task_id, created_at, task_type, created_by, task_body
FROM tasks
WHERE completed = false AND task_type = %s
ORDER BY created_at ASC
""".strip()

SQL_SELECT_TYPES = """
SELECT DISTINCT(task_type)
FROM tasks
WHERE completed = false AND task_type != %s
""".strip()

SQL_COMPLETE_TASKS = """
UPDATE tasks
SET completed = true
WHERE task_id = %s
""".strip() # TODO - completed on


# helpers

## UI friendly task object
class Task:
    def __init__(self, id, date, type, user, body):
        self.id = id
        self.date = date.strftime(DATE_FMT)
        self.type = type
        self.user = user
        self.body = body

## map select to task object
def map_to_tasks(queryResult):
    tasks = []
    for r in queryResult:
        tasks.append(Task(r[0], r[1], r[2], r[3], r[4]))
    return tasks

## provide a function to ensure nothing leaks from query objet
def map_to_types(queryResult):
    types = []
    for r in queryResult:
        types.append(r[0])
    types.sort()
    return types

## get types from task
def get_types(tasks):
    types = []
    for t in tasks:
        if not t.type in types:
            types.append(t.type)
    types.sort()
    return types

## safe DB connector (db might not be available upon start
def db_connect(config, max_retries=5):
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

## check the input coming from the server
def validate_task_ids(task_ids):
    if type(task_ids) is not list:
        logging.warning('tasks not list')
        return False
    for id in task_ids:
        try:
            if not uuid.UUID(id).version:
                logging.warning('not uuid')
                return False
        except ValueError:
            logging.warning('value error', exc_info=True)
            return False
    return True

## copy list into list of tuples
def ids_to_uuid_tuples(some_list):
    copy_list = []
    for v in some_list:
        copy_list.append((uuid.UUID(v), ))
    return copy_list

# copy cfg configuration subset into application (uppercasing keys)
def configureApp(app, configItems):
    updateDict = dict()
    for k, v in configItems:
        updateDict[k.upper()] = v
    app.config.update(updateDict)

# determine redirect - is host https:// or less? (http:// or somethign else ??
# TODO - this seems hacky, mabye setup better CORs handling 
def handle_redirect(request):
    if (request.referrer and request.referrer.find(request.host) <= 7):
        return redirect(request.referrer)
    else:
        logging.warning('referer [%s] did not match [%s], could not redirect', request.referrer, request.host)
        flash('Unable to complete redirect to original page', 'warning')
        return redirect(url_for('open'))

# utils
logging.basicConfig(format='%(asctime)s - [%(levelname)s]\t%(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
        level=logging.INFO)
config = configparser.ConfigParser()
config.read_file(open('/secrets/tasklog.cfg'))
register_uuid() # allow DB to use UUIDs

# flask
app = Flask(__name__)
configureApp(app, config.items('taskui', raw=True))
conn = db_connect(config['db'])

@app.route('/')
@app.route('/open')
def open():
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(SQL_SELECT_OPEN)
        res = cursor.fetchall()
        tasks = map_to_tasks(res)
        types = get_types(tasks)
        return render_template('open.html.jinja', tasks=tasks, types=types, title='Open')
    except:
        logging.error('Failed to list open tasks', exc_info=True)
        return render_template('error.html.jinja', message='Unexpected error loading {}'.format(url_for('open'))), 501
    finally:
        if cursor:
            cursor.close()

# TODO - can we validate this so we don't make SQL requests w/o the tasks existing?
@app.route('/open/<string:task_type>')
def open_tasks(task_type):
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(SQL_SELECT_BY_TYPE, (task_type,))
        res = cursor.fetchall()
        tasks = map_to_tasks(res)
        cursor.execute(SQL_SELECT_TYPES, (task_type,))
        res = cursor.fetchall()
        types = map_to_types(res)
        return render_template('open.html.jinja', tasks=tasks, types=types, title=task_type.title(), by_type=True)
    except:
        logging.error('Failed to list open tasks for type: {}'.format(task_type), exc_info=True)
        return render_template('error.html.jinja', message='Unexpected error loading {}'.format(url_for('open_tasks', task_type=task_type))), 500
    finally:
        if cursor:
            cursor.close()

@app.route('/action/complete', methods=['POST'])
def action_complete():
    cursor = None
    try:
        rqIds = request.form.getlist('completedTasks')
        if validate_task_ids(rqIds):
            task_ids = ids_to_uuid_tuples(rqIds)
            cursor = conn.cursor()
            execute_batch(cursor, SQL_COMPLETE_TASKS, task_ids)
            conn.commit()
            flash('Successfully compelted {} tasks'.format(len(task_ids)), 'success')
            return handle_redirect(request)
        else:
            flash('Bad request - server got unexpected request data. Refresh and try again', 'warning')
            return handle_redirect(request)
    except KeyError as e:
        logging.debug('Empty form submitted to: %s', url_for('action_complete'))
    except:
        logging.error('Failed to complete tasks', exc_info=True)
        conn.rollback()
        return render_template('error.html.jinja', message='Failed to complete tasks. Please return and try again'), 500
    finally:
        if cursor:
            cursor.close()
    return render_template('error.html.jinja', message='Invalid request body, please return and try again'), 400

@app.route('/completed')
def compelted():
    return 'Completed'


