# Keycloak Client Configuration

# SAML Client for Platform Authentication
resource "keycloak_saml_client" "faux_splunk_cloud" {
  realm_id  = keycloak_realm.faux_splunk.id
  client_id = "faux-splunk-cloud"
  name      = "Faux Splunk Cloud Platform"

  enabled     = true
  sign_documents = true
  sign_assertions = true
  client_signature_required = false
  signature_algorithm = "RSA_SHA256"

  front_channel_logout = true
  full_scope_allowed   = true

  root_url = "https://${var.portal_host}"
  base_url = "https://${var.portal_host}"
  valid_redirect_uris = [
    "https://${var.portal_host}/*",
    "https://${var.portal_host}/api/v1/auth/saml/acs"
  ]

  master_saml_processing_url = "https://${var.portal_host}/api/v1/auth/saml/acs"

  assertion_consumer_post_url     = "https://${var.portal_host}/api/v1/auth/saml/acs"
  assertion_consumer_redirect_url = "https://${var.portal_host}/api/v1/auth/saml/acs"
  logout_service_post_binding_url = "https://${var.portal_host}/api/v1/auth/saml/slo"
  logout_service_redirect_binding_url = "https://${var.portal_host}/api/v1/auth/saml/slo"

  name_id_format = "email"
  force_name_id_format = true
}

# SAML Protocol Mappers
resource "keycloak_saml_user_property_protocol_mapper" "email" {
  realm_id  = keycloak_realm.faux_splunk.id
  client_id = keycloak_saml_client.faux_splunk_cloud.id
  name      = "email"

  user_property               = "email"
  friendly_name               = "email"
  saml_attribute_name         = "email"
  saml_attribute_name_format  = "Basic"
}

resource "keycloak_saml_user_property_protocol_mapper" "first_name" {
  realm_id  = keycloak_realm.faux_splunk.id
  client_id = keycloak_saml_client.faux_splunk_cloud.id
  name      = "firstName"

  user_property               = "firstName"
  friendly_name               = "givenName"
  saml_attribute_name         = "firstName"
  saml_attribute_name_format  = "Basic"
}

resource "keycloak_saml_user_property_protocol_mapper" "last_name" {
  realm_id  = keycloak_realm.faux_splunk.id
  client_id = keycloak_saml_client.faux_splunk_cloud.id
  name      = "lastName"

  user_property               = "lastName"
  friendly_name               = "surname"
  saml_attribute_name         = "lastName"
  saml_attribute_name_format  = "Basic"
}

resource "keycloak_generic_protocol_mapper" "saml_roles" {
  realm_id        = keycloak_realm.faux_splunk.id
  client_id       = keycloak_saml_client.faux_splunk_cloud.id
  name            = "roles"
  protocol        = "saml"
  protocol_mapper = "saml-role-list-mapper"
  config = {
    "single"                   = "false"
    "attribute.nameformat"     = "Basic"
    "attribute.name"           = "roles"
  }
}

resource "keycloak_saml_user_attribute_protocol_mapper" "tenant_id" {
  realm_id  = keycloak_realm.faux_splunk.id
  client_id = keycloak_saml_client.faux_splunk_cloud.id
  name      = "tenant_id"

  user_attribute              = "tenant_id"
  friendly_name               = "tenant_id"
  saml_attribute_name         = "tenant_id"
  saml_attribute_name_format  = "Basic"
}

# OIDC Client for Vault
resource "keycloak_openid_client" "vault" {
  realm_id  = keycloak_realm.faux_splunk.id
  client_id = "vault"
  name      = "HashiCorp Vault"

  enabled       = true
  access_type   = "CONFIDENTIAL"
  client_secret = var.vault_oidc_secret

  standard_flow_enabled        = true
  implicit_flow_enabled        = false
  direct_access_grants_enabled = false
  service_accounts_enabled     = false

  valid_redirect_uris = [
    "https://${var.portal_host}/vault/ui/vault/auth/oidc/oidc/callback",
    "https://${var.portal_host}/vault/oidc/callback",
    "http://localhost:8250/oidc/callback"
  ]

  web_origins = ["https://${var.portal_host}"]
}

# OIDC Protocol Mapper for Vault groups claim
resource "keycloak_openid_user_realm_role_protocol_mapper" "vault_groups" {
  realm_id  = keycloak_realm.faux_splunk.id
  client_id = keycloak_openid_client.vault.id
  name      = "groups"

  claim_name          = "groups"
  multivalued         = true
  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}

# OIDC Client for Concourse
resource "keycloak_openid_client" "concourse" {
  realm_id  = keycloak_realm.faux_splunk.id
  client_id = "concourse"
  name      = "Concourse CI"

  enabled       = true
  access_type   = "CONFIDENTIAL"
  client_secret = var.concourse_oidc_secret

  standard_flow_enabled        = true
  implicit_flow_enabled        = false
  direct_access_grants_enabled = false
  service_accounts_enabled     = false

  valid_redirect_uris = [
    "https://${var.portal_host}/concourse/sky/issuer/callback"
  ]

  web_origins = ["https://${var.portal_host}"]
}

# OIDC Protocol Mapper for Concourse groups claim
resource "keycloak_openid_user_realm_role_protocol_mapper" "concourse_groups" {
  realm_id  = keycloak_realm.faux_splunk.id
  client_id = keycloak_openid_client.concourse.id
  name      = "groups"

  claim_name          = "groups"
  multivalued         = true
  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}
