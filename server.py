import sys
import signal
from bson import json_util
from datetime import datetime
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient()
db = client['gigiqdb']
jobs_col = db['jobs']

def signal_handler(signal, frame):
	print '\nclosing database...'
	client.close()
	sys.exit(0)

def validate_latlng(latlng):
	if not 0.0 < float(latlng['lat']) < 360.0:
		return False
	elif not 0.0 < float(latlng['lng']) < 360.0:
		return False
	else:
		return True

def validate_accept_job(job_obj):
	try:
		if len(job_obj['service']) == 0:
			raise ValueError('Invalid service name')
		
		if not validate_latlng(json_util.loads(str(job_obj['pickup']))):
			raise ValueError('Invalid pickup location')
		
		if not validate_latlng(json_util.loads(str(job_obj['dropoff']))):
			raise ValueError('Invalid dropoff location')		
		
		return True
	except Exception, e:
		print e

@app.route('/')
def index():
	return 'hello world'

@app.route('/api/jobs', methods=['POST'])
def create_job():
	job_obj = request.get_json(silent=True)
	if validate_accept_job(job_obj):
		job_obj['timestamp'] = datetime.utcnow()
		jobs_col.insert_one(job_obj)
		print str(job_obj)
		return 'success'
	else:
		return 'invalid data'

@app.route('/api/jobs', methods=['GET'])
def read_jobs():
	agg_jobs = [j for j in jobs_col.find()]
	return json_util.dumps(agg_jobs)

@app.route('/api/jobs', methods=['DELETE'])
def delete_jobs():
	res = jobs_col.delete_many({})
	return 'deleted {} jobs.'.format(res.deleted_count)

@app.route('/api/jobs/accept/<job_id>', methods=['POST'])
def accept_job(job_id):
	return 'will accept job: {}.'.format(job_id)

# Heartbeat
@app.route('/api/jobs/search', methods=['GET'])
def search_jobs():
	lat_str = request.args.get('lat', '')
	lng_str = request.args.get('lng', '')
	services = request.args.get('services', '').split(',')

	print 'searching from ({}, {}) for {}'.format(lat_str, lng_str, services)

	try:
		lat = float(lat_str)
		lng = float(lng_str)
		return 'searching from ({}, {}) for {}'.format(lat, lng, services)
	except ValueError, e:
		return 'invalid lat/lng'



if __name__ == "__main__":
	signal.signal(signal.SIGINT, signal_handler)
	app.debug = True
	app.run()