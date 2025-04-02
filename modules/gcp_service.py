
from google.auth import default
from google.cloud.compute_v1 import RegionsClient
from google.cloud import compute_v1, storage, bigtable, secretmanager
import sys
import os
import json
import time



def check_region(config_region):
    credentials, project = default()
    client = RegionsClient()

    # List regions for the project
    regions = [region.name for region in client.list(project=project)]

    # Check if the configured region matches any in the project
    return config_region in regions


def get_all_instances(key_name, ar_name, region):
    credentials, project = default()
    instance_client = compute_v1.InstancesClient()

    # Get the list of instances in the specified region
    instances = []
    zone_client = compute_v1.ZonesClient()
    zones = [zone.name for zone in zone_client.list(project=project) if region in zone.name]

    for zone in zones:
        request = compute_v1.AggregatedListInstancesRequest(
            project=project,
            filter=f"tags.items:ar- AND name:{key_name}"
        )
        response = instance_client.aggregated_list(request=request)
        for _, scoped_list in response.items():
            if 'instances' in scoped_list:
                for instance in scoped_list['instances']:
                    if instance.status != 'TERMINATED':
                        if 'labels' in instance:
                            for key, value in instance.labels.items():
                                if key_name in value and ar_name in value:
                                    instances.append(instance)

    return instances


def get_instance_by_name(project_id, instance_name, key_name, ar_name, region):
    client = compute_v1.InstancesClient()

    # Get the zones in the specified region
    zone_client = compute_v1.ZonesClient()
    zones = [zone.name for zone in zone_client.list(project=project_id) if region in zone.name]

    for zone in zones:
        request = compute_v1.ListInstancesRequest(
            project=project_id,
            zone=zone
        )
        response = client.list(request=request)

        for instance in response:
            # Check if instance name matches
            if instance.name == instance_name:
                # Validate metadata (key_name and ar_name are likely stored in metadata or labels)
                if 'labels' in instance:
                    labels = instance.labels
                    if key_name in labels.values() and ar_name in labels.values():
                        return instance

    return None  # Return None if no matching instance is found
        
def get_instances_by_ids(project_id, instance_ids, instance_name, key_name, ar_name, region):
    client = compute_v1.InstancesClient()

    # Get the zones in the specified region
    zone_client = compute_v1.ZonesClient()
    zones = [zone.name for zone in zone_client.list(project=project_id) if region in zone.name]

    result = []
    for zone in zones:
        request = compute_v1.ListInstancesRequest(
            project=project_id,
            zone=zone
        )
        response = client.list(request=request)

        for instance in response:
            # Check if the instance ID matches
            if instance.id in instance_ids:
                # Validate metadata (key_name and ar_name are likely stored in labels or metadata)
                if 'labels' in instance:
                    labels = instance.labels
                    if key_name in labels.values() and ar_name in labels.values():
                        result.append(instance)

    return result


def get_single_instance_public_ip(project_id, instance_name, key_name, ar_name, region):
    client = compute_v1.InstancesClient()

    # Get the zones in the specified region
    zone_client = compute_v1.ZonesClient()
    zones = [zone.name for zone in zone_client.list(project=project_id) if region in zone.name]

    for zone in zones:
        request = compute_v1.GetInstanceRequest(
            project=project_id,
            zone=zone,
            instance=instance_name
        )
        try:
            instance = client.get(request=request)

            # Check if labels match key_name and ar_name
            if 'labels' in instance:
                labels = instance.labels
                if key_name in labels.values() and ar_name in labels.values():
                    # Extract the public IP
                    for network_interface in instance.network_interfaces:
                        if network_interface.access_configs:
                            return network_interface.access_configs[0].nat_ip

        except Exception as e:
            continue  # Skip if the instance is not found in the current zone

    return None  # Return None if no matching instance or public IP is found


def change_instance_state(project_id, instances, new_state, log, region):
    client = compute_v1.InstancesClient()

    if len(instances) == 0:
        log.error('No instances passed.')
        sys.exit(1)

    for instance in instances:
        instance_name = instance['name']
        zone = instance['zone'].split('/')[-1]  # Extract zone from the full resource URL

        try:
            if new_state == 'stopped' and instance['status'] == 'RUNNING':
                operation = client.stop(project=project_id, zone=zone, instance=instance_name)
                log.info(f'Successfully stopped instance with name {instance_name}. Operation ID: {operation.name}')

            elif new_state == 'running' and instance['status'] == 'TERMINATED':
                operation = client.start(project=project_id, zone=zone, instance=instance_name)
                log.info(f'Successfully started instance with name {instance_name}. Operation ID: {operation.name}')

        except Exception as e:
            log.error(f"Failed to change state for instance {instance_name}: {e}")


