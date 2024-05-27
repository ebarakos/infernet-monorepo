import json
from typing import Generator

import pytest
from dotenv import load_dotenv
from eth_abi.abi import encode
from infernet_ml.utils.codec.vector import encode_vector
from infernet_ml.utils.model_loader import ModelSource
from onnx_inference_service.common import (
    SERVICE_NAME,
    iris_classification_web2_assertions_fn,
    iris_input_vector_params,
)
from test_library.constants import (
    hf_model_id,
    skip_contract,
    skip_deploying,
    skip_teardown,
)
from test_library.infernet_fixture import handle_lifecycle
from test_library.web2_utils import get_job, request_job
from test_library.web3_utils import (
    assert_generic_callback_consumer_output,
    iris_web3_assertions,
    request_web3_compute,
)

load_dotenv()


@pytest.fixture(scope="module", autouse=True)
def hf_hub_setup() -> Generator[None, None, None]:
    yield from handle_lifecycle(
        SERVICE_NAME,
        {
            "MODEL_SOURCE": ModelSource.HUGGINGFACE_HUB.value,
            "LOAD_ARGS": json.dumps(
                {
                    "repo_id": "Ritual-Net/iris-classification",
                    "filename": "iris.onnx",
                }
            ),
        },
        skip_deploying=skip_deploying,
        skip_contract=skip_contract,
        skip_teardown=skip_teardown,
    )


model_source, load_args = (
    ModelSource.HUGGINGFACE_HUB,
    {
        "repo_id": hf_model_id("iris-classification"),
        "filename": "iris.onnx",
        "version": None,
    },
)


@pytest.mark.asyncio
async def test_basic_web2_inference_from_hf_hub() -> None:
    task = await request_job(
        SERVICE_NAME,
        {
            "model_source": None,
            "load_args": None,
            "inputs": {"input": {**iris_input_vector_params, "dtype": "float"}},
        },
    )

    job_result = await get_job(task.id)

    iris_classification_web2_assertions_fn(job_result.result.output)


@pytest.mark.asyncio
async def test_basic_web3_inference_from_hf_hub() -> None:
    task_id = await request_web3_compute(
        SERVICE_NAME,
        encode(
            ["uint8", "string", "string", "string", "bytes"],
            [
                0,
                "",
                "",
                "",
                encode_vector(
                    **iris_input_vector_params,
                ),
            ],
        ),
    )

    await assert_generic_callback_consumer_output(task_id, iris_web3_assertions)
