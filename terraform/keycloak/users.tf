# Keycloak Users Configuration

# Default Admin User
resource "keycloak_user" "admin" {
  realm_id = keycloak_realm.faux_splunk.id
  username = "admin"
  enabled  = true

  email          = var.default_admin_email
  email_verified = true
  first_name     = "Platform"
  last_name      = "Admin"

  initial_password {
    value     = var.default_admin_password
    temporary = false
  }
}

# Admin role assignments
resource "keycloak_user_roles" "admin_roles" {
  realm_id = keycloak_realm.faux_splunk.id
  user_id  = keycloak_user.admin.id

  role_ids = [
    keycloak_role.platform_admin.id,
    keycloak_role.splunk_admin.id,
  ]
}

# Default Customer User
resource "keycloak_user" "customer" {
  realm_id = keycloak_realm.faux_splunk.id
  username = "customer"
  enabled  = true

  email          = "customer@faux-splunk.local"
  email_verified = true
  first_name     = "Test"
  last_name      = "Customer"

  initial_password {
    value     = "customer"
    temporary = false
  }
}

# Customer role assignment
resource "keycloak_user_roles" "customer_roles" {
  realm_id = keycloak_realm.faux_splunk.id
  user_id  = keycloak_user.customer.id

  role_ids = [
    keycloak_role.tenant_user.id,
  ]
}