def image_available(image_name, project_id):
    client = compute_v1.ImagesClient()

    try:
        # Get the image details
        image = client.get(project=project_id, image=image_name)

        # Check if the image is in "READY" state
        if image.status == "READY":
            return True
    except Exception as e:
        # Image does not exist or another error occurred
        return False

    return False

# not needed
def ami_available_other_region(ami_name):
    regions = [
        "us-east-1", 
        "us-east-2", 
        "us-west-1", 
        "us-west-2", 
        "ca-central-1", 
        "eu-west-1", 
        "eu-west-2", 
        "eu-central-1", 
        "ap-southeast-1", 
        "ap-southeast-2", 
        "ap-south-1", 
        "ap-northeast-1", 
        "ap-northeast-2", 
        "sa-east-1", 
        "cn-north-1"
    ]

    for region in regions:
        if ami_available(ami_name, region):
            return {"region": region, "image_id": get_image_id(ami_name, region)}

    return {}

def get_image_id(image_name, project_id):
    client = compute_v1.ImagesClient()

    try:
        # Retrieve the image details
        image = client.get(project=project_id, image=image_name)
        return image.self_link
    except Exception as e:
        # Image not found or another error occurred
        return None

# not needed for now
def copy_image(ami_name, ami_image_id, source_region, dest_region):
    session = boto3.client('ec2',region_name=dest_region)

    response = session.copy_image(
        Name=ami_name,
        Description='Copied this AMI from region ' + source_region,
        SourceImageId=ami_image_id,
        SourceRegion=source_region
    )

    for x in range(0, 10):
        if ami_available(ami_name, dest_region):
            break
        print("Image not yet available. " + str(10-x) + " tries left.")
        time.sleep(60)

    if not ami_available(ami_name, dest_region):
        print("Error: Copying of AMI took longer as expected.")
        sys.exit(1)


def check_gcs_bucket(bucket_name):
    client = storage.Client()

    # Data to write to the bucket
    some_binary_data = b'Here we have some data'

    try:
        # Get the bucket
        bucket = client.get_bucket(bucket_name)

        # Test by uploading a small object
        blob = bucket.blob('test.txt')
        blob.upload_from_string(some_binary_data)

        # Delete the test object
        blob.delete()

        return True
    except Exception as e:
        # Log or print the error if needed
        return False


def create_gcs_bucket(bucket_name, region, logger):
    client = storage.Client()

    try:
        # Create a new bucket
        bucket = client.bucket(bucket_name)
        bucket.storage_class = "STANDARD"  # specify other storage classes if needed
        new_bucket = client.create_bucket(bucket, location=region)

        logger.info(f"Created GCS bucket with name {bucket_name} in region {region}")
    except Exception as e:
        logger.error(f"Couldn't create GCS bucket with name {bucket_name}")
        logger.error(e)
        sys.exit(1)


def create_bigtable_instance_and_table(name, region, logger):
    client = bigtable.Client(admin=True)

    # Create an instance (if it doesn't exist)
    instance_id = name
    try:
        instance = client.instance(instance_id, instance_type=bigtable.enums.Instance.Type.DEVELOPMENT, labels={})
        instance.create(location_id=region)
        logger.info(f"Created Bigtable instance with name {instance_id} in region {region}.")
    except AlreadyExists:
        logger.info(f"Bigtable instance {instance_id} already exists.")

    # Create a table (if it doesn't exist)
    table_id = name + '-table'
    instance = client.instance(instance_id)
    table = instance.table(table_id)

    try:
        if not table.exists():
            # Define column families (schema-like structure in Bigtable)
            column_families = {
                'locks': table.column_family('locks')  # Create a column family named 'locks'
            }
            table.create(column_families=column_families)
            logger.info(f"Created Bigtable table with name {table_id} and schema.")
        else:
            logger.info(f"Bigtable table {table_id} already exists.")
    except Exception as e:
        logger.error(f"Couldn't create Bigtable table with name {table_id}.")
        logger.error(e)
        sys.exit(1)


def delete_gcs_bucket(bucket_name, logger):
    client = storage.Client()

    try:
        # Get the bucket
        bucket = client.get_bucket(bucket_name)

        # Delete all objects in the bucket
        blobs = bucket.list_blobs()
        for blob in blobs:
            blob.delete()

        # Delete the bucket itself
        bucket.delete()

        logger.info(f"Deleted GCS bucket with name {bucket_name}")
    except Exception as e:
        logger.error(f"Couldn't delete GCS bucket with name {bucket_name}")
        logger.error(e)
        return


