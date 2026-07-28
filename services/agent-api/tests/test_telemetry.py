import os
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from app.main import app

try:
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
except ImportError:
    transport = None

def get_client():
    if transport is not None:
        return AsyncClient(transport=transport, base_url="http://test")
    else:
        return AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
async def test_telemetry_disabled_without_api_key():
    # Remove BRAINTRUST_API_KEY from environment
    with patch.dict(os.environ, {}, clear=True):
        if "BRAINTRUST_API_KEY" in os.environ:
            del os.environ["BRAINTRUST_API_KEY"]
            
        with patch("braintrust.init_logger") as mock_init, \
             patch("braintrust.start_span") as mock_start:
             
            async with get_client() as client:
                response = await client.post(
                    "/api/v1/session/init",
                    json={"guest_session_id": "test-telemetry-no-key", "mode": "guest"}
                )
            
            # Should not call Braintrust tracing
            mock_init.assert_not_called()
            mock_start.assert_not_called()
            assert response.status_code == 200

@pytest.mark.asyncio
async def test_telemetry_enabled_with_api_key():
    # Set BRAINTRUST_API_KEY in environment
    with patch.dict(os.environ, {"BRAINTRUST_API_KEY": "test_api_key"}):
        mock_span = MagicMock()
        with patch("braintrust.init_logger") as mock_init, \
             patch("braintrust.start_span", return_value=mock_span) as mock_start:
             
            async with get_client() as client:
                response = await client.post(
                    "/api/v1/session/init",
                    json={"guest_session_id": "test-telemetry-with-key", "mode": "guest"}
                )
            
            # Verify request completed successfully
            assert response.status_code == 200
            
            # Verify Braintrust tracing was initialized and span was created/closed
            mock_init.assert_called_once_with(project="PourMind-AI")
            mock_start.assert_called_once_with(name="POST /api/v1/session/init")
            
            # Verify log and close were called on the span
            mock_span.log.assert_called_once()
            mock_span.close.assert_called_once()
            
            # Retrieve arguments passed to span.log
            args, kwargs = mock_span.log.call_args
            log_input = kwargs.get("input", {})
            log_output = kwargs.get("output", {})
            log_metadata = kwargs.get("metadata", {})
            
            assert log_input["method"] == "POST"
            assert log_input["path"] == "/api/v1/session/init"
            assert log_output["status_code"] == 200
            assert "duration" in log_metadata
            assert log_metadata["status_code"] == 200

@pytest.mark.asyncio
async def test_telemetry_error_logging():
    # Set BRAINTRUST_API_KEY in environment
    with patch.dict(os.environ, {"BRAINTRUST_API_KEY": "test_api_key"}):
        mock_span = MagicMock()
        with patch("braintrust.init_logger") as mock_init, \
             patch("braintrust.start_span", return_value=mock_span) as mock_start:
             
            async with get_client() as client:
                # Invalid payload triggers 422 Unprocessable Entity
                response = await client.post(
                    "/api/v1/session/init",
                    json={}
                )
            
            assert response.status_code == 422
            
            mock_init.assert_called_once_with(project="PourMind-AI")
            mock_start.assert_called_once_with(name="POST /api/v1/session/init")
            mock_span.log.assert_called_once()
            mock_span.close.assert_called_once()
            
            args, kwargs = mock_span.log.call_args
            log_output = kwargs.get("output", {})
            assert log_output["status_code"] == 422

@pytest.mark.asyncio
async def test_telemetry_graceful_failures():
    # Test that the middleware continues to work even if Braintrust start_span raises an exception
    with patch.dict(os.environ, {"BRAINTRUST_API_KEY": "test_api_key"}):
        with patch("braintrust.init_logger") as mock_init, \
             patch("braintrust.start_span", side_effect=Exception("Braintrust is down")) as mock_start:
             
            async with get_client() as client:
                response = await client.post(
                    "/api/v1/session/init",
                    json={"guest_session_id": "test-telemetry-graceful", "mode": "guest"}
                )
            
            # Request should still succeed even if Braintrust start_span threw an exception
            assert response.status_code == 200

@pytest.mark.asyncio
async def test_telemetry_non_api_v1_ignored():
    # Set BRAINTRUST_API_KEY in environment
    with patch.dict(os.environ, {"BRAINTRUST_API_KEY": "test_api_key"}):
        with patch("braintrust.init_logger") as mock_init, \
             patch("braintrust.start_span") as mock_start:
             
            async with get_client() as client:
                response = await client.get("/health")
            
            assert response.status_code == 200
            mock_init.assert_not_called()
            mock_start.assert_not_called()
