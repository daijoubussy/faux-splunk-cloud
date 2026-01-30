# Keycloak Terraform Variables
# Note: Provider credentials are configured at root level

variable "realm_name" {
  description = "Name of the Keycloak realm"
  type        = string
  default     = "faux-splunk"
}

variable "portal_host" {
  description = "Portal hostname for redirect URLs"
  type        = string
  default     = "portal.fsc.orb.local"
}

variable "default_admin_email" {
  description = "Email for the default admin user"
  type        = string
  default     = "admin@faux-splunk.local"
}

variable "default_admin_password" {
  description = "Password for the default admin user"
  type        = string
  sensitive   = true
  default     = "admin"
}

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
