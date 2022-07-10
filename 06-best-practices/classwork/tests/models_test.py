from pathlib import Path
import model

def read_text(file):
    test_dir = Path(__file__).parent
    with open(test_dir / file, 'rt', encoding='utf8') as f:
        return f.read().strip()

def test_prepare_features():
    model_service = model.ModelService(None)
    ride = {
        "PULocationID": 130,
        "DOLocationID": 205,
        "trip_distance": 3.66
    }
    actual_features = model_service.prepare_features(ride)
    expected_features = {
        "PU_DO": "130_205",
        "trip_distance": 3.66
    }
    assert actual_features == expected_features
    
def test_base64_decode():
    base64_input = read_text("data.b64")
    actual_result = model.base64_decode(base64_input)

    expected_result = {
        "ride": {
            "PULocationID": 130,
            "DOLocationID": 205,
            "trip_distance": 3.66
        }, 
        "ride_id": 256
    }
    assert actual_result == expected_result

class ModelMock:
    
    def __init__(self, value):
        self.value = value
    
    def predict(self, X):
        n = len(X)
        return [self.value] * n

    
def test_predict():
    model_mock = ModelMock(10.0)
    model_service = model.ModelService(model_mock)
    features = {
        "PU_DO": "130_205",
        "trip_distance": 3.66
    }
    actual_prediction = model_service.predict(features)
    expected_result = 10.0
    assert actual_prediction == expected_result
    
def test_lambda_handler():
    model_mock = ModelMock(10.0)
    model_version = "123"
    model_service = model.ModelService(model_mock, model_version)
    event = {
        "Records": [{
            "kinesis": {
                "data": read_text("data.b64"),
            }
        }]
    }
    actual_predictions = model_service.lambda_handler(event)
    expected_predictions = {
        "predictions": [
            {
                "model": "ride_duration_prediction_model", 
                "version": model_version, 
                "prediction": {"ride_duration": 10.0, "ride_id": 256}
            }
        ]
    }
    assert actual_predictions == expected_predictions