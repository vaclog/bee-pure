class DepositoApiClient:
    def __init__(self, config, dry_run=True):
        self.config = config
        self.dry_run = dry_run

    def confirm_customer_sync(self, request_id, status, error_detail=""):
        payload = {
            "request_id": request_id,
            "status": status,
            "error_detail": error_detail or "",
            "queue_type": "customers",
        }
        if self.dry_run:
            return {"dry_run": True, "payload": payload}

        return self._post_json("/api/ordenes-venta/customer-sync/confirm/", payload)

    def export_pending_customers(self, client_id=None, request_id="", limit=500):
        payload = {
            "request_id": request_id or "",
            "limit": limit,
        }
        if client_id not in (None, ""):
            payload["client_id"] = client_id
        if self.dry_run:
            return {"dry_run": True, "payload": payload, "rows": [], "request_id": request_id or ""}

        return self._post_json("/api/ordenes-venta/customer-sync/export/", payload)

    def _post_json(self, path, payload):
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests no esta instalado.") from exc

        if not self.config.base_url:
            raise RuntimeError("DEPOSITO_API_BASE_URL es requerido.")

        headers = {"Content-Type": "application/json"}
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"

        response = requests.post(
            f"{self.config.base_url}{path}",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
