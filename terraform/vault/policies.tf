# Vault Policies Configuration

# Admin policy - full access
resource "vault_policy" "admin" {
  name   = "admin"
  policy = <<-EOT
    # Full administrative access
    path "*" {
      capabilities = ["create", "read", "update", "delete", "list", "sudo"]
    }
  EOT
}

# Reader policy - read-only access to secrets
resource "vault_policy" "reader" {
  name   = "reader"
  policy = <<-EOT
    # Read access to FSC secrets
    path "fsc/data/*" {
      capabilities = ["read", "list"]
    }

    path "fsc/metadata/*" {
      capabilities = ["read", "list"]
    }
  EOT
}

# FSC API policy - access for the backend API
resource "vault_policy" "fsc_api" {
  name   = "fsc-api"
  policy = <<-EOT
    # Manage Splunk instance secrets
    path "fsc/data/splunk/*" {
      capabilities = ["create", "read", "update", "delete"]
    }

    path "fsc/metadata/splunk/*" {
      capabilities = ["read", "list", "delete"]
    }

    # Manage HEC token secrets
    path "fsc/data/hec/*" {
      capabilities = ["create", "read", "update", "delete"]
    }

    path "fsc/metadata/hec/*" {
      capabilities = ["read", "list", "delete"]
    }

    # Transit encryption for sensitive data
    path "transit/encrypt/${var.transit_key_name}" {
      capabilities = ["update"]
    }

    path "transit/decrypt/${var.transit_key_name}" {
      capabilities = ["update"]
    }

    # Read transit key info
    path "transit/keys/${var.transit_key_name}" {
      capabilities = ["read"]
    }
  EOT
}

# Concourse policy - read access for CI/CD pipelines
resource "vault_policy" "fsc_concourse" {
  name   = "fsc-concourse"
  policy = <<-EOT
    # Read Concourse-specific secrets
    path "fsc/data/concourse/*" {
      capabilities = ["read"]
    }

    path "fsc/metadata/concourse/*" {
      capabilities = ["read", "list"]
    }

    # Read Splunk instance secrets (for test pipelines)
    path "fsc/data/splunk/*" {
      capabilities = ["read"]
    }

    path "fsc/metadata/splunk/*" {
      capabilities = ["read", "list"]
    }
  EOT
}

# Tenant isolation policy template
resource "vault_policy" "tenant_template" {
  name   = "tenant-template"
  policy = <<-EOT
    # Tenant-scoped access - use with identity groups
    # Path templating uses {{identity.entity.metadata.tenant_id}}
    path "fsc/data/tenants/{{identity.entity.metadata.tenant_id}}/*" {
      capabilities = ["create", "read", "update", "delete", "list"]
    }

    path "fsc/metadata/tenants/{{identity.entity.metadata.tenant_id}}/*" {
      capabilities = ["read", "list"]
    }
  EOT
}
