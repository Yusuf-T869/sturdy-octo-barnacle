
resource "snowflake_table" "table" {
  name     = var.table_name
  schema   = snowflake_schema.schema.name
  database = var.database_name

  column {
    name = "id"
    type = "INT"
  }

  column {
    name = "name"
    type = "VARCHAR(255)"
  }

  column {
    name = "price"
    type = "DECIMAL(10, 2)"
  }

  column {
    name = "description"
    type = "VARCHAR(1000)"
  }

  column {
    name = "remark"
    type = "VARCHAR(100)"
  }
}