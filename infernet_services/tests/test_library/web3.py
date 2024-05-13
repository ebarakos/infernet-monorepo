import json
import logging
import shlex
import subprocess
from typing import Callable, List, Dict, Any
from uuid import uuid4

from eth_abi.exceptions import InsufficientDataBytes
from reretry import retry
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.contract import AsyncContract
from web3.exceptions import ContractLogicError
from web3.middleware.signing import async_construct_sign_and_send_raw_middleware

from test_library.config_creator import infernet_services_dir
from test_library.constants import (
    DEFAULT_PRIVATE_KEY,
    DEFAULT_COORDINATOR_ADDRESS,
    DEFAULT_CONTRACT_FILENAME,
    DEFAULT_CONTRACT,
    ANVIL_NODE,
)
from test_library.test_config import global_config

log = logging.getLogger(__name__)


def deploy_smart_contracts(
    filename: str = DEFAULT_CONTRACT_FILENAME,
    consumer_contract: str = DEFAULT_CONTRACT,
    sender: str = DEFAULT_PRIVATE_KEY,
    rpc_url: str = ANVIL_NODE,
    coordinator_address: str = DEFAULT_COORDINATOR_ADDRESS,
) -> None:
    """
    Deploys an infernet consumer contract to the chain. Uses the makefile script under
    the hood.

    Args:
        filename (str, optional): The filename of the contract. Defaults to
        GenericCallbackConsumer.sol.
        consumer_contract (str, optional): The contract name. Defaults to
        GenericCallbackConsumer.
        sender (str, optional): The private key of the sender. Defaults to
        DEFAULT_PRIVATE_KEY, which is one of anvil's test private keys.
        rpc_url (str, optional): The RPC URL. Defaults to DEFAULT_INFERNET_RPC_URL.
        coordinator_address (str, optional): The coordinator address. Defaults to
        DEFAULT_COORDINATOR_ADDRESS.

    """
    cmd = (
        f"make deploy-contract filename={filename} "
        f"contract={consumer_contract} sender={sender} "
        f"rpc_url={rpc_url} coordinator={coordinator_address}"
    )
    log.info(f"deploying contract: {cmd}")
    subprocess.run(shlex.split(cmd))


ABIType = List[Dict[str, Any]]


def get_abi(filename: str, contract_name: str) -> ABIType:
    """
    Reads the ABI from a contract file. Uses the `out` directory in the
    `consumer-contracts` foundry project.

    Args:
        filename (str): The filename of the contract.
        contract_name (str): The contract name.

    Returns:
        ABIType: The ABI of the contract.
    """
    with open(
        f"{infernet_services_dir()}/consumer-contracts/out/{filename}/{contract_name}.json"
    ) as f:
        _abi: ABIType = json.load(f)["abi"]
        return _abi


async def assert_web3_output(
    task_id: bytes,
    assertions: Callable[[bytes, bytes, bytes], None],
    timeout: int = 20,
) -> None:
    """
    Asserts the output of a web3 consumer contract. Retries if the assertion
    fails.

    Args:
        index (int): The index of the output.
        assertions (Callable[[bytes, bytes, bytes], None]): The assertion
        function.
        task_id (bytes): The task id.
        timeout (int, optional): The timeout. Defaults to 10 seconds.

    """

    @retry(
        exceptions=(AssertionError, InsufficientDataBytes, ContractLogicError),
        tries=timeout * 2,
        delay=1 / 2,
    )  # type: ignore
    async def _assert():
        log.info(f"querying consumer contract for task id {task_id}")
        consumer = await get_consumer_contract()
        _input = await consumer.functions.receivedInput(task_id).call()
        _output = await consumer.functions.receivedOutput(task_id).call()
        _proof = await consumer.functions.receivedProof(task_id).call()
        log.info(f"consumer contract call: {_input} {_output} {_proof}")
        assertions(_input, _output, _proof)

    await _assert()


async def get_w3() -> AsyncWeb3:
    """
    Gets a web3 instance.

    Returns:
        AsyncWeb3: The web3 instance.
    """
    w3 = AsyncWeb3(AsyncHTTPProvider(global_config.rpc_url))
    account = w3.eth.account.from_key(global_config.private_key)
    w3.middleware_onion.add(await async_construct_sign_and_send_raw_middleware(account))
    w3.eth.default_account = account.address
    return w3


def get_account() -> str:
    w3 = AsyncWeb3(AsyncHTTPProvider(global_config.rpc_url))
    account = w3.eth.account.from_key(global_config.private_key)
    return account.address


def get_deployed_contract_address(deployment_name: str) -> str:
    with open(
        f"{infernet_services_dir()}/consumer-contracts/deployments/deployments.json"
    ) as f:
        deployments = json.load(f)
    return deployments[deployment_name]


async def get_consumer_contract(
    filename: str = DEFAULT_CONTRACT_FILENAME,
    consumer_contract: str = DEFAULT_CONTRACT,
):
    """
    Gets the deployed consumer contract.

    Args:
        filename (str, optional): The filename of the contract. Defaults to
        GenericCallbackConsumer.sol.
        consumer_contract (str, optional): The contract name. Defaults to
        GenericCallbackConsumer.

    Returns:
        AsyncContract: The consumer contract.
    """
    contract_address = global_config.contract_address or get_deployed_contract_address(
        consumer_contract
    )

    return (await get_w3()).eth.contract(
        address=contract_address,
        abi=get_abi(filename, consumer_contract),
    )


async def request_web3_compute(service_id: str, input: bytes) -> bytes:
    """
    Requests compute from the consumer contract.

    Args:
        service_id (str): The service ID.
        input (bytes): The input.

    Returns:
        int: The index of the request.
    """
    consumer = await get_consumer_contract()
    randomness = f"{uuid4()}"
    log.info(f"requesting compute {service_id} {randomness} {input}")
    fn = consumer.functions.requestCompute(service_id, randomness, input)
    gen_id = await fn.call()
    log.info(f"generated id {gen_id}")
    tx = await fn.transact()
    log.info(f"awaiting transaction {tx.hex()}")
    await (await get_w3()).eth.wait_for_transaction_receipt(tx)
    return gen_id
