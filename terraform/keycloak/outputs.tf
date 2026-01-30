# Keycloak Terraform Outputs

output "realm_id" {
  description = "Keycloak realm ID"
  value       = keycloak_realm.faux_splunk.id
}

output "realm_name" {
  description = "Keycloak realm name"
  value       = keycloak_realm.faux_splunk.realm
}

output "saml_client_id" {
  description = "SAML client ID for platform authentication"
  value       = keycloak_saml_client.faux_splunk_cloud.client_id
}

output "vault_oidc_client_id" {
  description = "OIDC client ID for Vault"
  value       = keycloak_openid_client.vault.client_id
}

output "concourse_oidc_client_id" {
  description = "OIDC client ID for Concourse"
  value       = keycloak_openid_client.concourse.client_id
}

output "saml_metadata_url" {
  description = "SAML metadata URL for the realm"
  value       = "https://${var.portal_host}/realms/${var.realm_name}/protocol/saml/descriptor"
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL for the realm"
  value       = "https://${var.portal_host}/realms/${var.realm_name}"
}

output "admin_user_id" {
  description = "Admin user ID"
  value       = keycloak_user.admin.id
}

output "authentication_flow_alias" {
  description = "Custom browser authentication flow with passkeys"
  value       = keycloak_authentication_flow.browser_with_passkeys.alias
}
