#!/bin/bash
#
# Keycloak Realm Initialization Script
#
# This script automatically sets up the faux-splunk realm in Keycloak with:
# - SAML client for the platform
# - Enterprise roles (platform_admin, tenant_admin, tenant_user)
# - Default admin user
#
# Usage: This script runs as an init container in docker-compose
#

set -e

# Configuration from environment
KEYCLOAK_URL="${KEYCLOAK_URL:-http://keycloak:8080}"
KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
REALM_NAME="${FSC_KEYCLOAK_REALM:-faux-splunk}"
PLATFORM_URL="${FSC_HOSTNAME:-localhost}"
DEFAULT_ADMIN_EMAIL="${FSC_DEFAULT_ADMIN_EMAIL:-admin@faux-splunk.local}"
DEFAULT_ADMIN_PASSWORD="${FSC_DEFAULT_ADMIN_PASSWORD:-admin}"

echo "=========================================="
echo "Keycloak Realm Initialization"
echo "=========================================="
echo "Keycloak URL: ${KEYCLOAK_URL}"
echo "Realm: ${REALM_NAME}"
echo "Platform URL: ${PLATFORM_URL}"
echo ""

# Wait for Keycloak to be ready
echo "Waiting for Keycloak to be ready..."
max_attempts=60
attempt=0
until curl -sf "${KEYCLOAK_URL}/health/ready" > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "ERROR: Keycloak did not become ready in time"
        exit 1
    fi
    echo "  Attempt ${attempt}/${max_attempts}..."
    sleep 5
done
echo "Keycloak is ready!"

# Get admin token
echo ""
echo "Authenticating with Keycloak..."
echo "  Using admin: ${KEYCLOAK_ADMIN}"
TOKEN_RESPONSE=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${KEYCLOAK_ADMIN}" \
    -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
    -d "grant_type=password" \
    -d "client_id=admin-cli" 2>&1)

if [ -z "$TOKEN_RESPONSE" ]; then
    echo "ERROR: Failed to authenticate with Keycloak (empty response)"
    exit 1
fi

# Check for error in response
if echo "$TOKEN_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo "ERROR: Authentication failed"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
if [ "$ACCESS_TOKEN" = "null" ] || [ -z "$ACCESS_TOKEN" ]; then
    echo "ERROR: Failed to get access token"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi
echo "Authentication successful!"

# Helper function for API calls
kc_api() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ -n "$data" ]; then
        curl -sf -X "$method" "${KEYCLOAK_URL}/admin${endpoint}" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -sf -X "$method" "${KEYCLOAK_URL}/admin${endpoint}" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}"
    fi
}

# Check if realm exists
echo ""
echo "Checking if realm '${REALM_NAME}' exists..."
if kc_api GET "/realms/${REALM_NAME}" > /dev/null 2>&1; then
    echo "Realm '${REALM_NAME}' already exists - skipping creation"
else
    echo "Creating realm '${REALM_NAME}'..."

    # Create realm with SAML enabled
    REALM_CONFIG=$(cat <<EOF
{
    "realm": "${REALM_NAME}",
    "enabled": true,
    "displayName": "Faux Splunk Cloud",
    "displayNameHtml": "<div>Faux Splunk Cloud</div>",
    "loginWithEmailAllowed": true,
    "duplicateEmailsAllowed": false,
    "resetPasswordAllowed": true,
    "editUsernameAllowed": false,
    "bruteForceProtected": true,
    "permanentLockout": false,
    "maxFailureWaitSeconds": 900,
    "minimumQuickLoginWaitSeconds": 60,
    "waitIncrementSeconds": 60,
    "quickLoginCheckMilliSeconds": 1000,
    "maxDeltaTimeSeconds": 43200,
    "failureFactor": 5,
    "defaultSignatureAlgorithm": "RS256",
    "accessTokenLifespan": 3600,
    "accessTokenLifespanForImplicitFlow": 900,
    "ssoSessionIdleTimeout": 28800,
    "ssoSessionMaxLifespan": 36000
}
EOF
)

    if kc_api POST "/realms" "$REALM_CONFIG" > /dev/null 2>&1; then
        echo "Realm created successfully!"

        # Set custom theme for the realm
        echo "Setting faux-splunk theme for realm..."
        THEME_CONFIG='{"loginTheme": "faux-splunk"}'
        kc_api PUT "/realms/${REALM_NAME}" "$THEME_CONFIG" > /dev/null 2>&1 || echo "  Warning: Could not set custom theme"
    else
        echo "ERROR: Failed to create realm"
        exit 1
    fi
