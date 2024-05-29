import json
import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from test_library.constants import (
    DEFAULT_COORDINATOR_ADDRESS,
    DEFAULT_INFERNET_RPC_URL,
    DEFAULT_PAYMENT_ADDRESS,
    DEFAULT_PRIVATE_KEY,
)

base_config = {
    "log_path": "infernet_node.log",
    "server": {"port": 4000},
    "chain": {
        "enabled": True,
        "trail_head_blocks": 0,
        "rpc_url": "",
        "coordinator_address": "",
        "wallet": {
            "max_gas_limit": 4000000,
            "private_key": "",
            "allowed_sim_errors": ["reverting"],
        },
    },
    "startup_wait": 1.0,
    "docker": {"username": "your-username", "password": ""},
    "redis": {"host": "redis", "port": 6379},
    "forward_stats": True,
    "containers": [],
}

ServiceEnvVars = Dict[str, Any]

log = logging.getLogger(__name__)


class ServiceConfig(BaseModel):
    """
    A Pydantic model for the service configuration.

    Args:
        name: The name of the service
        image_id: The image ID of the service
        env_vars: A dictionary of environment variables
        port: The port on which the service will run
    """

    name: str
    image_id: str
    env_vars: ServiceEnvVars = {}
    port: int

    @classmethod
    def build_service(
        cls,
        name: str,
        image_id: str = "",
        port: int = 3000,
        env_vars: Optional[ServiceEnvVars] = None,
    ) -> "ServiceConfig":
        return cls(
            name=name,
            image_id=image_id or f"ritualnetwork/{name}:latest",
            env_vars=env_vars if env_vars else {},
            port=port,
        )


def create_config_file(
    services: List[ServiceConfig],
    private_key: str = DEFAULT_PRIVATE_KEY,
    coordinator_address: str = DEFAULT_COORDINATOR_ADDRESS,
    rpc_url: str = DEFAULT_INFERNET_RPC_URL,
) -> None:
    log.info(f"Creating config file for services {services}")
    cfg = get_config(
        services,
        private_key=private_key,
        coordinator_address=coordinator_address,
        rpc_url=rpc_url,
    )
    with open(config_path(), "w") as f:
        f.write(json.dumps(cfg, indent=4))


def get_service_port(service_name: str) -> int:
    """
    Get the port for the service with the given name.
    Reads it from the default `config.json` file. Use this function after generating the
    config file.

    Args:
        service_name: The name of the service

    Returns:
        The port number
    """
    with open(config_path(), "r") as f:
        cfg = json.load(f)
    for container in cfg["containers"]:
        if container["id"] == service_name:
            return int(container["port"])
    raise ValueError(f"Service {service_name} not found in config file")


def get_config(
    services: List[ServiceConfig],
    private_key: str = DEFAULT_PRIVATE_KEY,
    coordinator_address: str = DEFAULT_COORDINATOR_ADDRESS,
    payment_address: str = DEFAULT_PAYMENT_ADDRESS,
    rpc_url: str = DEFAULT_INFERNET_RPC_URL,
) -> Dict[str, Any]:
    """
    Create an infernet config.json dictionary with the given parameters.

    Args:
        services: A list of ServiceConfig objects.
        private_key: The private key of the wallet
        coordinator_address: The coordinator address
        payment_address: The payment address of the node. This is the address that will
            receive payments.
        rpc_url: The RPC URL of the chain

    Returns:
        A dictionary representing the infernet config.json file
    """

    cfg: Dict[str, Any] = base_config.copy()
    for service in services:
        cfg["containers"].append(
            {
                "id": service.name,
                "image": service.image_id,
                "env": service.env_vars,
                "port": service.port,
                "allowed_delegate_addresses": [],
                "allowed_addresses": [],
                "allowed_ips": [],
                "command": "--bind=0.0.0.0:3000 --workers=2",
                "external": True,
            }
        )
    cfg["chain"]["wallet"]["private_key"] = private_key
    cfg["chain"]["wallet"]["payment_address"] = payment_address
    cfg["chain"]["coordinator_address"] = coordinator_address
    cfg["chain"]["rpc_url"] = rpc_url
    return cfg


def monorepo_dir() -> str:
    """
    Get the top level directory of the infernet monorepo.

    Returns:
        The path to the top level directory
    """
    top_level_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    while "infernet-monorepo" not in os.path.basename(top_level_dir):
        top_level_dir = os.path.dirname(top_level_dir)
    return top_level_dir


def infernet_services_dir() -> str:
    """
    Get the path to the `infernet_services` directory under the infernet monorepo.

    Returns:
        The path to the `infernet_services` directory
    """
    return os.path.join(monorepo_dir(), "infernet_services")


def config_path() -> str:
    """
    Get the path to the config.json file under the `infernet_services/deploy` directory.
    This is used to write the config file for the infernet deployment.

    Returns:
        The target path
    """
    return os.path.join(infernet_services_dir(), "deploy", "config.json")
