# Keycloak Authentication Configuration

# Enable WebAuthn Required Actions
resource "keycloak_required_action" "webauthn_register" {
  realm_id       = keycloak_realm.faux_splunk.id
  alias          = "webauthn-register"
  name           = "Webauthn Register"
  enabled        = true
  default_action = false
  priority       = 50
}

resource "keycloak_required_action" "webauthn_passwordless" {
  realm_id       = keycloak_realm.faux_splunk.id
  alias          = "webauthn-register-passwordless"
  name           = "Webauthn Register Passwordless"
  enabled        = true
  default_action = false
  priority       = 55
}

# Custom authentication flow for browser with WebAuthn option
resource "keycloak_authentication_flow" "browser_with_passkeys" {
  realm_id    = keycloak_realm.faux_splunk.id
  alias       = "browser-with-passkeys"
  description = "Browser flow with passkey support"
}

# Cookie sub-flow (checks if already authenticated)
resource "keycloak_authentication_subflow" "cookie" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_flow.browser_with_passkeys.alias
  alias             = "cookie"
  requirement       = "ALTERNATIVE"
}

resource "keycloak_authentication_execution" "cookie_auth" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_subflow.cookie.alias
  authenticator     = "auth-cookie"
  requirement       = "REQUIRED"
}

# Kerberos execution (optional)
resource "keycloak_authentication_execution" "kerberos" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_flow.browser_with_passkeys.alias
  authenticator     = "auth-spnego"
  requirement       = "DISABLED"
  depends_on        = [keycloak_authentication_subflow.cookie]
}

# Identity Provider Redirector (optional)
resource "keycloak_authentication_execution" "idp_redirector" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_flow.browser_with_passkeys.alias
  authenticator     = "identity-provider-redirector"
  requirement       = "ALTERNATIVE"
  depends_on        = [keycloak_authentication_execution.kerberos]
}

# Forms sub-flow (username/password + 2FA)
resource "keycloak_authentication_subflow" "forms" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_flow.browser_with_passkeys.alias
  alias             = "forms"
  requirement       = "ALTERNATIVE"
  depends_on        = [keycloak_authentication_execution.idp_redirector]
}

resource "keycloak_authentication_execution" "username_password" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_subflow.forms.alias
  authenticator     = "auth-username-password-form"
  requirement       = "REQUIRED"
}

# 2FA conditional sub-flow
resource "keycloak_authentication_subflow" "conditional_2fa" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_subflow.forms.alias
  alias             = "conditional-2fa"
  requirement       = "CONDITIONAL"
  depends_on        = [keycloak_authentication_execution.username_password]
}

resource "keycloak_authentication_execution" "condition_configured" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_subflow.conditional_2fa.alias
  authenticator     = "conditional-user-configured"
  requirement       = "REQUIRED"
}

resource "keycloak_authentication_execution" "webauthn_authenticator" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_subflow.conditional_2fa.alias
  authenticator     = "webauthn-authenticator"
  requirement       = "ALTERNATIVE"
  depends_on        = [keycloak_authentication_execution.condition_configured]
}

resource "keycloak_authentication_execution" "otp_form" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_subflow.conditional_2fa.alias
  authenticator     = "auth-otp-form"
  requirement       = "ALTERNATIVE"
  depends_on        = [keycloak_authentication_execution.webauthn_authenticator]
}

# WebAuthn Passwordless flow (passkey-only login)
resource "keycloak_authentication_subflow" "passkey_only" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_flow.browser_with_passkeys.alias
  alias             = "passkey-only"
  requirement       = "ALTERNATIVE"
  depends_on        = [keycloak_authentication_subflow.forms]
}

resource "keycloak_authentication_execution" "webauthn_passwordless" {
  realm_id          = keycloak_realm.faux_splunk.id
  parent_flow_alias = keycloak_authentication_subflow.passkey_only.alias
  authenticator     = "webauthn-authenticator-passwordless"
  requirement       = "REQUIRED"
}
