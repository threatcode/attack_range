
# -----------------------------------------------------------------------------
# Variable Definitions for Terraform Attack Range Deployment
# -----------------------------------------------------------------------------
# This file contains variable definitions used to deploy resources on Google Cloud
# Platform (GCP) for an attack range environment, including general configurations,
# instance-specific settings, and networking details. Each variable block defines
# default values and expected data types, allowing for flexibility and reusability
# across environments.
# -----------------------------------------------------------------------------

# General configuration settings for the attack range, including common parameters
variable "general" {
  description = "General configuration for the attack range"
  type = map(string)

  default = {
    attack_range_password               = "Pl3ase-k1Ll-me:p"  # Password for the attack range instances
    attack_range_name                   = "attack-range-name" # Name identifier for the attack range
    key_name                            = "attack-range-key-pair" # SSH key pair name
    ip_whitelist                        = "0.0.0.0/0" # Whitelist IP range for open access
    cloud_provider                      = "gcp" # Cloud provider, e.g., "gcp" or "aws"
    install_contentctl                  = "1" # "1" to install content control tools, "0" to skip
    carbon_black_cloud                  = "0" # "0" to disable Carrbon Black Cloud
    cisco_secure_endpoint               = "0" # "0" to disable Cisco Secure Endpoint
    crowdstrike_falcon                  = "1" # Install Crowdstrike Falcon Sensor
    crowdstrike_customer_ID             = "" # Crowdstrike Customer ID
    crowdstrike_logs_access_key_id      = "" # AWS Access Key ID for accessing CrowdStrike FDR logs from S3 (required for integration). Investigate if there is similar implementation in GCP.
    crowdstrike_logs_region             = "" # AWS region where the CrowdStrike FDR S3 bucket is hosted (e.g., "us-east-1"). Investigate if there is similar implementation in GCP.
    crowdstrike_logs_secret_access_key  = "" # AWS Secret Access Key for accessing CrowdStrike FDR logs from S3 (required for authentication). Investigate if there is similar implementation in GCP.
    crowdstrike_logs_sqs_url            = "" # AWS SQS URL to retrieve notifications about new CrowdStrike FDR logs in the S3 bucket. Investigate if there is similar implementation in GCP.
  }
}

# Google Cloud Platform-specific configuration settings
variable "gcp" {
  description = "GCP configuration"
  type = map(string)

  default = {
    region                  = "us-central1" # GCP region
    zone                    = "us-central1-a" # GCP zone within the specified region
    project_id              = "your-gcp-project-id" # Replace with actual project ID
    public_key_path         = "~/.ssh/id_rsa.pub" # Path to SSH public key
    private_key_path        = "~/.ssh/id_rsa" # Path to SSH private key
    use_elastic_ips         = "0" # "1" to use elastic IPs, "0" otherwise
  }
}

