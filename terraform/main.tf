# Faux Splunk Cloud - Root Terraform Configuration
#
# This is the root module that orchestrates all infrastructure:
# - Keycloak realm and authentication setup
# - Vault secrets management
#
# Usage:
#   cd terraform
#   terraform init
#   terraform plan -var-file=../terraform.tfvars
#   terraform apply -var-file=../terraform.tfvars

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    keycloak = {
      source  = "mrparkers/keycloak"
      version = "~> 4.4"
    }
    vault = {
      source  = "hashicorp/vault"
      version = "~> 4.0"
    }
  }
}

# Configure providers at root level
provider "keycloak" {
  url       = var.keycloak_url
  client_id = "admin-cli"
  username  = var.keycloak_admin_user
  password  = var.keycloak_admin_password
}

provider "vault" {
  address = var.vault_address
  token   = var.vault_root_token
}

# Keycloak Module
module "keycloak" {
  source = "./keycloak"

  # Provider is configured at root level, just pass resource config
  realm_name              = var.keycloak_realm
  portal_host             = var.portal_host
  default_admin_email     = var.default_admin_email
  default_admin_password  = var.default_admin_password
  vault_oidc_secret       = var.vault_oidc_secret
  concourse_oidc_secret   = var.concourse_oidc_secret
}

# Vault Module (depends on Keycloak for OIDC)
module "vault" {
  source = "./vault"

  # Provider is configured at root level, just pass resource config
  keycloak_issuer_url      = module.keycloak.oidc_issuer_url
  vault_oidc_client_id     = module.keycloak.vault_oidc_client_id
  vault_oidc_client_secret = var.vault_oidc_secret
  portal_host              = var.portal_host

  depends_on = [module.keycloak]
}
