# Vault Secrets Engines Configuration

# KV v2 secrets engine for Faux Splunk Cloud
resource "vault_mount" "fsc_kv" {
  path        = "fsc"
  type        = "kv"
  description = "KV secrets engine for Faux Splunk Cloud"
  options = {
    version = "2"
  }
}

# Transit secrets engine for encryption-as-a-service
resource "vault_mount" "transit" {
  path        = "transit"
  type        = "transit"
  description = "Transit encryption engine for data protection"
}

# Transit encryption key for FSC
resource "vault_transit_secret_backend_key" "fsc" {
  backend          = vault_mount.transit.path
  name             = var.transit_key_name
  type             = "aes256-gcm96"
  deletion_allowed = false
  exportable       = false

  # Auto-rotate every 30 days
  auto_rotate_period = 2592000
}

# Bootstrap secrets structure
resource "vault_kv_secret_v2" "concourse_config" {
  mount = vault_mount.fsc_kv.path
  name  = "concourse/config"

  data_json = jsonencode({
    note = "Concourse secrets are stored under concourse/*"
  })

  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "splunk_config" {
  mount = vault_mount.fsc_kv.path
  name  = "splunk/config"

  data_json = jsonencode({
    note = "Splunk instance secrets are stored under splunk/*"
  })

  lifecycle {
    ignore_changes = [data_json]
  }
}
