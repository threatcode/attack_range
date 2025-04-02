
variable "general" { }

variable "gcp" { }

variable "vpc_network" { }

variable "subnetwork" { }

variable "service_accounts" { }

variable "windows_sa_email" { }

variable "windows_sa_roles" { }

variable "simulation" { }

variable "splunk_server" { }

variable "windows_servers" { }

variable "zeek_server" { }

variable "snort_server" { }

variable "private_cidr_three_octets" {
  type = string
  description = "The first three octets of the private subnet CIDR block."
}
