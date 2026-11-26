"""Wait for Kuma's application handlers after the Socket.IO handshake."""
def setup_required(client, socketio):
    # Kuma awaits sendInfo() before installing its handlers. An event emitted
    # immediately after transport connection can be lost. Retry a read only.
    for timeout in (3, 5, 10, 20):
        try:
            needed = client.call("needSetup", timeout=timeout)
        except socketio.exceptions.TimeoutError:
            continue
        if type(needed) is not bool:
            raise ValueError("Kuma returned an unknown account setup state")
        return needed
    raise ValueError("Kuma account API did not become ready")
