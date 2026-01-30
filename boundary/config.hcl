# HashiCorp Boundary Configuration
# For Faux Splunk Cloud - Short-Lived Access to Ephemeral Instances
#
# This configuration runs Boundary in "all-in-one" mode (controller + worker)
# suitable for development and small deployments.

disable_mlock = true

# Controller configuration
controller {
  name        = "faux-splunk-boundary"
  description = "Faux Splunk Cloud Access Controller"

  # Database URL is provided via environment variable BOUNDARY_PG_URL
  database {
    url = "env://BOUNDARY_PG_URL"
  }

  # Public cluster address (for workers to connect)
  public_cluster_addr = "boundary:9201"
}

# Worker configuration (runs in same process for dev)
worker {
  name        = "faux-splunk-worker"
  description = "Faux Splunk Cloud Access Worker"

  # Connect to the controller
  controllers = ["boundary:9201"]

  # Public address for client connections
  public_addr = "boundary:9202"

  # Tags for target filtering
  tags {
    type = ["splunk", "ephemeral"]
  }
}

# Listeners

# API listener for clients and admin
listener "tcp" {
  purpose = "api"
  address = "0.0.0.0:9200"
  tls_disable = true  # TLS handled by Traefik
}

# Cluster listener for controller-worker communication
listener "tcp" {
  purpose = "cluster"
  address = "0.0.0.0:9201"
  tls_disable = true  # Internal network
}

# Proxy listener for session connections
listener "tcp" {
  purpose = "proxy"
  address = "0.0.0.0:9202"
  tls_disable = true  # TLS handled by Traefik
}

# Operations listener (health checks)
listener "tcp" {
  purpose = "ops"
  address = "0.0.0.0:9203"
  tls_disable = true
}

# Events configuration (audit)
events {
  audit_enabled       = true
  observations_enable = true
  sysevents_enabled   = true

  sink "stderr" {
    name = "all-events"
    description = "All events sent to stderr"
    event_types = ["*"]
    format = "cloudevents-json"
  }

  sink {
    name = "audit-sink"
    description = "Audit events for compliance"
    event_types = ["audit"]
    format = "cloudevents-json"

    file {
      path = "/boundary/data/audit.log"
      file_name = "audit.log"
    }
  }
}

# KMS configuration for encryption
# In production, use Vault Transit, AWS KMS, etc.
kms "aead" {
  purpose = "root"
  aead_type = "aes-gcm"
  key = "8fVBkCvMp5QFKjhXA5hC/YvABfKNQ/xHF2rGm7WpYqk="  # CHANGE IN PRODUCTION
  key_id = "global_root"
}

kms "aead" {
  purpose = "worker-auth"
  aead_type = "aes-gcm"
  key = "Kl62uD4fQKV5e/i6Dsi/mBTkxaOsuzq8M5OKo5rdTuI="  # CHANGE IN PRODUCTION
  key_id = "global_worker-auth"
}

kms "aead" {
  purpose = "recovery"
  aead_type = "aes-gcm"
  key = "9dVBkCvMp5QFKjhXA5hC/YvABfKNQ/xHF2rGm7WpYqk="  # CHANGE IN PRODUCTION
  key_id = "global_recovery"
}
