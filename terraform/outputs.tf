# Faux Splunk Cloud - Root Outputs

# Keycloak Outputs
output "keycloak_realm_name" {
  description = "Keycloak realm name"
  value       = module.keycloak.realm_name
}

output "saml_metadata_url" {
  description = "SAML metadata URL"
  value       = module.keycloak.saml_metadata_url
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL"
  value       = module.keycloak.oidc_issuer_url
}

# Vault Outputs
output "vault_kv_path" {
  description = "Vault KV secrets path"
  value       = module.vault.kv_mount_path
}

output "vault_transit_key" {
  description = "Vault transit encryption key name"
  value       = module.vault.transit_key_name
}

# AppRole Credentials (for services)
output "fsc_api_vault_role_id" {
  description = "Vault AppRole Role ID for FSC API"
  value       = module.vault.fsc_api_role_id
  sensitive   = true
}

output "fsc_api_vault_secret_id" {
  description = "Vault AppRole Secret ID for FSC API"
  value       = module.vault.fsc_api_secret_id
  sensitive   = true
}

output "concourse_vault_role_id" {
  description = "Vault AppRole Role ID for Concourse"
  value       = module.vault.concourse_role_id
  sensitive   = true
}

output "concourse_vault_secret_id" {
  description = "Vault AppRole Secret ID for Concourse"
  value       = module.vault.concourse_secret_id
  sensitive   = true
}
