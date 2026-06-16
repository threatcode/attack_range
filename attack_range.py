#!/usr/bin/env python3
"""
Simple script to execute AttackRangeController commands.
"""

import os
import sys
import argparse
import glob
import json
import yaml

from attack_range.attack_range_controller import AttackRangeController
from attack_range.managers.ansible_manager import resolve_local_role_name
from attack_range.utils import prepare_config_from_template, resolve_template_path

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.
    
    :param config_path: Path to the configuration file
    :return: Configuration dictionary
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Failed to parse YAML configuration: {e}")
        sys.exit(1)


def build_action(args):
    """Execute build action."""
    # Template is required
    if not args.template:
        print("Error: --template is required. Please specify a template from the templates folder.")
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        if os.path.exists(templates_dir):
            templates = [f for f in os.listdir(templates_dir) if f.endswith(('.yml', '.yaml'))]
            if templates:
                print("\nAvailable templates:")
                for t in sorted(templates):
                    print(f"  - {t}")
        sys.exit(1)
    
    # Set up directories
    base_dir = os.path.dirname(__file__)
    templates_dir = os.path.join(base_dir, "templates")
    config_dir = os.path.join(base_dir, "config")
    
    try:
        # Prepare config from template (loads template, adds metadata, saves to config folder)
        config, config_path, attack_range_id = prepare_config_from_template(
            args.template,
            templates_dir,
            config_dir,
            generate_id=True
        )
        
        print(f"Prepared config from template: {args.template}")
        print(f"Attack Range ID: {attack_range_id}")
        print(f"Config saved to: {config_path}")
        
        # Create controller with prepared config
        controller = AttackRangeController(config, config_path=config_path)
        controller.build()
        
    except FileNotFoundError as e:
        print(f"Error: Template file not found: {e}")
        # List available templates
        if os.path.exists(templates_dir):
            # Check provider subdirectories
            templates = []
            for provider in ["aws", "azure", "gcp"]:
                provider_dir = os.path.join(templates_dir, provider)
                if os.path.exists(provider_dir):
                    provider_templates = [f for f in os.listdir(provider_dir) if f.endswith(('.yml', '.yaml'))]
                    templates.extend([f"{provider}/{t}" for t in provider_templates])
            # Also check root templates folder
            if os.path.exists(templates_dir):
                root_templates = [f for f in os.listdir(templates_dir) if f.endswith(('.yml', '.yaml'))]
                templates.extend(root_templates)
            
            if templates:
                print("\nAvailable templates:")
                for t in sorted(set(templates)):
                    print(f"  - {t}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to prepare config from template: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def destroy_action(args):
    """Execute destroy action."""
    config_dir = os.path.join(os.path.dirname(__file__), "config")
    
    # If config not specified, check config folder
    if not args.config:
        # Find all .yml files in config folder
        yml_files = glob.glob(os.path.join(config_dir, "*.yml"))
        
        if not yml_files:
            print("Error: No config files found in config folder.")
            print("Please specify a config file using --config")
            sys.exit(1)
        
        if len(yml_files) == 1:
            # Only one file exists, use it automatically
            config_path = yml_files[0]
            config_name = os.path.basename(config_path)
            print(f"Found single config file: {config_name}")
        else:
            # Multiple files exist, require user to specify
            print(f"Error: Multiple config files found ({len(yml_files)} files).")
            print("Please specify which config file to use with --config")
            print("\nAvailable config files:")
            for yml_file in sorted(yml_files):
                config_name = os.path.basename(yml_file)
                print(f"  - {config_name}")
            sys.exit(1)
    else:
        # User specified config file
        config_path = args.config
        
        # If only a filename is provided (no directory), look in config folder
        if os.path.dirname(config_path) == '' or os.path.dirname(config_path) == '.':
            config_path = os.path.join(config_dir, os.path.basename(config_path))
        
        # Check if config file exists
        if not os.path.exists(config_path):
            print(f"Error: Config file not found: {config_path}")
            sys.exit(1)
    
    # Load config from the specified file
    config = load_config(config_path)
    # Get absolute path to config file
    config_path = os.path.abspath(config_path)
    controller = AttackRangeController(config, config_path=config_path)
    controller.destroy()


def simulate_action(args):
    """Execute simulate action."""
    config_dir = os.path.join(os.path.dirname(__file__), "config")
    
    # If config not specified, check config folder
    if not args.config:
        # Find all .yml files in config folder
        yml_files = glob.glob(os.path.join(config_dir, "*.yml"))
        
        if not yml_files:
            print("Error: No config files found in config folder.")
            print("Please specify a config file using --config")
            sys.exit(1)
        
        if len(yml_files) == 1:
            # Only one file exists, use it automatically
            config_path = yml_files[0]
            config_name = os.path.basename(config_path)
            print(f"Found single config file: {config_name}")
        else:
            # Multiple files exist, require user to specify
            print(f"Error: Multiple config files found ({len(yml_files)} files).")
            print("Please specify which config file to use with --config")
            print("\nAvailable config files:")
            for yml_file in sorted(yml_files):
                config_name = os.path.basename(yml_file)
                print(f"  - {config_name}")
            sys.exit(1)
    else:
        # User specified config file
        config_path = args.config
        
        # If only a filename is provided (no directory), look in config folder
        if os.path.dirname(config_path) == '' or os.path.dirname(config_path) == '.':
            config_path = os.path.join(config_dir, os.path.basename(config_path))
        
        # Check if config file exists
        if not os.path.exists(config_path):
            print(f"Error: Config file not found: {config_path}")
            sys.exit(1)
    
    techniques = []
    if args.techniques:
        techniques = [t.strip() for t in args.techniques.split(",") if t.strip()]

    atomics = []
    if args.atomics:
        for part in args.atomics.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" not in part:
                print(
                    f"Error: Invalid atomic entry {part!r}. "
                    "Use TECHNIQUE:GUID (e.g., T1003.001:0be2230c-9ab3-4ac2-8826-3199b9a0ebf8)."
                )
                sys.exit(1)
            technique, guid = part.split(":", 1)
            atomics.append({"technique": technique.strip(), "guid": guid.strip()})

    atomic_files = []
    if args.atomic_files:
        for file_path in args.atomic_files.split(","):
            file_path = file_path.strip()
            if not file_path:
                continue
            if not os.path.isfile(file_path):
                print(f"Error: Atomic file not found: {file_path}")
                sys.exit(1)
            atomic_files.append({"path": os.path.abspath(file_path)})

    if not techniques and not atomics and not atomic_files:
        print(
            "Error: Specify at least one technique ID (--techniques), "
            "atomic (--atomics TECHNIQUE:GUID,...), or atomic file (--atomic-file PATH,...)."
        )
        sys.exit(1)
    
    # Load config from the specified file
    config = load_config(config_path)
    # Get absolute path to config file
    config_path = os.path.abspath(config_path)
    controller = AttackRangeController(config, config_path=config_path)
    controller.simulate(args.target, techniques, atomics, atomic_files)


def _resolve_config_path(config_arg: str | None) -> str:
    """Resolve config path from CLI arg or single config in config/."""
    config_dir = os.path.join(os.path.dirname(__file__), "config")

    if not config_arg:
        yml_files = glob.glob(os.path.join(config_dir, "*.yml"))
        if not yml_files:
            print("Error: No config files found in config folder.")
            print("Please specify a config file using --config")
            sys.exit(1)
        if len(yml_files) > 1:
            print(f"Error: Multiple config files found ({len(yml_files)} files).")
            print("Please specify which config file to use with --config")
            print("\nAvailable config files:")
            for yml_file in sorted(yml_files):
                print(f"  - {os.path.basename(yml_file)}")
            sys.exit(1)
        return os.path.abspath(yml_files[0])

    config_path = config_arg
    if os.path.dirname(config_path) in ("", "."):
        config_path = os.path.join(config_dir, os.path.basename(config_path))
    if not os.path.exists(config_path):
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    return os.path.abspath(config_path)


def _load_role_vars_file(vars_file_path: str, role_paths: list[str]) -> dict[str, dict]:
    """Load per-role vars from YAML/JSON; shared vars apply to all roles when unkeyed."""
    with open(vars_file_path, "r", encoding="utf-8") as f:
        if vars_file_path.endswith(".json"):
            data = json.load(f)
        else:
            data = yaml.safe_load(f)

    if not data:
        return {}
    if not isinstance(data, dict):
        print("Error: --vars-file must contain a YAML/JSON object.")
        sys.exit(1)

    resolved_names = [resolve_local_role_name(os.path.abspath(path)) for path in role_paths]
    if any(name in data for name in resolved_names):
        return {name: data.get(name, {}) or {} for name in resolved_names}
    return {name: data for name in resolved_names}


def apply_role_action(args):
    """Execute apply-role action."""
    if not args.role:
        print("Error: Specify at least one local role directory with -r/--role.")
        sys.exit(1)

    for role_path in args.role:
        if not os.path.isdir(role_path):
            print(f"Error: Role directory not found: {role_path}")
            sys.exit(1)

    config_path = _resolve_config_path(args.config)
    vars_by_role = {}
    if args.vars_file:
        if not os.path.isfile(args.vars_file):
            print(f"Error: Vars file not found: {args.vars_file}")
            sys.exit(1)
        vars_by_role = _load_role_vars_file(args.vars_file, args.role)

    roles = []
    for role_path in args.role:
        abs_path = os.path.abspath(role_path)
        role_name = resolve_local_role_name(abs_path)
        role_entry = {"path": abs_path}
        if vars_by_role:
            role_entry["vars"] = vars_by_role.get(role_name, {})
        roles.append(role_entry)

    config = load_config(config_path)
    controller = AttackRangeController(config, config_path=config_path)
    try:
        result = controller.apply_role(args.target, roles)
        print(f"Successfully applied role(s) on {result['target']}: {', '.join(result['roles_applied'])}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)


def share_action(args):
    """Execute share action."""
    config_dir = os.path.join(os.path.dirname(__file__), "config")

    if not args.config:
        yml_files = glob.glob(os.path.join(config_dir, "*.yml"))
        if not yml_files:
            print("Error: No config files found in config folder.")
            print("Please specify a config file using --config")
            sys.exit(1)
        if len(yml_files) > 1:
            print("Error: Multiple config files found. Please specify which to use with --config")
            print("\nAvailable config files:")
            for yml_file in sorted(yml_files):
                print(f"  - {os.path.basename(yml_file)}")
            sys.exit(1)
        config_path = yml_files[0]
    else:
        config_path = args.config
        if os.path.dirname(config_path) in ('', '.'):
            config_path = os.path.join(config_dir, os.path.basename(config_path))
        if not os.path.exists(config_path):
            print(f"Error: Config file not found: {config_path}")
            sys.exit(1)

    config = load_config(config_path)
    config_path = os.path.abspath(config_path)
    controller = AttackRangeController(config, config_path=config_path)

    try:
        config_content = controller.share(args.name)
        print("\n" + "=" * 60)
        print(f"WireGuard config for '{args.name}' (saved to general.sharing):")
        print("=" * 60)
        print(config_content)
        print("=" * 60)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Simple script to execute AttackRangeController commands"
    )
    
    subparsers = parser.add_subparsers(
        title="actions",
        dest="action",
        help="Available actions",
        required=True
    )
    
    # Build action
    build_parser = subparsers.add_parser(
        "build",
        help="Build the attack range infrastructure"
    )
    build_parser.add_argument(
        "-t",
        "--template",
        required=True,
        help="Template from the templates folder (e.g., splunk_minimal_aws, splunk_windows_aws)",
    )
    build_parser.set_defaults(func=build_action)
    
    # Destroy action
    destroy_parser = subparsers.add_parser(
        "destroy",
        help="Destroy the attack range infrastructure"
    )
    destroy_parser.add_argument(
        "-c",
        "--config",
        help="Path to the config file (optional if only one config exists in config/ folder)",
    )
    destroy_parser.set_defaults(func=destroy_action)
    
    # Simulate action
    simulate_parser = subparsers.add_parser(
        "simulate",
        help="Run Atomic Red Team techniques against a target server"
    )
    simulate_parser.add_argument(
        "-c",
        "--config",
        help="Path to the config file (optional if only one config exists in config/ folder)",
    )
    simulate_parser.add_argument(
        "-t",
        "--target",
        required=True,
        help="Target server name (must match a server name in attack_range config)",
    )
    simulate_parser.add_argument(
        "-te",
        "--techniques",
        help="Comma-separated MITRE ATT&CK technique IDs (e.g., T1003.001,T1059.003); runs all atomics per technique",
    )
    simulate_parser.add_argument(
        "-a",
        "--atomics",
        help=(
            "Comma-separated TECHNIQUE:GUID pairs (e.g., "
            "T1003.001:0be2230c-9ab3-4ac2-8826-3199b9a0ebf8); runs one atomic per pair"
        ),
    )
    simulate_parser.add_argument(
        "-f",
        "--atomic-file",
        dest="atomic_files",
        help=(
            "Comma-separated paths to custom atomic YAML files on this machine "
            "(deployed to the target host and executed)"
        ),
    )
    simulate_parser.set_defaults(func=simulate_action)

    # Apply-role action
    apply_role_parser = subparsers.add_parser(
        "apply-role",
        help="Stage and execute local Ansible roles against a target server",
    )
    apply_role_parser.add_argument(
        "-c",
        "--config",
        help="Path to the config file (optional if only one config exists in config/ folder)",
    )
    apply_role_parser.add_argument(
        "-t",
        "--target",
        required=True,
        help="Target server name (must match a server name in attack_range config)",
    )
    apply_role_parser.add_argument(
        "-r",
        "--role",
        action="append",
        required=True,
        help="Path to a local Ansible role directory (repeat for multiple roles)",
    )
    apply_role_parser.add_argument(
        "--vars-file",
        help="YAML or JSON file with role variables (keyed by role name, or shared across all roles)",
    )
    apply_role_parser.set_defaults(func=apply_role_action)

    # Share action
    share_parser = subparsers.add_parser(
        "share",
        help="Share the attack range: generate a new WireGuard config for the given name, run playbooks, save to general.sharing",
    )
    share_parser.add_argument(
        "-c",
        "--config",
        help="Path to the config file (optional if only one config exists in config/ folder)",
    )
    share_parser.add_argument(
        "-n",
        "--name",
        required=True,
        help="Share name (e.g. 'alice') — used as the new WireGuard client name",
    )
    share_parser.set_defaults(func=share_action)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
