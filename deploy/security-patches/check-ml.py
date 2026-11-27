"""Exercise the patched codecs and run a tiny offline model on the CPU provider."""
import idna
import msgpack
import numpy as np
import onnx
import onnxruntime
import pygments
import urllib3
from onnx import TensorProto, helper
from pygments.formatters import TerminalFormatter
from pygments.lexers import PythonLexer

assert msgpack.unpackb(msgpack.packb({"rows": [1, 2]})) == {"rows": [1, 2]}
assert urllib3.util.parse_url("https://localhost:3003/ping").host == "localhost"
assert idna.__version__ == '3.15'
assert idna.decode(idna.encode('bücher.example')) == 'bücher.example'
assert pygments.__version__ == '2.20.0'
assert 'print' in pygments.highlight('print(1)', PythonLexer(), TerminalFormatter())
shape = [1]
inputs = [helper.make_tensor_value_info("x", TensorProto.FLOAT, shape)]
outputs = [helper.make_tensor_value_info("y", TensorProto.FLOAT, shape)]
graph = helper.make_graph([helper.make_node("Identity", ["x"], ["y"])], "pilot", inputs, outputs)
model = helper.make_model(graph, ir_version=8, opset_imports=[helper.make_opsetid("", 13)])
onnx.checker.check_model(model)
session = onnxruntime.InferenceSession(model.SerializeToString(), providers=["CPUExecutionProvider"])
np.testing.assert_array_equal(session.run(None, {"x": np.array([3], dtype=np.float32)})[0], [3])

# Drive FastAPI and Starlette over ASGI without opening a port or fetching models.
import anyio
from fastapi import FastAPI
from starlette.requests import Request

app = FastAPI()

@app.post("/fixture")
async def fixture(request: Request):
    return await request.json()

async def verify_asgi():
    replies = []

    async def receive():
        return {"type": "http.request", "body": b'{"ready":true}', "more_body": False}

    async def send(message):
        replies.append(message)

    await app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
               "method": "POST", "path": "/fixture", "query_string": b"",
               "scheme": "http", "headers": [(b"content-type", b"application/json")]},
              receive, send)
    assert replies[0]["status"] == 200
    assert replies[1]["body"] == b'{"ready":true}'

anyio.run(verify_asgi)
