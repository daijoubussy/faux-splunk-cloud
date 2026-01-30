# Vault Terraform Configuration for Faux Splunk Cloud
# Declarative infrastructure-as-code for Vault setup
#
# This configuration initializes Vault with:
# - OIDC auth via Keycloak for UI/CLI access
# - AppRole auth for API and Concourse service accounts
# - KV secrets engine for credential storage
# - Transit engine for encryption-as-a-service
# - Policies for role-based access control

# Provider configuration is in the root module
terraform {
  required_providers {
    vault = {
      source = "hashicorp/vault"
    }
  }
}
