# Sturdy Octo Barnacle

This is a Terraform project for managing Snowflake resources.

## Prerequisites

- Terraform 1.0.0 or higher
- Snowflake account

## Usage

1. Create a `terraform.tfvars` file with the following variables:

```hcl
snowflake_organization = "YOUR_ORGANIZATION"
snowflake_account      = "YOUR_ACCOUNT"
snowflake_user         = "YOUR_USER"
snowflake_password     = "YOUR_PASSWORD"
snowflake_role         = "YOUR_ROLE"
snowflake_passcode     = "YOUR_PASSCODE"
database_name          = "YOUR_DATABASE"
```

2. Run the following commands:

```bash
terraform init
terraform plan
terraform apply
```