fi

# Ensure theme is set on existing realm
echo ""
echo "Updating realm theme..."
THEME_CONFIG='{"loginTheme": "faux-splunk"}'
kc_api PUT "/realms/${REALM_NAME}" "$THEME_CONFIG" > /dev/null 2>&1 && echo "  Theme set to faux-splunk" || echo "  Warning: Could not update theme"

# Configure WebAuthn/Passkey authentication
echo ""
echo "Configuring WebAuthn/Passkey support..."
WEBAUTHN_CONFIG=$(cat <<EOF
{
    "webAuthnPolicyRpEntityName": "Faux Splunk Cloud",
    "webAuthnPolicySignatureAlgorithms": ["ES256", "RS256"],
    "webAuthnPolicyRpId": "",
    "webAuthnPolicyAttestationConveyancePreference": "not specified",
    "webAuthnPolicyAuthenticatorAttachment": "not specified",
    "webAuthnPolicyRequireResidentKey": "not specified",
    "webAuthnPolicyUserVerificationRequirement": "preferred",
    "webAuthnPolicyCreateTimeout": 0,
    "webAuthnPolicyAvoidSameAuthenticatorRegister": false,
    "webAuthnPolicyAcceptableAaguids": [],
    "webAuthnPolicyPasswordlessRpEntityName": "Faux Splunk Cloud",
    "webAuthnPolicyPasswordlessSignatureAlgorithms": ["ES256", "RS256"],
    "webAuthnPolicyPasswordlessRpId": "",
    "webAuthnPolicyPasswordlessAttestationConveyancePreference": "not specified",
    "webAuthnPolicyPasswordlessAuthenticatorAttachment": "platform",
    "webAuthnPolicyPasswordlessRequireResidentKey": "Yes",
    "webAuthnPolicyPasswordlessUserVerificationRequirement": "required",
    "webAuthnPolicyPasswordlessCreateTimeout": 0,
    "webAuthnPolicyPasswordlessAvoidSameAuthenticatorRegister": false,
    "webAuthnPolicyPasswordlessAcceptableAaguids": []
}
EOF
)
kc_api PUT "/realms/${REALM_NAME}" "$WEBAUTHN_CONFIG" > /dev/null 2>&1 && echo "  WebAuthn policies configured" || echo "  Warning: Could not configure WebAuthn"

# Enable WebAuthn required action for registration
echo "Enabling WebAuthn required actions..."
WEBAUTHN_REGISTER_ACTION='{"alias":"webauthn-register","name":"Webauthn Register","providerId":"webauthn-register","enabled":true,"defaultAction":false,"priority":50,"config":{}}'
kc_api PUT "/realms/${REALM_NAME}/authentication/required-actions/webauthn-register" "$WEBAUTHN_REGISTER_ACTION" > /dev/null 2>&1 && echo "  webauthn-register enabled" || echo "  Warning: Could not enable webauthn-register"

WEBAUTHN_PASSWORDLESS_ACTION='{"alias":"webauthn-register-passwordless","name":"Webauthn Register Passwordless","providerId":"webauthn-register-passwordless","enabled":true,"defaultAction":false,"priority":55,"config":{}}'
kc_api PUT "/realms/${REALM_NAME}/authentication/required-actions/webauthn-register-passwordless" "$WEBAUTHN_PASSWORDLESS_ACTION" > /dev/null 2>&1 && echo "  webauthn-register-passwordless enabled" || echo "  Warning: Could not enable webauthn-register-passwordless"

# Create roles
echo ""
echo "Creating roles..."
for role in platform_admin tenant_admin tenant_user customer splunk_admin; do
    ROLE_EXISTS=$(kc_api GET "/realms/${REALM_NAME}/roles/${role}" 2>/dev/null || echo "")
    if [ -z "$ROLE_EXISTS" ]; then
        ROLE_CONFIG="{\"name\": \"${role}\", \"description\": \"${role} role for Faux Splunk Cloud\"}"
        if kc_api POST "/realms/${REALM_NAME}/roles" "$ROLE_CONFIG" > /dev/null 2>&1; then
            echo "  Created role: ${role}"
        else
            echo "  Warning: Could not create role ${role}"
        fi
    else
        echo "  Role exists: ${role}"
    fi
done

