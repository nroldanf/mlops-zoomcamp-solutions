# Workflow Orchestration

Automate, schedule, retry and monitor pipelines like the one build in past section [02-tracking](../02-tracking/README.md). Also, the idea is to provide observability so you can fix pipelines that fail.

Pipelines can fail many points, so, according to pipeline dependencies, some of the steps must not execute if a upstream task fails. 

One of the goal of workflow orchestration is to **minimize** the impact of the errors, and fail gracefully if they happen.

Also, is to eliminate negative engineering; don't spend too much time coding for failure to happen.

## Negative Engineering

Coding against failure/negative scenarios from happening.

## Prefect for workflow orchestration

- Open source workflow orchestration
- Python Based
- Modern Data stack, i.e. Py data ecosystem
- Native Dask integration
- Very active community (slack)
- Prefect Cloud/Prefect Server
- Prefect Orion = Prefect 2.0 / Prefect Core = 1.0

## Prefect Orion

- Decorators for functions to define **tasks** and **flows**.
- Observable orchestration rules.

```python
from prefect import flow, task
from typing import List
import httpx

@task(retries=3)
def get_stars(repo: str):
    url = f"https://api.github.com/repos/{repo}"
    count = httpx.get(url).json()["stargazers_count"]
    print(f"{repo} has {count} stars!")

# wraps the task
@flow(name="Github Stars)
def github_stars(repos: List[str]):
    for repo in repos:
        get_stars(repo)

# Run the flow
github_stars(
    [
        "PrefectHQ/Prefect",
        "PrefectHQ/miter-design"
    ]
)
```

## How to use prefect?

Under the hood, by wrapping functions as a task or a flow, we are adding observability.

Start the prefect server:
```
prefect orion start (--host 0.0.0.0)
```

Prefect uses pydantic to validate parameters. Parameters in task and flow functions must be annotated for this feature to work. Unless is a `str`, almost anything can be coarsed into an string, so this feature doesn't work gracefully when this happens.

## Prefect server remotely

Start a VM (could be an EC2 instance). I used latest free tier ubuntu instance (22 at the time) and `t3.xlarge`.

Login into the instance using ssh. Inside the instance do the following steps.

**Note**: Use an environment to install prefect, could be a conda environment.

Install conda:
```
wget <search in https://www.anaconda.com/products/distribution x86 linux dist and copy url>
bash <file>
conda create -n mlops python=3.9
conda activate mlops
```


Install `prefect`:
```
sudo apt update
sudo apt install python3-pip
python3 -m pip install prefect==2.0b5
```

```
prefect config set PREFECT_ORION_UI_API_URL="http://{public-ip}:4200/api"
# to confirm the change
prefect config view
```

If you incur in a bug where URL is not updated:
```
prefect config unset PREFECT_ORION_UI_API_URL
```

Start the server:
```
prefect orion start --host 0.0.0.0
```

To start logging flow and task runs against remote server (this on your local machine)
```
prefect config set PREFECT_API_URL="http://{public-ip}:4200/api"
```

There is also a Prefect cloud, where they host prefect and add an authentication layer.

## Prefect storage

List all configured storages:
```
prefect storage ls
```

Create a storage:
```
prefect storage create
```

## Prefect Deployment

Have the option to deploy the flow using locally, docker (as a container) or k8s (as a pod).

Tags are used for filtering or assigning a GPU instance for this specific flow.

To create a deployment:
```
prefect deployment create model_training.py
```

Still, even if you created a deployment you need to provide where the flow is going to run.

## Prefect agent and work queues

Work queue are just queues.

Agent is attached to queues and is the one that looks for work to do `every 5 seconds`, they poll a specific work queue for new work.

```
prefect work-queue preview 212bc626-d80a-489f-834a-0f14733014d5
```

To spin up an agent:
```
prefect agent start <queue-id>
# e.g.
prefect agent start 212bc626-d80a-489f-834a-0f14733014d5
```

For example, if we use `a docker flow runner` the agent will be the one responsible for spinning up a docker container and run the flow inside of it.


## Homework

A data scientist in your team handed it to you a script and your job is schedule the running of training script using a workflow orchestration - Prefect in this case. Below are the requirements. Do not implement them yet, we will do so in this exercise. Just understand the goal.

1. The training flow will be run every month.
2. The flow will take in a parameter called date which will be a datetime.
a. date should default to None
b. If date is None, set date as the current day. Use the data from 2 months back as the training data and the data from the previous month as validation data.
c. If date is passed, get 2 months before the date as the training data, and the previous month as validation data.
d. As a concrete example, if the date passed is "2021-03-15", the training data should be "fhv_tripdata_2021-01.parquet" and the validation file will be "fhv_trip_data_2021-02.parquet"

3. Save the model as "model-{date}.bin" where date is in YYYY-MM-DD. Note that date here is the value of the flow parameter. In practice, this setup makes it very easy to get the latest model to run predictions because you just need to get the most recent one.
4. In this example we use a DictVectorizer. That is needed to run future data through our model. Save that as "dv-{date}.b". Similar to above, if the date is 2021-03-15, the files output should be model-2021-03-15.bin and dv-2021-03-15.b.

In order, this homework assignment will be about:

1. Converting the script to a Flow
2. Changing the parameters to take in a date. Making this parameter dynamic.
3. Scheduling a batch training job that outputs the latest model somewhere

## Resources

- **Cron tab**: To test cron expressions. https://crontab.guru/
