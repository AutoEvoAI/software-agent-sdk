for pkg in openhands-sdk openhands-tools openhands-workspace openhands-agent-server; do
    uv build --package "$pkg"
done

for pkg in openhands-sdk openhands-tools openhands-workspace openhands-agent-server; do
    pip uninstall -y "$pkg"
    pip install dist/*.whl
done
