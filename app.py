import os
import requests
import re
import datetime
import time
import redis
import sys
import json
from kubernetes import client, config

from flask import Flask, make_response, render_template, request, jsonify
app = Flask(__name__)

config.load_incluster_config()
v1 = client.CoreV1Api()
api_instance = client.AppsV1Api(client.ApiClient())

start_time = time.time()

CHART_VERSION = os.getenv('CHART_VERSION', None)
NAMESPACE = os.getenv('NAMESPACE', None)
RELEASENAME = os.getenv('RELEASENAME', None)
DAHOSTNAME = os.getenv('DAHOSTNAME', None)
S3ENABLE = os.getenv('S3ENABLE', None)
S3BUCKET = os.getenv('S3BUCKET', None)
S3ACCESSKEY = os.getenv('S3ACCESSKEY', None)
S3SECRETACCESSKEY = os.getenv('S3SECRETACCESSKEY', None)
S3REGION = os.getenv('S3REGION', None)
S3ENDPOINTURL = os.getenv('S3ENDPOINTURL', None)
AZUREENABLE = os.getenv('AZUREENABLE', None)
AZUREACCOUNTKEY = os.getenv('AZUREACCOUNTKEY', None)
AZUREACCOUNTNAME = os.getenv('AZUREACCOUNTNAME', None)
AZURECONTAINER = os.getenv('AZURECONTAINER', None)
DBHOST = os.getenv('DBHOST', None)
DBUSER = os.getenv('DBUSER', None)
DBPASSWORD = os.getenv('DBPASSWORD', None)
DBPORT = os.getenv('DBPORT', None)
DBPREFIX = os.getenv('DBPREFIX', None)
DBTABLEPREFIX = os.getenv('DBTABLEPREFIX', None)
BEHINDHTTPSLOADBALANCER = os.getenv('', None)
REDIS = os.getenv('REDIS', None)
RABBITMQ = os.getenv('RABBITMQ', None)
LOGSERVER = os.getenv('LOGSERVER', None)
DA_IMAGE = os.getenv('DA_IMAGE', None)
DA_MONITOR_IMAGE = os.getenv('DA_MONITOR_IMAGE', None)
IN_CLUSTER_MINIO = os.getenv('IN_CLUSTER_MINIO', None)
IN_CLUSTER_NGINX = os.getenv('IN_CLUSTER_NGINX', None)
IN_CLUSTER_POSTGRES = os.getenv('IN_CLUSTER_POSTGRES', None)
IN_CLUSTER_RABBITMQ = os.getenv('IN_CLUSTER_RABBITMQ', None)
IN_CLUSTER_REDIS = os.getenv('IN_CLUSTER_REDIS', None)
MINIO_REPLICAS = os.getenv('MINIO_REPLICAS', None)
MINIO_STORAGE = os.getenv('MINIO_STORAGE', None)
POSTGRES_IMAGE = os.getenv('POSTGRES_IMAGE', None)
POSTGRES_STORAGE = os.getenv('POSTGRES_STORAGE', None)
REDIS_IMAGE = os.getenv('REDIS_IMAGE', None)
REDIS_STORAGE = os.getenv('REDIS_STORAGE', None)
REPLICAS = os.getenv('REPLICAS', None)

if REDIS:
    redis_host = re.sub(r'^redis://', r'', REDIS.strip())
    m = re.search(r':([0-9]+)$', redis_host)
    if m:
        redis_port = m.group(1)
        redis_host = re.sub(r':([0-9]+)$', '', redis_host)
    else:
        redis_port = '6379'

@app.route('/api/v1/config')
def config():
    data = {
        'release': RELEASENAME,
        'hostname': DAHOSTNAME,
        's3': {
            'enable': True if S3ENABLE else False,
            'bucket': S3BUCKET,
            'region': S3REGION,
            'endpoint': S3ENDPOINTURL
        },
        'azure': {
            'enable': True if (not IN_CLUSTER_MINIO) and AZUREENABLE else False,
            'container': AZURECONTAINER
        },
        'db': {
            'host': DBHOST,
            'user': DBUSER,
            'port': DBPORT,
            'table prefix': DBTABLEPREFIX,
            'table prefix': DBPREFIX
        },
        'behindLoadBalancer': BEHINDHTTPSLOADBALANCER,
        'docassembleImage': DA_IMAGE,
        'docassembleMonitorImage': DA_MONITOR_IMAGE,
        'clusterFeatures': {
            'minio': IN_CLUSTER_MINIO,
            'nginx': IN_CLUSTER_NGINX,
            'postgres': IN_CLUSTER_POSTGRES,
            'rabbitmq': IN_CLUSTER_RABBITMQ,
            'redis': IN_CLUSTER_REDIS
        },
        'redis': REDIS,
        'rabbitmq': redact_rabbitmq(RABBITMQ),
        'logserver': LOGSERVER,
        'minioReplicas': MINIO_REPLICAS,
        'postgresImage': POSTGRES_IMAGE,
        'storage': {
            'minio': MINIO_STORAGE,
            'postgres': POSTGRES_STORAGE,
            'redis': REDIS_STORAGE
        },
        'redisImage': REDIS_IMAGE,
        'replicas': REPLICAS
    }
    return jsonify(data)

