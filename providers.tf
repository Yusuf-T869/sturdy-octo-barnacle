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
  password                 = var.use_remote_auth == false ? var.snowflake_password : null
  authenticator            = var.use_remote_auth == true ? "SNOWFLAKE_JWT" : null
  private_key              = var.use_remote_auth == true ? file(var.snowflake_private_key_path) : null
  role                     = var.snowflake_role
  preview_features_enabled = ["snowflake_table_resource", "snowflake_dynamic_table_resource"]
}

variable "use_remote_auth" {
  description = "Use remote auth (private key) instead of local (password)"
  type        = bool
  default     = false
}

variable "snowflake_private_key_path" {
  description = "Path to the Snowflake private key file"
  type        = string
}
