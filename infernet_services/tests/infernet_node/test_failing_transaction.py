import logging
import random

import pytest
from infernet_node.test_delegate_subscription import (
    create_delegated_subscription,
    get_next_subscription_id,
)
from infernet_node.test_subscriptions import create_sub_with_random_input
from test_library.assertion_utils import assert_regex_in_node_logs
from test_library.web3_utils import echo_input

log = logging.getLogger(__name__)

CONSUMER_CONTRACT = "FailingSubscriptionConsumer"


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=2, reruns_delay=2)
async def test_infernet_failing_subscription_must_retry_then_give_up() -> None:
    next_sub = await get_next_subscription_id()
    log.info(f"next_sub: {next_sub}")
    await create_sub_with_random_input(1, 5, contract_name=CONSUMER_CONTRACT)

    await assert_regex_in_node_logs(
        f"Subscription has exceeded the maximum number of attempts.*{next_sub}",
        timeout=20,
    )


@pytest.mark.asyncio
async def test_infernet_failing_delegated_subscription_must_retry_then_give_up() -> None:
    i = random.randint(0, 255)
    nonce = await create_delegated_subscription(
        echo_input(i), 8, 1, contract_name=CONSUMER_CONTRACT
    )

    await assert_regex_in_node_logs(
        f"Subscription has exceeded the maximum number of attempts.*{nonce}"
    )