# Instance-specific configuration settings for logging, monitoring, and alerting
variable "log_sink_config" {
  description = "Configuration for log sinks, including destinations, filters, topics, and identity settings."
  type = object({
    destinations          = map(string) # Map of Pub/Sub destinations for each module/server
    filters               = map(string) # Map of log filters for each module/server
    topics                = map(string) # Map of Pub/Sub topics for each module/server
    writer_identity       = bool        # Flag for unique writer identity
  })

  default = {
    destinations = {
      splunk     = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/splunk-log-topic",
      phantom    = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/phantom-log-topic",
      kali       = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/kali-log-topic",
      nginx      = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/nginx-log-topic",
      linux      = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/linux-log-topic",
      windows    = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/windows-log-topic",
      snort      = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/snort-log-topic",
      zeek       = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/zeek-log-topic",
      iam        = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/iam-log-topic",
      network    = "pubsub.googleapis.com/projects/GOOGLE_PROJECT_ID/topics/network-log-topic"
    },
    filters  = {
      splunk     = "resource.type=gce_instance AND resource.labels.instance_id=\"SPLUNK_INSTANCE_ID\"",
      phantom    = "resource.type=gce_instance AND resource.labels.instance_id=\"PHANTOM_INSTANCE_ID\"",
      kali       = "resource.type=gce_instance AND resource.labels.instance_id=\"KALI_INSTANCE_ID\"",
      nginx      = "resource.type=gce_instance AND resource.labels.instance_id=\"NGINX_INSTANCE_ID\"",
      linux      = "resource.type=gce_instance AND resource.labels.instance_id in (LINUX_INSTANCE_IDS)",
      windows    = "resource.type=gce_instance AND resource.labels.instance_id in (WINDOWS_INSTANCE_IDS)",
      snort      = "resource.type=gce_instance AND resource.labels.instance_id=\"SNORT_INSTANCE_ID\"",
      zeek       = "resource.type=gce_instance AND resource.labels.instance_id=\"ZEEK_INSTANCE_ID\"",
      iam        = "resource.type=\"gce_project\" AND protoPayload.serviceName=\"iam.googleapis.com\"",
      network    = "resource.type=(gce_network OR gce_subnetwork)"
    },
    topics = {
      splunk     = "splunk-log-topic",
      phantom    = "phantom-log-topic",
      kali       = "kali-log-topic",
      nginx      = "nginx-log-topic",
      linux      = "linux-log-topic",
      windows    = "windows-log-topic",
      snort      = "snort-log-topic",
      zeek       = "zeek-log-topic",
      iam        = "iam-log-topic",
      network    = "network-log-topic"
    },
    writer_identity = true
  }
}

variable "monitor_alert" {
  description = "Alert configurations including email and per-instance filters"
  type = object({
    notification              = string
    email_address             = string
    telemetry                 = map(object({
      cpu_utilization         = string
      disk_average_io_latency = string
      memory_balloon_ram_used = string
    }))
  })
  default = {
    notification          = "email",
    email_address = "marco.villarruel@cna.com",
    telemetry = {
      splunk = {
        cpu_utilization         = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"SPLUNK_INSTANCE_ID\""
        disk_average_io_latency = "metric.type=\"compute.googleapis.com/instance/disk/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"SPLUNK_INSTANCE_ID\""
        memory_balloon_ram_used = "metric.type=\"compute.googleapis.com/instance/memory/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"SPLUNK_INSTANCE_ID\""
      }
      phantom = {
        cpu_utilization         = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"PHANTOM_INSTANCE_ID\""
        disk_average_io_latency = "metric.type=\"compute.googleapis.com/instance/disk/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"PHANTOM_INSTANCE_ID\""
        memory_balloon_ram_used = "metric.type=\"compute.googleapis.com/instance/memory/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"PHANTOM_INSTANCE_ID\""
      }
      kali = {
        cpu_utilization         = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"KALI_INSTANCE_ID\""
        disk_average_io_latency = "metric.type=\"compute.googleapis.com/instance/disk/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"KALI_INSTANCE_ID\""
        memory_balloon_ram_used = "metric.type=\"compute.googleapis.com/instance/memory/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"KALI_INSTANCE_ID\""
      }
      nginx = {
        cpu_utilization         = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"NGINX_INSTANCE_ID\""
        disk_average_io_latency = "metric.type=\"compute.googleapis.com/instance/disk/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"NGINX_INSTANCE_ID\""
        memory_balloon_ram_used = "metric.type=\"compute.googleapis.com/instance/memory/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"NGINX_INSTANCE_ID\""
      }
      linux = {
        cpu_utilization         = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id in (LINUX_INSTANCE_IDS)"
        disk_average_io_latency = "metric.type=\"compute.googleapis.com/instance/disk/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id in (LINUX_INSTANCE_IDS)"
        memory_balloon_ram_used = "metric.type=\"compute.googleapis.com/instance/memory/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id in (LINUX_INSTANCE_IDS)"
      }
      windows = {
        cpu_utilization         = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id in (WINDOWS_INSTANCE_IDS)"
        disk_average_io_latency = "metric.type=\"compute.googleapis.com/instance/disk/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id in (WINDOWS_INSTANCE_IDS)"
        memory_balloon_ram_used = "metric.type=\"compute.googleapis.com/instance/memory/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id in (WINDOWS_INSTANCE_IDS)"
      }
      snort = {
        cpu_utilization         = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"SNORT_INSTANCE_ID\""
        disk_average_io_latency = "metric.type=\"compute.googleapis.com/instance/disk/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"SNORT_INSTANCE_ID\""
        memory_balloon_ram_used = "metric.type=\"compute.googleapis.com/instance/memory/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"SNORT_INSTANCE_ID\""
      }
      zeek = {
        cpu_utilization         = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"ZEEK_INSTANCE_ID\""
        disk_average_io_latency = "metric.type=\"compute.googleapis.com/instance/disk/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"ZEEK_INSTANCE_ID\""
        memory_balloon_ram_used = "metric.type=\"compute.googleapis.com/instance/memory/utilization\" AND resource.type=\"gce_instance\" AND resource.labels.instance_id=\"ZEEK_INSTANCE_ID\""
      }
    }
  }
}

