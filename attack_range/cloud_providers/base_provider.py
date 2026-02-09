"""
Base cloud provider abstract class.

This module defines the abstract base class for all cloud providers.
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging


class BaseCloudProvider(ABC):
    """Abstract base class for cloud providers."""

    def __init__(self, config: dict, logger: logging.Logger):
        """
        Initialize the cloud provider.

        :param config: Configuration dictionary
        :param logger: Logger instance
        """
        self.config = config
        self.logger = logger

    @abstractmethod
    def get_region(self, required: bool = True) -> Optional[str]:
        """
        Get the region/location for the cloud provider.

        :param required: If True, raise error if region is not found
        :return: Region string or None
        """
        pass

    @abstractmethod
    def check_backend_exists(self, backend_name: str) -> bool:
        """
        Check if the backend storage exists.

        :param backend_name: Name of the backend storage
        :return: True if backend exists, False otherwise
        """
        pass

    @abstractmethod
    def create_backend(self, backend_name: str, region: str) -> None:
        """
        Create the backend storage for Terraform state.

        :param backend_name: Name of the backend storage
        :param region: Region where the backend should be created
        """
        pass

    @abstractmethod
    def delete_backend(self, backend_name: str, region: str) -> None:
        """
        Delete the backend storage.

        :param backend_name: Name of the backend storage
        :param region: Region where the backend is located
        """
        pass

    @abstractmethod
    def sanitize_name(self, name: str) -> str:
        """
        Sanitize a name to meet cloud provider naming requirements.

        :param name: Name to sanitize
        :return: Sanitized name
        """
        pass

    @abstractmethod
    def import_ssh_key(self, key_name: str, public_key_content: str, region: str) -> None:
        """
        Import SSH public key to the cloud provider (if applicable).

        :param key_name: Name for the key
        :param public_key_content: Public key content
        :param region: Region for the key
        """
        pass

    @abstractmethod
    def delete_ssh_key(self, key_name: str, region: str) -> None:
        """
        Delete SSH key from the cloud provider (if applicable).

        :param key_name: Name of the key to delete
        :param region: Region where the key is located
        """
        pass

    @abstractmethod
    def update_backend_config(self, backend_params: dict, backend_file_path: str) -> None:
        """
        Update the backend configuration file.

        :param backend_params: Dictionary containing backend parameters
        :param backend_file_path: Path to the backend.tf file
        """
        pass
