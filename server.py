import sys
import signal

from bson import json_util
from bson.objectid import ObjectId
from datetime import datetime
from haversine import haversine
import random

from pymongo import GEOSPHERE
from pymongo import MongoClient
from flask import Flask, request

app = Flask(__name__)
client = MongoClient()
db = client['gigiqdb']
jobs_col = db['jobs']

jobs_col.ensure_index([('pickup', GEOSPHERE)])
jobs_col.ensure_index([('dropoff', GEOSPHERE)])

def signal_handler(signal, frame):
	print '\nclosing database...'
	client.close()
	sys.exit(0)

def row_array(cursor):
	return [j for j in cursor]

def validate_latlng(latlng):
	if not -90.0 < float(latlng['lat']) < 90.0:
		return False
	elif not -180.0 < float(latlng['lng']) < 180.0:
		return False
	else:
		return True

def validate_accept_job(job_obj):
	try:
		if len(job_obj['service']) == 0:
			raise ValueError('Invalid service name')

		if len(job_obj['type']) == 0:
			raise ValueError('Invalid service name')
		
		if not validate_latlng(job_obj['pickup']):
			raise ValueError('Invalid pickup location')
		
		if not validate_latlng(job_obj['dropoff']):
			raise ValueError('Invalid dropoff location')		
		
		return True
	except Exception, e:
		print e

def job_cost_factory(lat, lng):
	pos = (lat, lng)
	travel_cost = -0.3
	delivery_cost = 1.0
	def cost(job):
		pickup_tuple = (job['pickup']['lat'], job['pickup']['lng'])
		dropoff_tuple = (job['dropoff']['lat'], job['dropoff']['lng'])
		pickup_dist = haversine(pos, pickup_tuple)
		delivery_dist = haversine(pickup_tuple, dropoff_tuple)
		total_comp = travel_cost * (pickup_dist + delivery_dist) + delivery_cost * (delivery_dist)
		return total_comp / (pickup_dist + delivery_dist)
	return cost

def job_pay(job):
	pickup_tuple = (job['pickup']['lat'], job['pickup']['lng'])
	dropoff_tuple = (job['dropoff']['lat'], job['dropoff']['lng'])
	delivery_dist = haversine(pickup_tuple, dropoff_tuple)
	pay = random.uniform(1.5, 4.0) * delivery_dist
	job['pay'] = pay
	return job

def job_duration(job):
	pickup_tuple = (job['pickup']['lat'], job['pickup']['lng'])
	dropoff_tuple = (job['dropoff']['lat'], job['dropoff']['lng'])
	delivery_dist = haversine(pickup_tuple, dropoff_tuple)
	duration =  delivery_dist / random.uniform(25, 50) * 60.0
	job['duration'] = duration
	return job

def error_response(msg):
	resp = {
		'completion': 'error',
		'data': msg
	}
	return json_util.dumps(resp)

def success_response(data):
	resp = {
		'completion': 'success',
		'data': data
	}
	return json_util.dumps(resp)


@app.route('/')
def index():
	return success_response('hello world')

@app.route('/api/jobs', methods=['POST'])
def create_job():
	job_obj = request.get_json(silent=True)
	if validate_accept_job(job_obj):
		job_obj['timestamp'] = datetime.utcnow()
		job_obj = job_pay(job_obj)
		job_obj = job_duration(job_obj)
		jobs_col.insert_one(job_obj)
		return success_response('success')
	else:
		return error_response('invalid data')

@app.route('/api/jobs', methods=['GET'])
def read_jobs():
	agg_jobs = [j for j in jobs_col.find()]
	return success_response(agg_jobs)

@app.route('/api/jobs', methods=['DELETE'])
def delete_jobs():
	res = jobs_col.delete_many({})
	return success_response('deleted {} jobs.'.format(res.deleted_count))

@app.route('/api/jobs/accept/<job_id>', methods=['POST'])
def accept_job(job_id):
	result = jobs_col.delete_one({'_id': ObjectId(job_id)})
	return success_response(str(result.deleted_count))

	# return error_response('will accept job: {}.'.format(job_id))


def near_find_options(lat, lng, min_dist, max_dist):
	return {
		'$near': {
			'$geometry': {
				'type': "Point" ,
				'coordinates': [lat , lng]
			},
			'$maxDistance': max_dist,
			'$minDistance': min_dist
		}
	}

# Heartbeat
@app.route('/api/jobs/search', methods=['GET'])
def search_jobs():
	lat_str = request.args.get('lat', '')
	lng_str = request.args.get('lng', '')
	services = request.args.get('services', '').split(',')

	try:
		lat = float(lat_str)
		lng = float(lng_str)

		query_filter = {'pickup': near_find_options(lat, lng, 0, 100000)}

		if len(services) > 0:
			query_filter['service'] = {'$in': services}

		jobs = row_array(jobs_col.find(limit=20, filter=query_filter))
		sorted_jobs = sorted(jobs, key=job_cost_factory(lat, lng), reverse=True)

		return success_response(sorted_jobs[0:5])
	except ValueError, e:
		return error_response('invalid lat/lng')

# @app.route('/api/services', methods=['GET'])
# def all_services():
# 	services = row_array(jobs_col.distinct('service'))
# 	return success_response(services)


if __name__ == "__main__":
	signal.signal(signal.SIGINT, signal_handler)
	app.debug = True
	app.run(host="0.0.0.0", port=5100)
