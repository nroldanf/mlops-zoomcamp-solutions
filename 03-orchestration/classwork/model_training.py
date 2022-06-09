import mlflow
import pickle
import pandas as pd
import xgboost as xgb
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
from hyperopt.pyll import scope
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import mean_squared_error

from prefect import flow, task
from prefect.task_runners import SequentialTaskRunner

@task
def read_dataframe(filename: str):
    df = pd.read_parquet(filename)

    df.lpep_dropoff_datetime = pd.to_datetime(df.lpep_dropoff_datetime)
    df.lpep_pickup_datetime = pd.to_datetime(df.lpep_pickup_datetime)

    df['duration'] = df.lpep_dropoff_datetime - df.lpep_pickup_datetime
    df.duration = df.duration.apply(lambda td: td.total_seconds() / 60)

    df = df[(df.duration >= 1) & (df.duration <= 60)]

    categorical = ['PULocationID', 'DOLocationID']
    df[categorical] = df[categorical].astype(str)
    
    return df

@task
def add_features(df_train, df_val):

    df_train['PU_DO'] = df_train['PULocationID'] + '_' + df_train['DOLocationID']
    df_val['PU_DO'] = df_val['PULocationID'] + '_' + df_val['DOLocationID']
    
    categorical = ['PU_DO']
    numerical = ['trip_distance']

    dv = DictVectorizer()

    train_dicts = df_train[categorical + numerical].to_dict(orient='records')
    X_train = dv.fit_transform(train_dicts)

    val_dicts = df_val[categorical + numerical].to_dict(orient='records')
    X_val = dv.transform(val_dicts)
    
    target = 'duration'
    y_train = df_train[target].values
    y_val = df_val[target].values
    
    return  X_train, X_val, y_train, y_val, dv

# @task
# def parse_matrix(X, y):
#     matrix = xgb.DMatrix(X, label=y)
#     return matrix

@task
def train_model_search(train, valid, y_val):
    def objective(params):
        with mlflow.start_run():
            mlflow.set_tag("model", "xgboost")
            mlflow.log_params(params)
            booster = xgb.train(
                params=params,
                dtrain=train,
                num_boost_round=100,
                evals=[(valid, 'validation')],
                early_stopping_rounds=50
            )
            y_pred = booster.predict(valid)
            rmse = mean_squared_error(y_val, y_pred, squared=False)
            mlflow.log_metric("rmse", rmse)

        return {'loss': rmse, 'status': STATUS_OK}
    
    search_space = {
        'max_depth': scope.int(hp.quniform('max_depth', 4, 100, 1)),
        'learning_rate': hp.loguniform('learning_rate', -3, 0),
        'reg_alpha': hp.loguniform('reg_alpha', -5, -1),
        'reg_lambda': hp.loguniform('reg_lambda', -6, -1),
        'min_child_weight': hp.loguniform('min_child_weight', -1, 3),
        'objective': 'reg:linear',
        'seed': 42
    }
    best_params = fmin(
        fn=objective,
        space=search_space,
        algo=tpe.suggest,
        max_evals=1,
        trials=Trials()
    )
    best_params["max_depth"] = int(best_params["max_depth"])
    return best_params

@task
def train_best_model(train, valid, y_val, dv, best_params: dict):
    with mlflow.start_run():
        
        mlflow.log_params(best_params)

        booster = xgb.train(
            params=best_params,
            dtrain=train,
            num_boost_round=100,
            evals=[(valid, 'validation')],
            early_stopping_rounds=50
        )

        y_pred = booster.predict(valid)
        rmse = mean_squared_error(y_val, y_pred, squared=False)
        mlflow.log_metric("rmse", rmse)

        with open("models/preprocessor.b", "wb") as f_out:
            pickle.dump(dv, f_out)
        mlflow.log_artifact("models/preprocessor.b", artifact_path="preprocessor")

        mlflow.xgboost.log_model(booster, artifact_path="models_mlflow")

@flow(task_runner=SequentialTaskRunner())
def main(
        train_data_path: str='../data/green_tripdata_2021-01.parquet', 
        val_data_path: str='../data/green_tripdata_2021-02.parquet'
    ):
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("nyc-taxi-experiment")
    
    df_train = read_dataframe(train_data_path)
    df_val = read_dataframe(val_data_path)
    
    X_train, X_val, y_train, y_val, dv  = add_features(df_train, df_val).result()
    train = xgb.DMatrix(X_train, label=y_train)
    valid = xgb.DMatrix(X_val, label=y_val)
    # train = parse_matrix(X_train, y_train)
    # valid = parse_matrix(X_val, y_val)
    
    best_params = train_model_search(train, valid, y_val)
    train_best_model(train, valid, y_val, dv, best_params)
    
    
if __name__ == "__main__":
    main()