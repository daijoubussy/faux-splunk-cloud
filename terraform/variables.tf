# Faux Splunk Cloud - Root Variables

# General
variable "portal_host" {
  description = "Portal hostname"
  type        = string
  default     = "portal.fsc.orb.local"
}

# Keycloak Configuration
variable "keycloak_url" {
  description = "Keycloak server URL"
  type        = string
  default     = "http://keycloak:8080"
}

variable "keycloak_admin_user" {
  description = "Keycloak admin username"
  type        = string
  default     = "admin"
}

variable "keycloak_admin_password" {
  description = "Keycloak admin password"
  type        = string
  sensitive   = true
}

variable "keycloak_realm" {
  description = "Keycloak realm name"
  type        = string
  default     = "faux-splunk"
}

variable "default_admin_email" {
  description = "Default admin user email"
  type        = string
  default     = "admin@faux-splunk.local"
}

variable "default_admin_password" {
  description = "Default admin user password"
  type        = string
  sensitive   = true
  default     = "admin"
}

# Vault Configuration
variable "vault_address" {
  description = "Vault server address"
  type        = string
  default     = "http://vault:8200"
}

variable "vault_root_token" {
  description = "Vault root token"
  type        = string
  sensitive   = true
}

# OIDC Secrets
variable "vault_oidc_secret" {
  description = "OIDC client secret for Vault"
  type        = string
  sensitive   = true
  default     = "vault-oidc-secret"
}

variable "concourse_oidc_secret" {
  description = "OIDC client secret for Concourse"
  type        = string
  sensitive   = true
  default     = "concourse-oidc-secret"
}
