import os
import pickle

import requests
from flask import Flask, request, jsonify

from pymongo import MongoClient

MODEL_FILE = os.getenv('MODEL_FILE', 'lin_reg.bin')
MONGODB_ADDRESS = os.getenv("MONGODB_ADDRESS", "mongodb://127.0.0.1:27017")
EVIDENTLY_SERVICE_ADDRESS = os.getenv('EVIDENTLY_SERVICE', 'http://127.0.0.1:5000')

with open(MODEL_FILE, 'rb') as f_in:
    dv, model = pickle.load(f_in)
    
app = Flask('duration')
mongo_client = MongoClient(MONGODB_ADDRESS)
db = mongo_client.get_database("prediction_service")
# table in the database
collection = db.get_collection("data")

@app.route('/predict', methods=['POST'])
def predict():
    record = request.get_json()
    record['PU_DO'] = '%s_%s' % (record['PULocationID'], record['DOLocationID'])
    X = dv.transform([record])
    y_pred = model.predict(X)
    result = {
        'duration': float(y_pred),
    }
    save_to_db(record, float(y_pred))
    send_to_evidently_service(record, float(y_pred))
    return jsonify(result)

def save_to_db(record: dict, prediction: float):
    '''
    Save input data and prediciton into MongoDB database table.
    :param: record: input data.
    :param: prediction: prediction data.
    '''
    rec = record.copy()
    rec['prediction'] = prediction
    collection.insert_one(rec)
    
def send_to_evidently_service(record: dict, prediction: float):
    '''
    Send data for metrics calculation with evidently.
    :param: record: input data.
    :param: prediction: prediction data.
    '''
    rec = record.copy()
    rec['prediction'] = prediction
    requests.post(f"{EVIDENTLY_SERVICE_ADDRESS}/iterate/taxi", json=[rec])

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=9696)