# Network CIDR blocks for public and private subnets
variable "cidrs" {
  description = "Network configuration"
  type = map(any)

  default = {
    cidr_blocks = [
      "10.20.1.0/24", # Public subnet CIDR block
      "10.20.2.0/24"  # Private subnet CIDR block
    ]
  }
}

# Variable to define a map of service accounts and their associated roles.
# This variable expects a map where each key represents a service account's name (e.g., "splunk"),
# and each value is an object specifying the service account's ID and list of IAM roles to assign.

variable "service_accounts" {
  description = "Map of service accounts with their account IDs and assigned roles."
  type = map(object({
    # The unique identifier for the service account, used for creation and role assignment.
    account_id = string
    
    # A list of IAM roles to be assigned to the service account. 
    # These roles enable necessary permissions for each service account based on its purpose.
    roles = list(string)
  }))

  default = {
    # Service account configuration for "splunk" with its unique ID and required IAM roles.
    splunk = {
      account_id = "splunk-sa"
      roles      = ["roles/compute.viewer", "roles/logging.logWriter"]
    },
    
    # Service account configuration for "phantom" with assigned roles for compute viewing and logging.
    phantom = {
      account_id = "phantom-sa"
      roles      = ["roles/compute.viewer", "roles/logging.logWriter"]
    },
    
    # Service account "nginx" requires additional roles for storage and network viewing, 
    # along with compute viewing and logging.
    nginx = {
      account_id = "nginx-sa"
      roles      = [
        "roles/compute.viewer",
        "roles/logging.logWriter",
        "roles/storage.objectViewer",
        "roles/compute.networkViewer"
      ]
    },
    
    # Minimal IAM roles assigned for basic compute viewing and logging for "kali" service account.
    kali = {
      account_id = "kali-sa"
      roles      = ["roles/compute.viewer", "roles/logging.logWriter"]
    },
    
    # "linux" service account configuration for compute viewing and logging permissions.
    linux = {
      account_id = "linux-sa"
      roles      = ["roles/compute.viewer", "roles/logging.logWriter"]
    },
    
    # IAM roles for the "windows" service account, allowing compute viewing and log writing.
    windows = {
      account_id = "windows-sa"
      roles      = ["roles/compute.viewer", "roles/logging.logWriter"]
    },
    
    # The "snort" service account requires additional permissions for object and network viewing.
    snort = {
      account_id = "snort-sa"
      roles      = [
        "roles/compute.viewer",
        "roles/logging.logWriter",
        "roles/storage.objectViewer",
        "roles/compute.networkViewer"
      ]
    },
    
    # Configuration for "zeek" service account with multiple roles, including storage and network access.
    zeek = {
      account_id = "zeek-sa"
      roles      = [
        "roles/compute.viewer",
        "roles/logging.logWriter",
        "roles/storage.objectViewer",
        "roles/compute.networkViewer"
      ]
    },

    iam = {
        account_id = "iam-sa"
        roles      = ["roles/iam.securityReviewer", "roles/logging.logWriter"]
    },

    network = {
        account_id = "network-sa"
        roles      = ["roles/compute.networkAdmin", "roles/logging.logWriter"]
    }
  }
}

