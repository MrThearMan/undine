Apollo `reports.proto` and its Python bindings, used **only** for verifying
`undine.federation.tracing` output in tests.

The wheel does not ship these files — they live under `tests/` deliberately so
that the runtime hand-encoded ftv1 output can be cross-checked against the real
protobuf runtime.

To regenerate `reports_pb2.py`:

```
curl -sSL https://raw.githubusercontent.com/apollographql/apollo-server/main/packages/usage-reporting-protobuf/src/reports.proto \
    -o reports.proto
# strip proto2-era options that the current protoc rejects
sed -i 's/\s*\[(js_use_toArray)=true\]//g;s/\s*\[(js_preEncoded)=true\]//g' reports.proto
poetry run python -m grpc_tools.protoc --python_out=. --proto_path=. reports.proto
```
