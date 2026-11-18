terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

  }
  cloud {
    organization = "KaiFV"
    workspaces {
      name = "KFVWorkspace"
    }
  }
  required_version = ">= 0.14.9"
}

provider "aws" {
  region = "us-east-1"
}

data "aws_iam_role" "lab_role" {
  name = "LabRole"
}
resource "aws_lambda_function" "test_lambda" {
  filename      = "stopEC2.zip"
  function_name = "kai_lambda_function_name"
  role          = data.aws_iam_role.lab_role.arn
  runtime       = "python3.9"
  handler       = "stopEC2.lambda_handler"
} 

resource "aws_lambda_function" "start_ec2" {
  filename      = "startEC2/startEC2.zip"
  function_name = "kai_start_ec2_function"
  role          = data.aws_iam_role.lab_role.arn
  runtime       = "python3.13"
  handler       = "startEC2.lambda_handler"
}