# Create SAML client for the platform
echo ""
echo "Setting up SAML client..."
CLIENT_ID="faux-splunk-cloud"
EXISTING_CLIENT=$(kc_api GET "/realms/${REALM_NAME}/clients?clientId=${CLIENT_ID}" 2>/dev/null | jq -r '.[0].id // empty')

if [ -z "$EXISTING_CLIENT" ]; then
    echo "Creating SAML client '${CLIENT_ID}'..."

    SAML_CLIENT=$(cat <<EOF
{
    "clientId": "${CLIENT_ID}",
    "name": "Faux Splunk Cloud Platform",
    "description": "SAML authentication for Faux Splunk Cloud",
    "enabled": true,
    "protocol": "saml",
    "publicClient": false,
    "frontchannelLogout": true,
    "fullScopeAllowed": true,
    "attributes": {
        "saml.assertion.signature": "true",
        "saml.server.signature": "true",
        "saml.client.signature": "false",
        "saml.signature.algorithm": "RSA_SHA256",
        "saml.signing.certificate": "",
        "saml.encrypt": "false",
        "saml_assertion_consumer_url_post": "https://${PLATFORM_URL}/api/v1/auth/saml/acs",
        "saml_assertion_consumer_url_redirect": "https://${PLATFORM_URL}/api/v1/auth/saml/acs",
        "saml_single_logout_service_url_post": "https://${PLATFORM_URL}/api/v1/auth/saml/slo",
        "saml_single_logout_service_url_redirect": "https://${PLATFORM_URL}/api/v1/auth/saml/slo",
        "saml.authnstatement": "true",
        "saml.onetimeuse.condition": "false",
        "saml_force_name_id_format": "true",
        "saml_name_id_format": "email"
    },
    "baseUrl": "https://${PLATFORM_URL}",
    "rootUrl": "https://${PLATFORM_URL}",
    "redirectUris": [
        "https://${PLATFORM_URL}/*",
        "https://${PLATFORM_URL}/api/v1/auth/saml/acs"
    ],
    "webOrigins": ["https://${PLATFORM_URL}"],
    "defaultClientScopes": ["email", "profile", "roles"],
    "protocolMappers": [
        {
            "name": "email",
            "protocol": "saml",
            "protocolMapper": "saml-user-property-mapper",
            "consentRequired": false,
            "config": {
                "attribute.nameformat": "Basic",
                "user.attribute": "email",
                "friendly.name": "email",
                "attribute.name": "email"
            }
        },
        {
            "name": "firstName",
            "protocol": "saml",
            "protocolMapper": "saml-user-property-mapper",
            "consentRequired": false,
            "config": {
                "attribute.nameformat": "Basic",
                "user.attribute": "firstName",
                "friendly.name": "givenName",
                "attribute.name": "firstName"
            }
        },
        {
            "name": "lastName",
            "protocol": "saml",
            "protocolMapper": "saml-user-property-mapper",
            "consentRequired": false,
            "config": {
                "attribute.nameformat": "Basic",
                "user.attribute": "lastName",
                "friendly.name": "surname",
                "attribute.name": "lastName"
            }
        },
        {
            "name": "roles",
            "protocol": "saml",
            "protocolMapper": "saml-role-list-mapper",
            "consentRequired": false,
            "config": {
                "single": "false",
                "attribute.nameformat": "Basic",
                "attribute.name": "roles"
            }
        },
        {
            "name": "tenant_id",
            "protocol": "saml",
            "protocolMapper": "saml-user-attribute-mapper",
            "consentRequired": false,
            "config": {
                "attribute.nameformat": "Basic",
                "user.attribute": "tenant_id",
                "friendly.name": "tenant_id",
                "attribute.name": "tenant_id"
            }
        }
    ]
}
EOF
)

    if kc_api POST "/realms/${REALM_NAME}/clients" "$SAML_CLIENT" > /dev/null 2>&1; then
        echo "SAML client created successfully!"
    else
        echo "Warning: Could not create SAML client (may already exist)"
    fi
else
    echo "SAML client '${CLIENT_ID}' already exists"
fi

# Create default admin user
echo ""
echo "Setting up default admin user..."
ADMIN_USER_EXISTS=$(kc_api GET "/realms/${REALM_NAME}/users?username=admin&exact=true" 2>/dev/null | jq -r '.[0].id // empty')

