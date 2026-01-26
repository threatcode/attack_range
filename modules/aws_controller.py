import os
import ansible_runner
import subprocess
import sys
import signal
import yaml
import json

from python_terraform import Terraform, IsNotFlagged
from modules import aws_service, splunk_sdk
from tabulate import tabulate
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from modules.attack_range_controller import AttackRangeController
from modules.art_simulation_controller import ArtSimulationController
from modules.purplesharp_simulation_controller import PurplesharpSimulationController


class AwsController(AttackRangeController):

    def __init__(self, config: dict):
        super().__init__(config)
        statefile = self.config["general"]["attack_range_name"] + ".terraform.tfstate"
        self.config["general"]["statepath"] = os.path.join(
            os.path.dirname(__file__), "../terraform/aws/state", statefile
        )

        if not aws_service.check_region(self.config["aws"]["region"]):
            self.logger.error(
                "AWS cli region and region in config file are not the same."
            )
            sys.exit(1)

        backend_path_tmp = os.path.join(
            os.path.dirname(__file__), "../terraform/aws/backend.tf.tmp"
        )
        backend_path = os.path.join(
            os.path.dirname(__file__), "../terraform/aws/backend.tf"
        )

        if self.config["aws"]["use_remote_state"] == "1":
            with open(backend_path_tmp, "r") as file:
                filedata = file.read()
            filedata = filedata.replace("[region]", self.config["aws"]["region"])
            filedata = filedata.replace(
                "[bucket]", self.config["aws"]["tf_remote_state_s3_bucket"]
            )
            filedata = filedata.replace(
                "[name]", self.config["general"]["attack_range_name"]
            )
            filedata = filedata.replace(
                "[dynamodb_table]",
                self.config["aws"]["tf_remote_state_dynamo_db_table"],
            )
            with open(backend_path, "w+") as file:
                file.write(filedata)

        else:
            if os.path.isfile(backend_path):
                os.remove(backend_path)

        working_dir = os.path.join(os.path.dirname(__file__), "../terraform/aws")
        self.terraform = Terraform(
            working_dir=working_dir,
            variables=config,
            parallelism=15,
            state=self.config["general"]["statepath"],
        )

        for i in range(len(self.config["windows_servers"])):
            image_name = self.config["windows_servers"][i]["windows_image"]
            if image_name.startswith("windows-server-2016"):
                self.config["windows_servers"][i][
                    "windows_ami"
                ] = "Windows_Server-2016-English-Full-Base-*"

            elif image_name.startswith("windows-server-2019"):
                self.config["windows_servers"][i][
                    "windows_ami"
                ] = "Windows_Server-2019-English-Full-Base-*"
            elif image_name.startswith("windows-server-2022"):
                self.config["windows_servers"][i][
                    "windows_ami"
                ] = "Windows_Server-2022-English-Full-Base-*"
            else:
                self.logger.error("Image " + image_name + " not supported.")
                sys.exit(1)

    def build(self) -> None:
        self.logger.info("[action] > build\n")
        cwd = os.getcwd()
        os.system(
            "cd "
            + os.path.join(os.path.dirname(__file__), "../terraform/aws")
            + "&& terraform init -migrate-state"
        )
        os.system("cd " + cwd)

        return_code, stdout, stderr = self.terraform.apply(
            capture_output="yes", skip_plan=True, no_color=IsNotFlagged
        )

        if not return_code:
            self.logger.info("attack_range has been built using terraform successfully")

        self.show()

    def destroy(self) -> None:
        self.logger.info("[action] > destroy\n")

        cwd = os.getcwd()
        os.system(
            "cd "
            + os.path.join(os.path.dirname(__file__), "../terraform/aws")
            + "&& terraform init "
        )
        os.system("cd " + cwd)

        return_code, stdout, stderr = self.terraform.destroy(
            capture_output="yes",
            no_color=IsNotFlagged,
            force=IsNotFlagged,
            auto_approve=True,
        )

        self.logger.info("attack_range has been destroy using terraform successfully")

    def stop(self, instances_ids=None) -> None:
        instances = []
        if instances_ids is None:
            instances = aws_service.get_all_instances(
                self.config["general"]["key_name"],
                self.config["general"]["attack_range_name"],
                self.config["aws"]["region"],
            )
        else:
            instances = aws_service.get_instances_by_ids(
                instances_ids,
                self.config["general"]["key_name"],
                self.config["general"]["key_name"],
                self.config["general"]["attack_range_name"],
                self.config["aws"]["region"],
            )
        aws_service.change_ec2_state(
            instances, "stopped", self.logger, self.config["aws"]["region"]
        )

    def resume(self, instances_ids=None) -> None:
        instances = []
        if instances_ids is None:
            instances = aws_service.get_all_instances(
                self.config["general"]["key_name"],
                self.config["general"]["attack_range_name"],
                self.config["aws"]["region"],
            )
        else:
            instances = aws_service.get_instances_by_ids(
                instances_ids,
                self.config["general"]["key_name"],
                self.config["general"]["key_name"],
                self.config["general"]["attack_range_name"],
                self.config["aws"]["region"],
            )
        aws_service.change_ec2_state(
            instances, "running", self.logger, self.config["aws"]["region"]
        )

    def simulate(self, engine, target, technique, playbook) -> None:
        self.logger.info("[action] > simulate\n")
        if engine == "ART":
            simulation_controller = ArtSimulationController(self.config)
            simulation_controller.simulate(target, technique)
        if engine == "PurpleSharp":
            simulation_controller = PurplesharpSimulationController(self.config)
            simulation_controller.simulate(target, technique, playbook)

    def start_cap_attack(self, target: str) -> None:
        self.logger.info("[action] > start_cap_attack\n")
        target_public_ip = aws_service.get_single_instance_public_ip(
            target,
            self.config["general"]["key_name"],
            self.config["general"]["attack_range_name"],
            self.config["aws"]["region"],
        )
        private_key_path = self.config["aws"]["private_key_path"]

        if "win" in target:
            ansible_user = "Administrator"
            ansible_port = 5985
            cmd_line = str("-i " + target_public_ip + ", ")
            extravars = {
                "ansible_port": ansible_port,
                "ansible_connection": "winrm",
                "ansible_winrm_server_cert_validation": "ignore",
                "ansible_user": ansible_user,
                "ansible_password": self.config["general"]["attack_range_password"],
                "cap_attack_action": "start",
            }
        else:
            ansible_user = "ubuntu"
            ansible_port = 22
            cmd_line = (
                "-u "
                + ansible_user
                + " --private-key "
                + private_key_path
                + " -i "
                + target_public_ip
                + ", "
            )
            extravars = {
                "ansible_port": ansible_port,
                "ansible_connection": "ssh",
                "ansible_user": ansible_user,
                "cap_attack_action": "start",
            }

        ansible_runner.run(
            private_data_dir=os.path.join(os.path.dirname(__file__), "../"),
            cmdline=cmd_line,
            roles_path=os.path.join(os.path.dirname(__file__), "ansible/roles"),
            playbook=os.path.join(os.path.dirname(__file__), "ansible/cap_attack.yml"),
            extravars=extravars,
            verbosity=0,
        )

    def stop_cap_attack(self, target: str) -> None:
        self.logger.info("[action] > stop_cap_attack\n")
        target_public_ip = aws_service.get_single_instance_public_ip(
            target,
            self.config["general"]["key_name"],
            self.config["general"]["attack_range_name"],
            self.config["aws"]["region"],
        )
        private_key_path = self.config["aws"]["private_key_path"]

        if "win" in target:
            ansible_user = "Administrator"
            ansible_port = 5985
            cmd_line = str("-i " + target_public_ip + ", ")
            extravars = {
                "ansible_port": ansible_port,
                "ansible_connection": "winrm",
                "ansible_winrm_server_cert_validation": "ignore",
                "ansible_user": ansible_user,
                "ansible_password": self.config["general"]["attack_range_password"],
                "cap_attack_action": "stop",
                "cap_attack_upload_threat_capture": self.config["simulation"][
                    "cap_attack_upload_threat_capture"
                ],
            }
        else:
            ansible_user = "ubuntu"
            ansible_port = 22
            cmd_line = (
                "-u "
                + ansible_user
                + " --private-key "
                + private_key_path
                + " -i "
                + target_public_ip
                + ", "
            )
            extravars = {
                "ansible_port": ansible_port,
                "ansible_connection": "ssh",
                "ansible_user": ansible_user,
                "cap_attack_action": "stop",
                "cap_attack_upload_threat_capture": self.config["simulation"][
                    "cap_attack_upload_threat_capture"
                ],
            }

        ansible_runner.run(
            private_data_dir=os.path.join(os.path.dirname(__file__), "../"),
            cmdline=cmd_line,
            roles_path=os.path.join(os.path.dirname(__file__), "ansible/roles"),
            playbook=os.path.join(os.path.dirname(__file__), "ansible/cap_attack.yml"),
            extravars=extravars,
            verbosity=0,
        )

    def _get_user_name_from_config(self, instance_name: str, is_windows: bool = False) -> str:
        """Get user_name from config based on instance name.
        
        Args:
            instance_name: Instance name (e.g., "ar-splunk", "ar-win")
            is_windows: Whether this is a Windows instance
            
        Returns:
            Username from config or default based on OS and cloud provider
        """
        # Extract server name from instance name (remove "ar-" prefix)
        if instance_name.startswith("ar-"):
            server_name = instance_name[3:]  # Remove "ar-" prefix
            # Look up server in attack_range config
            attack_range_config = self.config.get("attack_range", [])
            for server in attack_range_config:
                if server.get("name") == server_name:
                    user_name = server.get("user_name")
                    if user_name:
                        return user_name
        
        # Default values if not found in config
        if is_windows:
            return "Administrator"
        else:
            # Try to infer from instance name
            if "kali" in instance_name.lower():
                return "kali"
            return "ubuntu"
    
    def show(self) -> None:
        self.logger.info("[action] > show\n")
        instances = aws_service.get_all_instances(
            self.config["general"]["key_name"],
            self.config["general"]["attack_range_name"],
            self.config["aws"]["region"],
        )
        response = []
        messages = []
        instances_running = False
        splunk_ip = ""
        for instance in instances:
            if instance["State"]["Name"] == "running":
                instances_running = True
                # Find the Name tag
                instance_name = None
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name":
                        instance_name = tag["Value"]
                        break
                
                if instance_name is None:
                    instance_name = "Unknown"
                
                response.append(
                    [
                        instance_name,
                        instance["State"]["Name"],
                        instance["NetworkInterfaces"][0]["Association"]["PublicIp"],
                        instance["InstanceId"],
                    ]
                )
                if instance_name.startswith("ar-splunk"):
                    splunk_ip = instance["NetworkInterfaces"][0]["Association"][
                        "PublicIp"
                    ]
                    username = self._get_user_name_from_config(instance_name, is_windows=False)
                    messages.append(
                        "\nAccess Guacamole via:\n\tWeb > http://"
                        + instance["NetworkInterfaces"][0]["Association"]["PublicIp"]
                        + ":8080/guacamole"
                        + "\n\tusername: Admin \n\tpassword: "
                        + self.config["general"]["attack_range_password"]
                    )
                    if self.config["splunk_server"]["install_es"] == "1":
                        messages.append(
                            "\nAccess Splunk via:\n\tWeb > https://"
                            + instance["NetworkInterfaces"][0]["Association"][
                                "PublicIp"
                            ]
                            + f":8000\n\tSSH > ssh -i"
                            + self.config["aws"]["private_key_path"]
                            + f" {username}@"
                            + instance["NetworkInterfaces"][0]["Association"][
                                "PublicIp"
                            ]
                            + "\n\tusername: admin \n\tpassword: "
                            + self.config["general"]["attack_range_password"]
                        )
                    else:
                        messages.append(
                            "\nAccess Splunk via:\n\tWeb > http://"
                            + instance["NetworkInterfaces"][0]["Association"][
                                "PublicIp"
                            ]
                            + f":8000\n\tSSH > ssh -i"
                            + self.config["aws"]["private_key_path"]
                            + f" {username}@"
                            + instance["NetworkInterfaces"][0]["Association"][
                                "PublicIp"
                            ]
                            + "\n\tusername: admin \n\tpassword: "
                            + self.config["general"]["attack_range_password"]
                        )
                elif instance_name.startswith("ar-phantom"):
                    if (
                        "splunk_soar-unpriv-6"
                        in self.config["phantom_server"]["phantom_app"]
                    ):
                        messages.append(
                            "\nAccess Phantom via:\n\tWeb > https://"
                            + instance["NetworkInterfaces"][0]["Association"][
                                "PublicIp"
                            ]
                            + ":8443"
                            + "\n\tSSH > ssh -i"
                            + self.config["aws"]["private_key_path"]
                            + " centos@"
                            + instance["NetworkInterfaces"][0]["Association"][
                                "PublicIp"
                            ]
                            + "\n\tusername: soar_local_admin \n\tpassword: "
                            + self.config["general"]["attack_range_password"]
                        )
                    else:
                        messages.append(
                            "\nAccess Phantom via:\n\tWeb > https://"
                            + instance["NetworkInterfaces"][0]["Association"][
                                "PublicIp"
                            ]
                            + ":8443"
                            + "\n\tSSH > ssh -i"
                            + self.config["aws"]["private_key_path"]
                            + " centos@"
                            + instance["NetworkInterfaces"][0]["Association"][
                                "PublicIp"
                            ]
                            + "\n\tusername: admin \n\tpassword: "
                            + self.config["general"]["attack_range_password"]
                        )
                elif instance_name.startswith("ar-win"):
                    username = self._get_user_name_from_config(instance_name, is_windows=True)
                    messages.append(
                        "\nAccess Windows via:\n\tRDP > rdp://"
                        + instance["NetworkInterfaces"][0]["Association"]["PublicIp"]
                        + f":3389\n\tusername: {username} \n\tpassword: "
                        + self.config["general"]["attack_range_password"]
                    )
                elif instance_name.startswith("ar-linux"):
                    username = self._get_user_name_from_config(instance_name, is_windows=False)
                    messages.append(
                        "\nAccess Linux via:\n\tSSH > ssh -i"
                        + self.config["aws"]["private_key_path"]
                        + f" {username}@"
                        + instance["NetworkInterfaces"][0]["Association"]["PublicIp"]
                        + f"\n\tusername: {username} \n\tpassword: "
                        + self.config["general"]["attack_range_password"]
                    )
                elif instance_name.startswith("ar-kali"):
                    username = self._get_user_name_from_config(instance_name, is_windows=False)
                    messages.append(
                        "\nAccess Kali via:\n\tSSH > ssh -i"
                        + self.config["aws"]["private_key_path"]
                        + f" {username}@"
                        + instance["NetworkInterfaces"][0]["Association"]["PublicIp"]
                        + f"\n\tusername: {username} \n\tpassword: "
                        + self.config["general"]["attack_range_password"]
                    )
                elif instance_name.startswith("ar-nginx"):
                    username = self._get_user_name_from_config(instance_name, is_windows=False)
                    messages.append(
                        "\nAccess Nginx Web Proxy via:\n\tSSH > ssh -i"
                        + self.config["aws"]["private_key_path"]
                        + f" {username}@"
                        + instance["NetworkInterfaces"][0]["Association"]["PublicIp"]
                    )
                elif instance_name.startswith("ar-zeek"):
                    username = self._get_user_name_from_config(instance_name, is_windows=False)
                    messages.append(
                        "\nAccess Zeek via:\n\tSSH > ssh -i"
                        + self.config["aws"]["private_key_path"]
                        + f" {username}@"
                        + instance["NetworkInterfaces"][0]["Association"]["PublicIp"]
                        + f"\n\tusername: {username} \n\tpassword: "
                        + self.config["general"]["attack_range_password"]
                    )
                elif instance_name.startswith("ar-snort"):
                    username = self._get_user_name_from_config(instance_name, is_windows=False)
                    messages.append(
                        "\nAccess Snort via:\n\tSSH > ssh -i"
                        + self.config["aws"]["private_key_path"]
                        + f" {username}@"
                        + instance["NetworkInterfaces"][0]["Association"]["PublicIp"]
                        + f"\n\tusername: {username} \n\tpassword: "
                        + self.config["general"]["attack_range_password"]
                    )
                elif instance_name.startswith("ar-caldera"):
                    messages.append(
                        "\nAccess Caldera via:\n\tWeb > http://"
                        + instance["NetworkInterfaces"][0]["Association"]["PublicIp"]
                        + ":8888\n\tSSH > ssh -i"
                        + self.config["aws"]["private_key_path"]
                        + " admin@"
                        + instance["NetworkInterfaces"][0]["Association"]["PublicIp"]
                        + "\n\tusername: admin \n\tpassword: "
                        + self.config["general"]["attack_range_password"]
                    )
            else:
                # Find the Name tag for non-running instances
                instance_name = None
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name":
                        instance_name = tag["Value"]
                        break
                
                if instance_name is None:
                    instance_name = "Unknown"
                
                response.append(
                    [instance_name, instance["State"]["Name"]]
                )

        print()
        print("Status Virtual Machines\n")
        if len(response) > 0:

            if instances_running:
                print(
                    tabulate(
                        response,
                        headers=["Name", "Status", "IP Address", "Instance ID"],
                    )
                )
                for msg in messages:
                    print(msg)
            else:
                print(tabulate(response, headers=["Name", "Status", "Instance ID"]))

            print()
        else:
            print("ERROR: Can't find configured Attack Range Instances")

    def dump(self, dump_name, search, earliest, latest) -> None:
        self.logger.info("Dump log data")
        dump_search = (
            "search "
            + search
            + " earliest=-"
            + earliest
            + " latest="
            + latest
            + " | sort 0 _time"
        )
        self.logger.info("Dumping Splunk Search: " + dump_search)
        out = open(os.path.join(os.path.dirname(__file__), "../" + dump_name), "wb")

        splunk_instance = (
            "ar-splunk-"
            + self.config["general"]["key_name"]
            + "-"
            + self.config["general"]["attack_range_name"]
        )
        splunk_sdk.export_search(
            aws_service.get_single_instance_public_ip(
                splunk_instance,
                self.config["general"]["key_name"],
                self.config["general"]["attack_range_name"],
                self.config["aws"]["region"],
            ),
            s=dump_search,
            password=self.config["general"]["attack_range_password"],
            out=out,
        )
        out.close()
        self.logger.info("[Completed]")

    def replay(self, file_name, index, sourcetype, source) -> None:
        ### check if input log file is afile path or just a file name
        ### if file name ,assume it is in current working dir of attack_range.py
        if Path(file_name).parent == Path("."):
            file_name = str(Path("../..")/file_name)
        ansible_vars = {}
        ansible_vars["file_name"] = file_name
        ansible_vars["ansible_user"] = "ubuntu"
        ansible_vars["ansible_ssh_private_key_file"] = self.config["aws"][
            "private_key_path"
        ]
        ansible_vars["attack_range_password"] = self.config["general"][
            "attack_range_password"
        ]
        ansible_vars["ansible_port"] = 22
        ansible_vars["sourcetype"] = sourcetype
        ansible_vars["source"] = source
        ansible_vars["index"] = index

        splunk_instance = (
            "ar-splunk-"
            + self.config["general"]["key_name"]
            + "-"
            + self.config["general"]["attack_range_name"]
        )
        splunk_ip = aws_service.get_single_instance_public_ip(
            splunk_instance,
            self.config["general"]["key_name"],
            self.config["general"]["attack_range_name"],
            self.config["aws"]["region"],
        )
        cmdline = "-i %s, -u %s" % (splunk_ip, ansible_vars["ansible_user"])
        runner = ansible_runner.run(
            private_data_dir=os.path.join(os.path.dirname(__file__), "../"),
            cmdline=cmdline,
            roles_path=os.path.join(os.path.dirname(__file__), "ansible/roles"),
            playbook=os.path.join(os.path.dirname(__file__), "ansible/data_replay.yml"),
            extravars=ansible_vars,
        )

    def create_remote_backend(self, backend_name) -> None:
        if not aws_service.check_s3_bucket(backend_name):
            self.logger.info(
                "Can not access remote S3 bucket with name " + backend_name
            )
            self.logger.info("Try to create a S3 for remote backend.")
            aws_service.create_s3_bucket(
                backend_name, self.config["aws"]["region"], self.logger
            )

        # create DynamoDB
        aws_service.create_dynamoo_db(
            backend_name, self.config["aws"]["region"], self.logger
        )

        self.config["aws"]["private_key_path"] = str(
            Path(backend_name + ".key").resolve()
        )
        self.config["general"]["key_name"] = backend_name

        # privat key in secrets manager
        if not aws_service.check_secret_exists(backend_name):
            key_material = aws_service.create_key_pair(
                backend_name, self.config["aws"]["region"], self.logger
            )
            aws_service.create_secret(
                backend_name, key_material, self.config, self.logger
            )

        with open(
            os.path.join(os.path.dirname(__file__), "../attack_range.yml"), "w"
        ) as outfile:
            yaml.dump(self.config, outfile, default_flow_style=False, sort_keys=False)

        # write versions.tf
        j2_env = Environment(
            loader=FileSystemLoader(
                os.path.join(os.path.dirname(__file__), "../terraform/aws")
            ),
            trim_blocks=True,
        )
        template = j2_env.get_template("versions.tf.j2")
        output = template.render(
            backend_name=backend_name, region=self.config["aws"]["region"]
        )
        with open("terraform/aws/versions.tf", "w") as f:
            output = output.encode("ascii", "ignore").decode("ascii")
            f.write(output)

    def delete_remote_backend(self, backend_name) -> None:
        aws_service.delete_s3_bucket(
            backend_name, self.config["aws"]["region"], self.logger
        )
        aws_service.delete_dynamo_db(
            backend_name, self.config["aws"]["region"], self.logger
        )
        aws_service.delete_secret(backend_name, self.logger)
        aws_service.delete_key_pair(
            backend_name, self.config["aws"]["region"], self.logger
        )
        try:
            os.remove(
                os.path.join(os.path.dirname(__file__), "../terraform/aws/versions.tf")
            )
        except Exception as e:
            self.logger.error(e)
        try:
            os.remove(
                os.path.join(os.path.dirname(__file__), "../", backend_name + ".key")
            )
        except Exception as e:
            self.logger.error(e)

    def init_remote_backend(self, backend_name) -> None:
        if not aws_service.check_s3_bucket(backend_name):
            self.logger.error("Can't find S3 bucket with name " + backend_name)
            sys.exit(1)
        if not aws_service.check_secret_exists(backend_name):
            self.logger.error("Secret doesn't exist with name " + backend_name)
            sys.exit(1)

        aws_service.get_secret_key(backend_name, self.logger)
        config = aws_service.get_secret_config(backend_name, self.logger)
        config["aws"]["private_key_path"] = str(Path(backend_name + ".key").resolve())
        with open(
            os.path.join(os.path.dirname(__file__), "../attack_range.yml"), "w"
        ) as outfile:
            yaml.dump(config, outfile, default_flow_style=False, sort_keys=False)

        # write versions.tf
        j2_env = Environment(
            loader=FileSystemLoader(
                os.path.join(os.path.dirname(__file__), "../terraform/aws")
            ),
            trim_blocks=True,
        )
        template = j2_env.get_template("versions.tf.j2")
        output = template.render(
            backend_name=backend_name, region=self.config["aws"]["region"]
        )
        with open("terraform/aws/versions.tf", "w") as f:
            output = output.encode("ascii", "ignore").decode("ascii")
            f.write(output)
