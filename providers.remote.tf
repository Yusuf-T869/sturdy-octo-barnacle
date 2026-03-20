
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 2.0"
    }
  }
}

provider "snowflake" {
  organization_name        = var.snowflake_organization
  account_name             = var.snowflake_account
  user                     = var.snowflake_user
  authenticator            = "SNOWFLAKE_JWT"
  private_key              = file(var.snowflake_private_key_path)
  role                     = var.snowflake_role
  preview_features_enabled = ["snowflake_table_resource", "snowflake_dynamic_table_resource"]
}

variable "snowflake_private_key_path" {
  description = "Path to the Snowflake private key file"
  type        = string
}