# Splunk server instance configuration settings
variable "splunk_server" {
  description = "Configuration for the Splunk server instance"
  type = object({
    hostname                = string # Hostname for the server instance
    machine_type            = string # Machine type, e.g., "e2-standard-4"
    image                   = string # Image, e.g., "ubuntu-2204-lts"
    disk_size               = number # Disk size in GB
    disk_type               = string # Disk type, e.g., "pd-standard"
    install_es              = string # "1" to install Splunk Enterprise Security, "0" otherwise
    byo_splunk              = string # "1" for BYO Splunk, "0" otherwise
    byo_splunk_ip           = string # BYO Splunk IP, if applicable
    ingest_bots3_data       = string # "1" to Ingest BOTS data to Attack Range
    install_dltk            = string # "1" to install Deep Learning Toolkit
    splunk_es_app           = string # Splunk Enterprise Security app to install
    network_ip              = string # Static internal IP
    splunk_url              = string # Splunk installation URL
    splunk_uf_url           = string # Splunk Universal Forwarder URL for Linux
    splunk_uf_win_url       = string # Splunk Universal Forwarder URL for Windows
    s3_bucket_url           = string # URL for S3 bucket containing Splunk apps
    splunk_apps             = string # Comma-separated list of Splunk apps to install
    splunk_server           = number
  })

  default = {
    hostname                = "splunk"
    machine_type            = "e2-standard-4"
    image                   = "ubuntu-2204-lts"
    disk_type               = "pd-standard"
    disk_size               = 120
    install_es              = "1"
    byo_splunk              = "1"
    byo_splunk_ip           = "192.168.20.220"
    ingest_bots3_data       = "0"
    install_dltk            = "1"
    splunk_es_app           = "splunk-enterprise-security_710.spl"
    network_ip              = "10.20.2.220"
    splunk_url              = "https://download.splunk.com/products/splunk/releases/9.3.0/linux/splunk-9.3.0-51ccf43db5bd-Linux-x86_64.tgz"
    splunk_uf_url           = "https://download.splunk.com/products/universalforwarder/releases/9.3.0/linux/splunkforwarder-9.3.0-51ccf43db5bd-linux-2.6-amd64.deb"
    splunk_uf_win_url       = "https://download.splunk.com/products/universalforwarder/releases/9.3.0/windows/splunkforwarder-9.3.0-51ccf43db5bd-x64-release.msi"
    s3_bucket_url           = "https://attack-range-appbinaries.s3-us-west-2.amazonaws.com"
    splunk_apps             = "TA-aurora-0.2.0.tar.gz,TA-osquery.tar.gz,app-for-circleci_011.tgz,..."
    splunk_server           = "0"
  }
}

# Configuration for Phantom server instance
variable "phantom_server" {
  description = "Phantom server configuration"
  type = object({
    phantom_server          = number # "1" if enabled, "0" otherwise
    hostname                = string # Phantom server hostname
    machine_type            = string # Machine type, e.g., "e2-standard-4"
    image                   = string # Image, e.g., "centos-cloud/centos-7"
    disk_size               = number # Disk size in GB
    disk_type               = string # Disk type, e.g., "pd-standard"
    network_ip              = string # Internal IP for the instance
    phantom_app             = string # Name of the Phantom application to install
    phantom_byo             = string # 1 to enable Bring Your Own Phantom
  })

  default = {
    phantom_server          = "1"
    hostname                = "phantom"
    machine_type            = "e2-standard-4"
    image                   = "centos-cloud/centos-7"
    disk_type               = "pd-standard"
    disk_size               = 30
    network_ip              = "10.20.2.5"
    phantom_app             = "splunk_soar-unpriv-6.3.0.719-d9df3cc1-el8-x86_64.tgz"
    phantom_byo              = "0"
  }
}

