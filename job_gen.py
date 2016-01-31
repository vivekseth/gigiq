import time
import json
import math
import random
import requests

CENTER_LAT = 40.427951
CENTER_LNG = -74.580549
MAX_DIST = 20

SERVICE_LIST = ['UBER', 'LYFT']

def random_point(lat1, lon1, max_dist):
	R = 6378.1 #Radius of the Earth
	brng = math.radians(random.uniform(0, 360))
	d = random.uniform(0.1, max_dist)

	lat1 = math.radians(lat1) #Current lat point converted to radians
	lon1 = math.radians(lon1) #Current long point converted to radians

	lat2 = math.asin( math.sin(lat1)*math.cos(d/R) +
	     math.cos(lat1)*math.sin(d/R)*math.cos(brng))

	lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(d/R)*math.cos(lat1),
	             math.cos(d/R)-math.sin(lat1)*math.sin(lat2))

	lat2 = math.degrees(lat2)
	lon2 = math.degrees(lon2)

	return {'lat': lat2, 'lng': lon2}

def random_service():
	return random.sample(SERVICE_LIST, 1)[0]

def send_job_req():
	data = {
		'service': random_service(),
		'pickup': random_point(CENTER_LAT, CENTER_LNG, MAX_DIST),
		'dropoff': random_point(CENTER_LAT, CENTER_LNG, MAX_DIST),
	}
	headers = {'Content-Type': 'application/json'}
	r = requests.post("http://localhost:5000/api/jobs", data=json.dumps(data), headers=headers)
	print r.text

send_job_req()