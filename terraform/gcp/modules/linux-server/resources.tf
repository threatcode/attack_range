
# Google Compute Engine Instance Configuration for Linux Servers
# This section configures a Linux server instance in GCP. Instances can be 
# configured with a custom image, machine type, and disk specifications.
# -----------------------------------------------------------------------------

# Linux Server Instance Configuration
resource "google_compute_instance" "linux_server" {
  # Define instance count based on the number of entries in the linux_servers variable
  count        = length(var.linux_servers)
  name         = "${var.general.attack_range_name}-linux-server-${var.general.key_name}-${count.index}"
  machine_type = (var.zeek_server.zeek_server == 1 || var.snort_server.snort_server == 1) ? var.zeek_server.machine_type : var.snort_server.machine_type
  zone         = var.gcp.zone   # Specify the GCP zone for deployment

  # Boot Disk Configuration
  # Set up the primary boot disk with configurable image, size, and type
  boot_disk {
    initialize_params {
      image = var.linux_servers[count.index].image        # OS image ID (e.g., "ubuntu-2204-lts")
      size  = var.linux_servers[count.index].disk_size    # Disk size in GB
      type  = var.linux_servers[count.index].disk_type    # Disk type (e.g., "pd-balanced")
    }
    auto_delete = true  # Automatically delete the boot disk upon instance deletion
  }

  # Network Interface Configuration
  # Attach the instance to the specified VPC and assign an external IP if required
  network_interface {
    network    = var.vpc_network
    subnetwork = var.subnetwork
    access_config {    # Assigns an external IP address (NAT)
      nat_ip = length(google_compute_address.linux_server_ip) > count.index ? google_compute_address.linux_server_ip[count.index].address : null
    }
  }

  # Use local-exec provisioner to clean known_hosts
  provisioner "local-exec" {
    command = "ssh-keygen -f ~/.ssh/known_hosts -R ${self.network_interface.0.access_config.0.nat_ip}"
  }

  # Assign the Linux Service Account to this instance
    service_account {
        email  = var.linux_sa_email
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    }

  # SSH Key Metadata Configuration
  # Add SSH keys for instance access
  metadata = {
    ssh-keys = "ubuntu:${file(var.gcp.public_key_path)}"
  }

  # Tags for Network Firewall Rules
  tags = ["gcp-infrastructure", "linux-server", "attack-range"]

  # Labels for Instance Identification (equivalent to AWS tags)
  labels = {
    name = "${var.general.attack_range_name}-linux-server-${var.general.key_name}-${count.index}"
  }

  # Remote Exec Provisioner - Initial Boot Check
  # Run basic initialization commands after the instance boots
  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = self.network_interface[0].access_config[0].nat_ip
      private_key = file(var.gcp.private_key_path)
    }
  }

  # Local Exec Provisioner - Create JSON Variables for Ansible
  # Generate JSON files with instance-specific variables to be used by Ansible
  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      cat > vars/linux_vars_${count.index}.json << 'EOF'
      {
        "ansible_python_interpreter": "/usr/bin/python3",
        "general": ${jsonencode(var.general)},
        "splunk_server": ${jsonencode(var.splunk_server)},
        "linux_servers": ${jsonencode(var.linux_servers[count.index])},
        "simulation": ${jsonencode(var.simulation)}
      }
      EOF
    EOT
  }

  # Local Exec Provisioner - Ansible Playbook Execution
  # Run the Ansible playbook to configure the instance with the specified variables
  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key '${var.gcp.private_key_path}' -i '${self.network_interface[0].access_config[0].nat_ip},' linux_server.yml -e @vars/linux_vars_${count.index}.json -vvv"
  }
}

# -----------------------------------------------------------------------------
# External IP Address Configuration for Linux Servers
# Allocates a static external IP address if required. Useful for public access.
# -----------------------------------------------------------------------------

resource "google_compute_address" "linux_server_ip" {
  count  = (var.gcp.use_elastic_ips == "1") ? length(var.linux_servers) : 0
  name   = "linux-server-ip-${count.index}"
  region = var.gcp.region   # Specify the region for the IP allocation
}