def delete_bigtable_table(instance_id, table_id, logger):
    client = bigtable.Client(admin=True)

    try:
        # Get the Bigtable instance
        instance = client.instance(instance_id)

        # Get the table
        table = instance.table(table_id)

        # Delete the table
        table.delete()

        logger.info(f"Deleted Bigtable table with name {table_id} in instance {instance_id}")
    except Exception as e:
        logger.error(f"Couldn't delete Bigtable table with name {table_id} in instance {instance_id}")
        logger.error(e)
        return


def check_secret_exists(name, project_id):
    client = secretmanager.SecretManagerServiceClient()

    # Format the secret name
    secret_name = f"{name}-key"
    parent = f"projects/{project_id}"

    try:
        # List secrets in the project
        for secret in client.list_secrets(request={"parent": parent}):
            if secret.name.split("/")[-1] == secret_name:
                return True
    except Exception as e:
        # Log or handle the exception if needed
        return False

    return False


def create_secret(name, value, config, logger, project_id):
    client = secretmanager.SecretManagerServiceClient()
    key_name = f"{name}-key"
    config_name = f"{name}-config"

    try:
        # Create the key secret
        key_secret_path = f"projects/{project_id}/secrets/{key_name}"
        client.create_secret(
            request={
                "parent": f"projects/{project_id}",
                "secret_id": key_name,
                "secret": {"replication": {"automatic": {}}}
            }
        )
        client.add_secret_version(
            request={
                "parent": key_secret_path,
                "payload": {"data": value.encode("UTF-8")}
            }
        )

        # Create the config secret
        config_secret_path = f"projects/{project_id}/secrets/{config_name}"
        client.create_secret(
            request={
                "parent": f"projects/{project_id}",
                "secret_id": config_name,
                "secret": {"replication": {"automatic": {}}}
            }
        )
        client.add_secret_version(
            request={
                "parent": config_secret_path,
                "payload": {"data": json.dumps(config).encode("UTF-8")}
            }
        )

        logger.info(f"Created secrets with names {key_name} and {config_name}")
    except Exception as e:
        logger.error(f"Couldn't create secrets with name {name}")
        logger.error(e)
        sys.exit(1)


def get_secret_key(name, logger, project_id):
    client = secretmanager.SecretManagerServiceClient()

    secret_name = f"{name}-key"
    secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    ssh_key_name = f"{name}.key"

    try:
        # Access the secret's latest version
        response = client.access_secret_version(request={"name": secret_path})
        secret_value = response.payload.data.decode("UTF-8")

        # Write the secret to a file
        with open(ssh_key_name, "w") as ssh_key:
            ssh_key.write(secret_value)

        # Set the file permissions
        os.chmod(ssh_key_name, 0o600)

        logger.info(f"Retrieved secret {secret_name} and saved to {ssh_key_name}")
    except Exception as e:
        logger.error(f"Couldn't retrieve or save secret {secret_name}")
        logger.error(e)
        return

# not needed
def get_secret_config(name, logger, project_id):
    client = secretmanager.SecretManagerServiceClient()

    secret_name = f"{name}-config"
    secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"

    try:
        # Access the secret's latest version
        response = client.access_secret_version(request={"name": secret_path})
        secret_value = response.payload.data.decode("UTF-8")

        # Parse the secret as JSON
        config = json.loads(secret_value)

        logger.info(f"Retrieved configuration secret {secret_name}")
        return config
    except Exception as e:
        logger.error(f"Couldn't retrieve secret {secret_name}")
        logger.error(e)
        return None


def delete_secret(name, logger, project_id):
    client = secretmanager.SecretManagerServiceClient()

    key_secret_name = f"{name}-key"
    config_secret_name = f"{name}-config"

    try:
        # Delete the key secret
        key_secret_path = f"projects/{project_id}/secrets/{key_secret_name}"
        client.delete_secret(request={"name": key_secret_path})
        logger.info(f"Deleted secret: {key_secret_name}")

        # Delete the config secret
        config_secret_path = f"projects/{project_id}/secrets/{config_secret_name}"
        client.delete_secret(request={"name": config_secret_path})
        logger.info(f"Deleted secret: {config_secret_name}")

    except Exception as e:
        logger.error(f"Couldn't delete secret with name {name}")
        logger.error(e)
        return

# TBD
def create_key_pair(name, region, logger):
    aws_session = boto3.Session()
    client = aws_session.client('ec2', region_name=region)

    response = client.create_key_pair(KeyName=name)
    ssh_key_name = name + ".key"
    with open(ssh_key_name, "w") as ssh_key:
        ssh_key.write(response['KeyMaterial'])
    os.chmod(ssh_key_name, 0o600)
    
    logger.info("Created key pair with name " + name)

    return response['KeyMaterial']

# TBD
def delete_key_pair(name, region, logger):
    ec2 = boto3.client('ec2', region_name=region)
    response = ec2.delete_key_pair(KeyName=name)
