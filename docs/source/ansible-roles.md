# Ansible Roles

Attack Range uses Ansible to configure the VPN router and all lab servers. Roles are applied per host via the **roles** list in each server entry in the config (or template). Many roles come from **Ansible Galaxy** (e.g. `P4T12ICK.*`); a few are shipped in the repo under `modules/ansible/roles/`.

## Where roles are defined

- **Galaxy roles** — Declared in the config (or in playbooks) and installed by the controller (e.g. `ansible-galaxy install -r requirements.yml`). Role names in configs often look like `P4T12ICK.ludus_ar_splunk`, `P4T12ICK.ar_guacamole`.
- **Bundled roles** — Live under `modules/ansible/roles/` in the project:
  - **atomic_red_team** — Install and run Atomic Red Team tests (Linux and Windows).
  - **cap_attack** — CAP Attack integration (threat capture around tests).
  - **data_replay** — Replay log files into Splunk (oneshot input).
  - **purplesharp** — Download and run PurpleSharp simulations on Windows.

Playbooks (e.g. VPN, main lab provisioning) live under `terraform/ansible/` (or the provider-specific ansible path) and reference these roles.

## Bundled roles (summary)

### atomic_red_team

Used by the **simulate** flow to run MITRE ATT&amp;CK techniques (Atomic Red Team).

- **Install (Linux):** `install_art_linux.yml` — installs PowerShell and Atomic Red Team (Invoke-AtomicRedTeam) on Ubuntu/Debian/RedHat.
- **Run (Linux):** `run_art_linux.yml` — for each technique, can start/stop CAP Attack (if enabled), then runs `Invoke-AtomicTest` (GetPrereqs, run, Cleanup).
- **Run (Windows):** `run_art_test_windows.yml` — runs Atomic tests on Windows hosts.
- **Entry:** `main.yml` includes the install/run task files based on OS (Ubuntu vs Windows).

Variables (from the simulate request or playbook) include the list of **techniques** (e.g. `T1003.001`, `T1059.003`). The controller (or API/CLI) passes the target host and techniques into the playbook.

### cap_attack

Wraps attack runs with **CAP Attack** (threat capture) on Windows and Linux.

- **Tasks:** Start/stop CAP Attack; optionally upload capture. Used from `atomic_red_team` (Linux) and from Windows playbooks.
- **Variables:** e.g. `cap_attack`, `cap_attack_action` (start/stop), `cap_attack_upload_threat_capture`.

When enabled, the role starts capture before running atoms and stops (and optionally uploads) after. Defaults live in `defaults/main.yml`.

### data_replay

Replays a log file into Splunk via the **oneshot** HTTP input.

- **Tasks:** Copy a file to the target (e.g. `/tmp/data.log`), then POST to `https://localhost:8089/services/data/inputs/oneshot` with `source`, `sourcetype`, `index`, and auth.
- **Variables:** `file_name`, `source`, `sourcetype`, `index`, `attack_range_password` (or Splunk auth). Used for dumping and re-ingesting attack data.

### purplesharp

Runs **PurpleSharp** on Windows hosts (adversary simulation).

- **Tasks:** Download the latest PurpleSharp binary from GitHub into `c:\Tools\PurpleSharp\`, then either run a **simulation playbook** or a list of **techniques**.
- **Includes:** `run_simulation_playbook.yml` when using a playbook; `run_simulation_techniques.yml` when using technique IDs.
- **Variables:** `run_simulation_playbook`, `techniques`, and playbook-specific vars.

## How roles are applied at build time

1. The config (from template) lists servers and their **roles** (and optional **vars**).
2. The controller installs Galaxy requirements (roles defined in the config or a generated `requirements.yml`).
3. Main provisioning playbooks run against the inventory (router + lab hosts); each host gets the roles listed under its entry in `attack_range`.

Example (from a template):

```yaml
attack_range:
  - name: splunk
    ...
    roles:
      - role: P4T12ICK.ludus_ar_splunk
        vars:
          ludus_ar_splunk_password: "Pl3ase-k1Ll-me:p"
      - role: P4T12ICK.ar_guacamole
        vars:
          ar_guacamole_password: "Pl3ase-k1Ll-me:p"
          ar_guacamole_servers: [...]
  - name: win
    ...
    roles:
      - role: P4T12ICK.ludus_ar_windows
        vars:
          ludus_ar_windows_splunk_ip: 10.0.2.10
```

## How simulate uses roles

When you run **simulate** (API or CLI):

1. The controller resolves the **target** host and **techniques** from the request.
2. It runs the Atomic Red Team playbook (and, if applicable, CAP Attack or PurpleSharp) against that host, passing `techniques` (and any other vars).
3. The **atomic_red_team** role (and optionally **cap_attack** or **purplesharp**) runs on the target; result is returned in the API response or CLI output.

So the same Ansible roles used during initial lab provisioning are reused for simulation; the simulate flow only invokes the execution parts (run atoms, run PurpleSharp, etc.) with the chosen target and techniques.

## Customizing and adding roles

- **Galaxy:** Add a role to the requirements used by the controller (or to a playbook’s `roles:` section). Ensure the config’s `attack_range` entries reference the role name and any `vars`.
- **Local:** Add a new role under `modules/ansible/roles/<role_name>/` with `tasks/main.yml` and optional `defaults/`, then reference it in templates/configs as `role: <role_name>` (or by full path if your playbooks use it). The controller and playbook paths must be set so that Ansible can find these roles (usually via `roles_path` or relative to the playbook).

For exact task names and variables, see the task files under `modules/ansible/roles/*/tasks/`.