# Configuration for NGINX server instance
variable "nginx_server" {
  description = "Nginx server configuration"
  type = object({
    nginx_server           = number # "1" if enabled, "0" otherwise
    hostname               = string # Hostname for NGINX server
    machine_type           = string # Machine type, e.g., "e2-small"
    image                  = string # Image, e.g., "ubuntu-2204-lts"
    disk_size              = number # Disk size in GB
    disk_type              = string # Disk type, e.g., "pd-standard"
    network_ip             = string # Static internal IP
    proxy_server_ip        = string # IP of proxy server, if applicable
    proxy_server_port      = string # Port for proxy server, if applicable
  })

  default = {
    nginx_server            = "1"
    hostname                = "nginx"
    machine_type            = "e2-small"
    image                   = "ubuntu-2204-lts"
    disk_type               = "pd-standard"
    disk_size               = 20
    network_ip              = "10.20.2.31"
    proxy_server_ip         = "10.20.2.254"
    proxy_server_port       = "8000"
  }
}

# Configuration for Kali Linux server instance
variable "kali_server" {
  description = "Kali Linux server configuration"
  type = object({
    kali_server             = number # "1" if enabled, "0" otherwise
    hostname                = string # Hostname for Kali Linux server
    machine_type            = string # Machine type, e.g., "e2-standard-2"
    image                   = string # Image, e.g., "kali-linux-image"
    disk_size               = number # Disk size in GB
    disk_type               = string # Disk type, e.g., "pd-ssd"
    network_ip              = string # Static internal IP
  })

  default = {
    kali_server             = "1"
    hostname                = "kali"
    machine_type            = "e2-standard-2"
    image                   = "kali-linux-image"
    disk_size               = 30
    disk_type               = "pd-ssd"
    network_ip              = "10.20.2.30"
  }
}

# List of Linux server instance configurations
variable "linux_servers" {
  description = "List of configurations for each Linux server instance"
  type = list(object({
    machine_type                  = string  # Instance machine type, e.g., "e2-standard-4"
    image                         = string  # Image, e.g., "ubuntu-2204-lts"
    disk_size                     = number  # Boot disk size in GB
    disk_type                     = string  # Disk type, e.g., "pd-standard" or "pd-ssd"
    hostname                      = string  # Hostname for the Linux server instance
    splunk_uf_url                 = string  # Splunk Universal Forwarder download URL
    sysmon_config                 = string  # Sysmon configuration file name
    install_crowdstrike           = string  # "1" to install CrowdStrike, "0" otherwise
    crowdstrike_linux_agent       = string # CrowdStrike Linux agent file name
    install_cisco_secure_endpoint = string # Disable Cisco Secure Endpoint
  }))

  default = [
    {
      machine_type                  = "e2-standard-4"
      image                         = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
      disk_type                     = "pd-standard"
      disk_size                     = 60
      hostname                      = "ar-linux"
      splunk_uf_url                 = "https://download.splunk.com/products/universalforwarder/releases/9.3.0/linux/splunkforwarder-9.3.0-51ccf43db5bd-linux-2.6-amd64.deb"
      sysmon_config                 = "SwiftOnSecurity.xml"
      install_crowdstrike           = "1"
      crowdstrike_linux_agent       = "falcon-sensor_7.17.0-17011_amd64.deb"
      install_cisco_secure_endpoint = "0"
    }
  ]
}

