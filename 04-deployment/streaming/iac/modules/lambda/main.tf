resource "aws_lambda_function" "kinesis_lambda" {
  function_name = "mlflow_kinesis_lambda"
  image_uri     = var.image_uri
  package_type  = "Image"
  role          = aws_iam_role.lambda_for_kinesis.arn

  environment {
    variables = {
      PREDICTIONS_STREAM_NAME = var.source_stream_name
      MODEL_BUCKET            = var.model_bucket
      RUN_ID                  = var.mlflow_run_id
    }
  }
  timeout = 180
  memory_size = 1024
}

# Lambda Invoke & Event Source Mapping
resource "aws_lambda_function_event_invoke_config" "kinesis_lambda_event" {
  function_name                = aws_lambda_function.kinesis_lambda.function_name
  maximum_event_age_in_seconds = 60
  maximum_retry_attempts       = 0
}

resource "aws_lambda_event_source_mapping" "kinesis_mapping" {
  event_source_arn  = var.source_stream_arn
  function_name     = aws_lambda_function.kinesis_lambda.arn
  starting_position = "LATEST"
  depends_on = [
    aws_iam_role_policy_attachment.kinesis_processing
  ]
}