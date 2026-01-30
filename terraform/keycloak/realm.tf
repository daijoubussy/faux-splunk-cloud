# Keycloak Realm Configuration

resource "keycloak_realm" "faux_splunk" {
  realm   = var.realm_name
  enabled = true

  display_name      = "Faux Splunk Cloud"
  display_name_html = "<div>Faux Splunk Cloud</div>"

  # Login settings
  login_with_email_allowed  = true
  duplicate_emails_allowed  = false
  reset_password_allowed    = true
  edit_username_allowed     = false
  registration_allowed      = true
  registration_email_as_username = false

  # Note: Brute force protection must be configured via Keycloak admin UI
  # The Terraform provider doesn't support these attributes directly

  # Token settings
  access_token_lifespan                    = "1h"
  access_token_lifespan_for_implicit_flow  = "15m"
  sso_session_idle_timeout                 = "8h"
  sso_session_max_lifespan                 = "10h"

  # Security settings
  default_signature_algorithm = "RS256"

  # Theme
  login_theme = "faux-splunk"

  # Internationalization
  internationalization {
    supported_locales = ["en"]
    default_locale    = "en"
  }

  # WebAuthn Policy for regular 2FA
  web_authn_policy {
    relying_party_entity_name         = "Faux Splunk Cloud"
    signature_algorithms              = ["ES256", "RS256"]
    relying_party_id                  = ""
    attestation_conveyance_preference = "not specified"
    authenticator_attachment          = "not specified"
    require_resident_key              = "not specified"
    user_verification_requirement     = "preferred"
    create_timeout                    = 0
    avoid_same_authenticator_register = false
  }

  # WebAuthn Policy for Passwordless
  web_authn_passwordless_policy {
    relying_party_entity_name         = "Faux Splunk Cloud"
    signature_algorithms              = ["ES256", "RS256"]
    relying_party_id                  = ""
    attestation_conveyance_preference = "not specified"
    authenticator_attachment          = "platform"
    require_resident_key              = "Yes"
    user_verification_requirement     = "required"
    create_timeout                    = 0
    avoid_same_authenticator_register = false
  }
}

# Realm roles
resource "keycloak_role" "platform_admin" {
  realm_id    = keycloak_realm.faux_splunk.id
  name        = "platform_admin"
  description = "Platform administrator with full access"
}

resource "keycloak_role" "tenant_admin" {
  realm_id    = keycloak_realm.faux_splunk.id
  name        = "tenant_admin"
  description = "Tenant administrator"
}

resource "keycloak_role" "tenant_user" {
  realm_id    = keycloak_realm.faux_splunk.id
  name        = "tenant_user"
  description = "Standard tenant user"
}

resource "keycloak_role" "customer" {
  realm_id    = keycloak_realm.faux_splunk.id
  name        = "customer"
  description = "Customer role"
}

resource "keycloak_role" "splunk_admin" {
  realm_id    = keycloak_realm.faux_splunk.id
  name        = "splunk_admin"
  description = "Splunk administrator"
}