if [ -z "$ADMIN_USER_EXISTS" ]; then
    echo "Creating admin user..."

    ADMIN_USER=$(cat <<EOF
{
    "username": "admin",
    "email": "${DEFAULT_ADMIN_EMAIL}",
    "emailVerified": true,
    "enabled": true,
    "firstName": "Platform",
    "lastName": "Admin",
    "credentials": [
        {
            "type": "password",
            "value": "${DEFAULT_ADMIN_PASSWORD}",
            "temporary": false
        }
    ]
}
EOF
)

    if kc_api POST "/realms/${REALM_NAME}/users" "$ADMIN_USER" > /dev/null 2>&1; then
        echo "Admin user created!"

        # Assign roles to admin user
        sleep 1  # Brief pause to ensure user is created
        ADMIN_USER_ID=$(kc_api GET "/realms/${REALM_NAME}/users?username=admin&exact=true" | jq -r '.[0].id')
        if [ -n "$ADMIN_USER_ID" ] && [ "$ADMIN_USER_ID" != "null" ]; then
            # Get role IDs and assign them
            for role in platform_admin splunk_admin; do
                ROLE_DATA=$(kc_api GET "/realms/${REALM_NAME}/roles/${role}" 2>/dev/null || echo "")
                if [ -n "$ROLE_DATA" ]; then
                    ROLE_ID=$(echo "$ROLE_DATA" | jq -r '.id')
                    ROLE_NAME=$(echo "$ROLE_DATA" | jq -r '.name')
                    if [ -n "$ROLE_ID" ] && [ "$ROLE_ID" != "null" ]; then
                        ROLE_ASSIGNMENT="[{\"id\": \"${ROLE_ID}\", \"name\": \"${ROLE_NAME}\"}]"
                        kc_api POST "/realms/${REALM_NAME}/users/${ADMIN_USER_ID}/role-mappings/realm" "$ROLE_ASSIGNMENT" > /dev/null 2>&1 || true
                        echo "  Assigned role '${role}' to admin user"
                    fi
                fi
            done
        fi
    else
        echo "Warning: Could not create admin user"
    fi
else
    echo "Admin user already exists"
fi

# Create a test customer user
echo ""
echo "Setting up test customer user..."
CUSTOMER_USER_EXISTS=$(kc_api GET "/realms/${REALM_NAME}/users?username=customer&exact=true" 2>/dev/null | jq -r '.[0].id // empty')

if [ -z "$CUSTOMER_USER_EXISTS" ]; then
    echo "Creating customer user..."

    CUSTOMER_USER=$(cat <<EOF
{
    "username": "customer",
    "email": "customer@faux-splunk.local",
    "emailVerified": true,
    "enabled": true,
    "firstName": "Test",
    "lastName": "Customer",
    "credentials": [
        {
            "type": "password",
            "value": "customer",
            "temporary": false
        }
    ]
}
EOF
)

    if kc_api POST "/realms/${REALM_NAME}/users" "$CUSTOMER_USER" > /dev/null 2>&1; then
        echo "Customer user created!"

        # Assign tenant_user role
        sleep 1
        CUSTOMER_USER_ID=$(kc_api GET "/realms/${REALM_NAME}/users?username=customer&exact=true" | jq -r '.[0].id')
        if [ -n "$CUSTOMER_USER_ID" ] && [ "$CUSTOMER_USER_ID" != "null" ]; then
            ROLE_DATA=$(kc_api GET "/realms/${REALM_NAME}/roles/tenant_user" 2>/dev/null || echo "")
            if [ -n "$ROLE_DATA" ]; then
                ROLE_ID=$(echo "$ROLE_DATA" | jq -r '.id')
                ROLE_NAME=$(echo "$ROLE_DATA" | jq -r '.name')
                if [ -n "$ROLE_ID" ] && [ "$ROLE_ID" != "null" ]; then
                    ROLE_ASSIGNMENT="[{\"id\": \"${ROLE_ID}\", \"name\": \"${ROLE_NAME}\"}]"
                    kc_api POST "/realms/${REALM_NAME}/users/${CUSTOMER_USER_ID}/role-mappings/realm" "$ROLE_ASSIGNMENT" > /dev/null 2>&1 || true
                    echo "  Assigned role 'tenant_user' to customer user"
                fi
            fi
        fi
    else
        echo "Warning: Could not create customer user"
    fi
else
    echo "Customer user already exists"
fi

# Create Vault OIDC client
echo ""
echo "Setting up Vault OIDC client..."
VAULT_CLIENT_ID="vault"
EXISTING_VAULT_CLIENT=$(kc_api GET "/realms/${REALM_NAME}/clients?clientId=${VAULT_CLIENT_ID}" 2>/dev/null | jq -r '.[0].id // empty')