# Configuration for Windows servers
variable "windows_servers" {
  description = "Configuration for Windows servers"
  type = list(object({
    advanced_logging              = string # "1" to enable advanced logging, "0" otherwise
    aurora_agent                  = string # "1" to enable aurora agemt deployment
    bad_blood                     = string # BadBlood (1 for true)
    create_domain                 = string # "1" to create domain, "0" otherwise
    crowdstrike_windows_agent     = string
    disk_type                     = string # Disk type, e.g., "pd-ssd"
    disk_size                     = number # Disk size in GB
    hostname                      = string # Hostname for the Windows server
    image                         = string # Image, e.g., "windows-2019"
    install_carbon_black          = string # Disable Install Carbon Black Agent
    install_cisco_secure_endpoint = string # Disable Cisco Secure Endpoint install
    install_crowdstrike           = string
    install_red_team_tools        = string # "1" to install red team tools, "0" otherwise
    join_domain                   = string # "1" to join domain, "0" otherwise
    machine_type                  = string # Machine type, e.g., "n2-standard-4"
    network_ip                    = string # IP address, e.g. "192.168.10.20"
    dc_network_ip                 = string
    splunk_uf_win_url             = string # Splunk Universal Forwarder for Windows URL
    win_sysmon_config             = string # Sysmon configuration file
  }))

  default = [
    {
      advanced_logging              = "1"
      aurora_agent                  = "1"
      bad_blood                     = "1"
      create_domain                 = "0"
      crowdstrike_windows_agent     = "FalconSensor_Windows.7.19.exe"
      disk_type                     = "pd-ssd"
      disk_size                     = 100
      hostname                      = "ar-win"
      image                         = "projects/windows-cloud/global/images/family/windows-2019"
      install_carbon_black          = "0"
      install_cisco_secure_endpoint = "0"
      install_crowdstrike           = "1"
      install_red_team_tools        = "0"
      join_domain                   = "0"
      machine_type                  = "n2-standard-4"
      network_ip                    = "192.168.10.20"
      dc_network_ip                 = "192.168.10.19"
      splunk_uf_win_url             = "https://download.splunk.com/products/universalforwarder/releases/9.3.0/windows/splunkforwarder-9.3.0-51ccf43db5bd-x64-release.msi"
      win_sysmon_config             = "SwiftOnSecurity.xml"
    }
  ]
}

# Placeholder variables for Snort and Zeek servers and simulation settings
variable "snort_server" { 
  description = ""
  type = object({
    hostname                = string # Hostname for Snort server
    image                   = string
    machine_type            = string # Machine type
    disk_type               = string # Disk type
    disk_size               = number # Disk size in GB
    network_ip              = string # Internal IP
    cloud_provider          = string
    snort_server            = number # Enable Snort server (1 for true)
  })

  default = {
      hostname                = "spl-ar-snort" 
      image                   = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
      machine_type            = "n2-standard-8"
      disk_type               = "pd-standard"
      disk_size               = 60
      network_ip              = "10.20.2.60"
      cloud_provider          = "gcp"
      snort_server            = "1"
  }
}

variable "zeek_server" { 
  description = ""
  type = object({
    hostname                = string # Hostname for Snort server
    image                   = string
    machine_type            = string # Machine type
    disk_type               = string # Disk type
    disk_size               = number # Disk size in GB
    network_ip              = string # Internal IP
    cloud_provider          = string
    zeek_server             = number # Enable Snort server (1 for true)
  })

  default = {
      hostname                = "spl-ar-zeek" 
      image                   = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
      machine_type            = "n2-standard-8"
      disk_type               = "pd-standard"
      disk_size               = 60
      network_ip              = "10.20.2.61"
      cloud_provider          = "gcp"
      zeek_server             = "1"
    }
}

variable "simulation" { 
  description = ""
  type = object({
    simulation                = string # Simulation type for attack range
    atomic_red_team_repo      = string
    atomic_red_team           = string # Atomic Red Team Repository
    atomic_red_team_branch    = string # Atomic Red Team Repository Branch
  })

  default = {
      simulation              = "redcanaryco"
      atomic_red_team_repo    = "git@github.com:redcanaryco/atomic-red-team.git"
      atomic_red_team         = "redcanaryco"
      atomic_red_team_branch  = "master"
    }
}
