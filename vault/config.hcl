# Vault Server Configuration
# Faux Splunk Cloud

ui = true
disable_mlock = true

# File storage for development (simpler than PostgreSQL)
# For production, use PostgreSQL or Consul
storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true  # TLS terminated by Traefik
}

api_addr = "http://vault:8200"
