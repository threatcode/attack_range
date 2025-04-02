
# Windows Server Output Variables
# -----------------------------------------------------------------------------
# These outputs provide details about the deployed Windows Server instances,
# including their names, internal and external IP addresses, and instance IDs.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# These outputs can be used for verification or additional configuration steps.
# -----------------------------------------------------------------------------

# Output: Windows Service Account Email
# Provides the email address of the Windows Service Account, if created
output "windows_sa_email" {
  description = "The email address of the Windows Service Account"
  value       = var.windows_sa_email
}

# Output: Windows Server Roles
# Lists the roles assigned to the Windows Service Account, if created
output "windows_sa_roles" {
  description = "Roles assigned to the Windows Service Account"
  value       = var.windows_sa_roles
}

# Output the names of the Windows Server instances
output "windows_server_names" {
  description = "Names of the Windows Server instances"
  value       = [for instance in google_compute_instance.windows_server : instance.name]
}

# Output the internal IP addresses of the Windows Server instances
output "windows_server_internal_ips" {
  description = "Internal IP addresses of the Windows Server instances"
  value       = [for instance in google_compute_instance.windows_server : instance.network_interface[0].network_ip]
}

# Output the external IP addresses of the Windows Server instances
# These are NAT IPs assigned to allow external access if configured.
output "windows_server_external_ips" {
  description = "External IP addresses of the Windows Server instances"
  value       = [for instance in google_compute_instance.windows_server : instance.network_interface[0].access_config[0].nat_ip]
}

# Output the unique instance IDs for each Windows Server instance
# Instance IDs are unique identifiers assigned by GCP.
output "windows_server_instance_ids" {
  description = "Instance IDs of the Windows Server instances"
  value       = [for instance in google_compute_instance.windows_server : instance.id]
}
