# Vault Authentication Methods Configuration

# OIDC Auth Method (Keycloak)
resource "vault_jwt_auth_backend" "keycloak" {
  description        = "Keycloak OIDC authentication"
  path               = "oidc"
  type               = "oidc"
  oidc_discovery_url = var.keycloak_issuer_url
  oidc_client_id     = var.vault_oidc_client_id
  oidc_client_secret = var.vault_oidc_client_secret
  default_role       = "default"

  tune {
    default_lease_ttl = "1h"
    max_lease_ttl     = "24h"
    token_type        = "default-service"
  }
}

# OIDC Role for Platform Admins
resource "vault_jwt_auth_backend_role" "admin" {
  backend        = vault_jwt_auth_backend.keycloak.path
  role_name      = "admin"
  role_type      = "oidc"
  token_policies = ["admin"]

  user_claim            = "preferred_username"
  groups_claim          = "groups"
  bound_claims = {
    groups = "platform_admin"
  }

  allowed_redirect_uris = [
    "https://${var.portal_host}/vault/ui/vault/auth/oidc/oidc/callback",
    "https://${var.portal_host}/vault/oidc/callback",
    "http://localhost:8250/oidc/callback"
  ]

  token_ttl     = 3600
  token_max_ttl = 86400
}

# OIDC Role for Default Users
resource "vault_jwt_auth_backend_role" "default" {
  backend        = vault_jwt_auth_backend.keycloak.path
  role_name      = "default"
  role_type      = "oidc"
  token_policies = ["reader"]

  user_claim = "preferred_username"

  allowed_redirect_uris = [
    "https://${var.portal_host}/vault/ui/vault/auth/oidc/oidc/callback",
    "https://${var.portal_host}/vault/oidc/callback",
    "http://localhost:8250/oidc/callback"
  ]

  token_ttl     = 3600
  token_max_ttl = 28800
}

# AppRole Auth Method
resource "vault_auth_backend" "approle" {
  type        = "approle"
  path        = "approle"
  description = "AppRole authentication for services"

  tune {
    default_lease_ttl = "1h"
    max_lease_ttl     = "24h"
  }
}

# AppRole for FSC API
resource "vault_approle_auth_backend_role" "fsc_api" {
  backend        = vault_auth_backend.approle.path
  role_name      = "fsc-api"
  token_policies = ["fsc-api"]

  token_ttl     = 3600
  token_max_ttl = 14400

  secret_id_ttl             = 0  # Never expires
  secret_id_num_uses        = 0  # Unlimited uses
  token_num_uses            = 0
  token_bound_cidrs         = []
  secret_id_bound_cidrs     = []
}

# AppRole for Concourse
resource "vault_approle_auth_backend_role" "concourse" {
  backend        = vault_auth_backend.approle.path
  role_name      = "concourse"
  token_policies = ["fsc-concourse"]

  token_ttl     = 3600
  token_max_ttl = 14400

  secret_id_ttl             = 0
  secret_id_num_uses        = 0
  token_num_uses            = 0
}

# Get RoleID and SecretID for FSC API
data "vault_approle_auth_backend_role_id" "fsc_api" {
  backend   = vault_auth_backend.approle.path
  role_name = vault_approle_auth_backend_role.fsc_api.role_name
}

resource "vault_approle_auth_backend_role_secret_id" "fsc_api" {
  backend   = vault_auth_backend.approle.path
  role_name = vault_approle_auth_backend_role.fsc_api.role_name
}

# Get RoleID and SecretID for Concourse
data "vault_approle_auth_backend_role_id" "concourse" {
  backend   = vault_auth_backend.approle.path
  role_name = vault_approle_auth_backend_role.concourse.role_name
}

resource "vault_approle_auth_backend_role_secret_id" "concourse" {
  backend   = vault_auth_backend.approle.path
  role_name = vault_approle_auth_backend_role.concourse.role_name
}