if [ -z "$EXISTING_VAULT_CLIENT" ]; then
    echo "Creating OIDC client '${VAULT_CLIENT_ID}'..."

    VAULT_CLIENT=$(cat <<EOF
{
    "clientId": "${VAULT_CLIENT_ID}",
    "name": "HashiCorp Vault",
    "description": "OIDC authentication for Vault UI and CLI",
    "enabled": true,
    "protocol": "openid-connect",
    "publicClient": false,
    "secret": "${FSC_VAULT_OIDC_SECRET:-vault-oidc-secret}",
    "standardFlowEnabled": true,
    "implicitFlowEnabled": false,
    "directAccessGrantsEnabled": false,
    "serviceAccountsEnabled": false,
    "redirectUris": [
        "https://${PLATFORM_URL}/vault/ui/vault/auth/oidc/oidc/callback",
        "https://${PLATFORM_URL}/vault/oidc/callback",
        "http://localhost:8250/oidc/callback"
    ],
    "webOrigins": ["https://${PLATFORM_URL}"],
    "defaultClientScopes": ["openid", "email", "profile", "roles"],
    "protocolMappers": [
        {
            "name": "groups",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-realm-role-mapper",
            "consentRequired": false,
            "config": {
                "multivalued": "true",
                "claim.name": "groups",
                "jsonType.label": "String",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true"
            }
        }
    ]
}
EOF
)

    if kc_api POST "/realms/${REALM_NAME}/clients" "$VAULT_CLIENT" > /dev/null 2>&1; then
        echo "Vault OIDC client created successfully!"
    else
        echo "Warning: Could not create Vault OIDC client"
    fi
else
    echo "Vault OIDC client '${VAULT_CLIENT_ID}' already exists"
fi

# Create Concourse OIDC client
echo ""
echo "Setting up Concourse OIDC client..."
CONCOURSE_CLIENT_ID="concourse"
EXISTING_CONCOURSE_CLIENT=$(kc_api GET "/realms/${REALM_NAME}/clients?clientId=${CONCOURSE_CLIENT_ID}" 2>/dev/null | jq -r '.[0].id // empty')

if [ -z "$EXISTING_CONCOURSE_CLIENT" ]; then
    echo "Creating OIDC client '${CONCOURSE_CLIENT_ID}'..."

    CONCOURSE_CLIENT=$(cat <<EOF
{
    "clientId": "${CONCOURSE_CLIENT_ID}",
    "name": "Concourse CI",
    "description": "OIDC authentication for Concourse CI/CD",
    "enabled": true,
    "protocol": "openid-connect",
    "publicClient": false,
    "secret": "${FSC_CONCOURSE_OIDC_SECRET:-concourse-oidc-secret}",
    "standardFlowEnabled": true,
    "implicitFlowEnabled": false,
    "directAccessGrantsEnabled": false,
    "serviceAccountsEnabled": false,
    "redirectUris": [
        "https://${PLATFORM_URL}/concourse/sky/issuer/callback"
    ],
    "webOrigins": ["https://${PLATFORM_URL}"],
    "defaultClientScopes": ["openid", "email", "profile", "roles"],
    "protocolMappers": [
        {
            "name": "groups",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-realm-role-mapper",
            "consentRequired": false,
            "config": {
                "multivalued": "true",
                "claim.name": "groups",
                "jsonType.label": "String",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true"
            }
        }
    ]
}
EOF
)

    if kc_api POST "/realms/${REALM_NAME}/clients" "$CONCOURSE_CLIENT" > /dev/null 2>&1; then
        echo "Concourse OIDC client created successfully!"
    else
        echo "Warning: Could not create Concourse OIDC client"
    fi
else
    echo "Concourse OIDC client '${CONCOURSE_CLIENT_ID}' already exists"
fi

echo ""
echo "=========================================="
echo "Keycloak Initialization Complete!"
echo "=========================================="
echo ""
echo "Test Users:"
echo "  Admin:    admin / ${DEFAULT_ADMIN_PASSWORD} (platform_admin role)"
echo "  Customer: customer / customer (tenant_user role)"
echo ""
echo "SAML Metadata URL:"
echo "  https://${PLATFORM_URL}/realms/${REALM_NAME}/protocol/saml/descriptor"
echo ""
echo "Keycloak Admin Console:"
echo "  ${KEYCLOAK_URL}/admin"
echo ""
