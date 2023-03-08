import json

from fastapi.testclient import TestClient
from app.main import app
import pytest

# Create a test client using the FastAPI instance
client = TestClient(app)
token = None


@pytest.fixture(scope="module")
def jwt_token():
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqYW5lLmRvZUBleGFtcGxlLmNvbSIsInJvbGUiOiJBRE1JTiIsImlzX2FjdGl2ZSI6dHJ1ZSwiaWQiOjEyLCJleHAiOjE2NzgyNTQwMDN9.W4BsaG6Ei4naCd_IuEQZLPAcEtF40bFWCHrAkdX1roo"


def test_incorrect_login():
    # Test with invalid credentials
    response = client.post("/auth/login", data={"username": "john.doe@example.com", "password": "wrong"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect password"}


def test_get_employees(jwt_token):
    response = client.get("/employees", params={"first_name": "jerter", "last_name": "dssdf"},
                          headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 404

    response = client.get("/employees", params={"first_name": "j", "last_name": "d"},
                          headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 200


def test_get_employee(jwt_token):
    response = client.get("/employees/john.e@example.com",
                          headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 404

    response = client.get("/employees/john.doe@example.com",
                          headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 200


def test_delete_employee(jwt_token):
    response = client.delete("/employees/john.e@example.com",
                             headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 404

    response = client.delete("/employees/ava.miller@example.com",
                          headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 200


def test_reset_password_admin(jwt_token):
    response = client.post("/auth/reset-password-admin/john.e@example.com",
                           headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 404

    response = client.get("/employees/emily.jones@example.com",
                          headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 200
