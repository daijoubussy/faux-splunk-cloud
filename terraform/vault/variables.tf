# Vault Terraform Variables
# Note: Provider credentials are configured at root level

# Keycloak OIDC Configuration
variable "keycloak_issuer_url" {
  description = "Keycloak OIDC issuer URL"
  type        = string
  default     = "https://portal.fsc.orb.local/realms/faux-splunk"
}

variable "vault_oidc_client_id" {
  description = "Vault OIDC client ID in Keycloak"
  type        = string
  default     = "vault"
}

variable "vault_oidc_client_secret" {
  description = "Vault OIDC client secret"
  type        = string
  sensitive   = true
}

variable "portal_host" {
  description = "Portal hostname for callback URLs"
  type        = string
  default     = "portal.fsc.orb.local"
}

# Transit Configuration
variable "transit_key_name" {
  description = "Name of the transit encryption key"
  type        = string
  default     = "fsc"
}
