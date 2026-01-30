# Keycloak Terraform Configuration for Faux Splunk Cloud
# Declarative infrastructure-as-code for Keycloak realm setup
#
# This configuration creates:
# - faux-splunk realm with enterprise security settings
# - SAML client for platform authentication
# - OIDC clients for Vault and Concourse
# - Realm roles for RBAC
# - Default admin and customer users
# - WebAuthn/Passkey authentication configuration

# Provider configuration is in the root module
terraform {
  required_providers {
    keycloak = {
      source = "mrparkers/keycloak"
    }
  }
}
