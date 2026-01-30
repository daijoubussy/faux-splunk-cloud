# Vault Terraform Outputs

# AppRole credentials for FSC API
output "fsc_api_role_id" {
  description = "AppRole Role ID for FSC API"
  value       = data.vault_approle_auth_backend_role_id.fsc_api.role_id
  sensitive   = true
}

output "fsc_api_secret_id" {
  description = "AppRole Secret ID for FSC API"
  value       = vault_approle_auth_backend_role_secret_id.fsc_api.secret_id
  sensitive   = true
}

# AppRole credentials for Concourse
output "concourse_role_id" {
  description = "AppRole Role ID for Concourse"
  value       = data.vault_approle_auth_backend_role_id.concourse.role_id
  sensitive   = true
}

output "concourse_secret_id" {
  description = "AppRole Secret ID for Concourse"
  value       = vault_approle_auth_backend_role_secret_id.concourse.secret_id
  sensitive   = true
}

# Mount paths for reference
output "kv_mount_path" {
  description = "Path to the KV secrets engine"
  value       = vault_mount.fsc_kv.path
}

output "transit_mount_path" {
  description = "Path to the Transit secrets engine"
  value       = vault_mount.transit.path
}

output "transit_key_name" {
  description = "Name of the Transit encryption key"
  value       = vault_transit_secret_backend_key.fsc.name
}

# OIDC configuration for reference
output "oidc_mount_path" {
  description = "Path to the OIDC auth method"
  value       = vault_jwt_auth_backend.keycloak.path
}