@app.route('/api/v1/pods')
def pods():
    return jsonify(get_pod_status())

@app.route('/api/v1/deployments')
def deployments():
    return jsonify(get_deployment_status())

@app.route('/api/v1/health')
def health():
    the_time = current_time()
    errors = get_errors()
    if len(errors) > 0:
        pass_fail = 'fail'
        output = "\n".join(errors)
        num_sessions = -1
        response_time = -1
    else:
        pass_fail = 'pass'
        output = ""
        num_sessions = get_session_count()
        response_time = get_response_time()
    data = {
        "status": pass_fail,
        "releaseId": CHART_VERSION,
        "notes": [""],
        "output": output,
        "checks": {
            "docassemble:responseTime": [
                {
                    "componentType": "datastore",
                    "observedValue": response_time,
                    "observedUnit": "ms",
                    "status": "pass" if response_time > 0 else "fail",
                    "affectedEndpoints" : [
                        "/health_check"
                    ],
                    "time": the_time,
                    "output": ""
                }
            ],
            "docassemble:sessions": [
                {
                    "componentType": "datastore",
                    "observedValue": num_sessions,
                    "status": "pass" if num_sessions >= 0 else "fail",
                    "time": the_time,
                    "output": ""
                }
            ],
            "uptime": [
                {
                    "componentType": "system",
                    "observedValue": current_seconds(),
                    "observedUnit": "s",
                    "status": "pass",
                    "time": the_time
                }
            ]
        }
    }
    return jsonify(data)

@app.route('/api/v1/status')
def status():
    errors = get_errors()
    if len(errors) > 0:
        ready = False
    else:
        ready = True
    return jsonify(dict(pods=get_pod_status(), deployments=get_deployment_status(), uptime=current_seconds(), session_count=get_session_count(), errors=errors, ready=ready))

@app.route('/api/v1/install_ready')
def install_ready():
    return ('', 200)

@app.route('/api/v1/install_complete')
def install_complete():
    return ready_response()

@app.route('/api/v1/pre_upgrade_ready')
def pre_upgrade_ready():
    return ('', 200)

@app.route('/api/v1/pre_upgrade_complete')
def pre_upgrade_complete():
    return ('', 200)

@app.route('/api/v1/post_upgrade_ready')
def post_upgrade_ready():
    return ('', 200)

@app.route('/api/v1/post_upgrade_complete')
def post_upgrade_complete():
    return ready_response()

def current_time():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

def current_seconds():
    return time.time() - start_time

def redact_rabbitmq(val):
    if val is None:
        return val
    return re.sub(r'^(pyamqp:[^@]*):[^@]*(@.*//)', r'\1\2', val)

def get_session_count():
    if not REDIS:
        return -1
    try:
        r = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
        num_sessions = r.get('da:stats:sessions')
        try:
            assert num_sessions is not None
            return int(num_sessions)
        except:
            return 0
    except Exception as err:
        sys.stderr.write("get_session_count: " + err.__class__.__name__ + ": " + str(err) + "\n")
        return -2

def get_response_time():
    try:
        r = requests.get('http://' + RELEASENAME + '-docassemble-service/health_check')
        if r.status_code != 200:
            sys.stderr.write("Health check did not return 200\n")
            return -1.0
        return r.elapsed.total_seconds()
    except Exception as err:
        sys.stderr.write("get_response_time: " + err.__class__.__name__ + ": " + str(err) + "\n")
        return -2.0

def get_deployment_status():
    ret = api_instance.list_namespaced_deployment(NAMESPACE)
    result = dict()
    for item in ret.items:
        try:
            result[re.sub(r'^' + RELEASENAME + '-', '', item.metadata.name)] = dict(available_replicas=item.status.available_replicas, ready_replicas=item.status.ready_replicas, replicas=item.status.replicas, updated_replicas=item.status.updated_replicas)
        except:
            pass
    return result

def get_pod_status():
    ret = v1.list_namespaced_pod(NAMESPACE, watch=False)
    result = dict()
    for item in ret.items:
        try:
            result[re.sub(r'^' + RELEASENAME + '-', '', item.metadata.labels['app'])] = dict(phase=item.status.phase, host_ip=item.status.host_ip, pod_ip=item.status.pod_ip, start_time=format_time(item.status.start_time))
        except:
            pass
    return result

def get_errors():
    status = get_deployment_status()
    errors = list()
    if 'docassemble' not in status:
        errors.append('docassemble deployment could not be found')
    if 'docassemble-backend' not in status:
        errors.append('docassemble-backed deployment could not be found')
    for deployment, values in status.items():
        try:
            if values['ready_replicas'] < values['replicas']:
                errors.append(deployment + ' deployment not ready: ' + str(values['ready_replicas']) + '/' + str(values['replicas']))
        except:
            errors.append('could not get data on ' + deployment + ' deployment')
    return errors

def ready_response():
    errors = get_errors()
    if len(errors):
        return ("\n".join(errors), 400)
    return('', 200)

def format_time(value):
    try:
        return value.strftime('%Y-%m-%dT%H:%M:%SZ')
    except:
        return None

if __name__ == '__main__':
    app.run(port=80)
