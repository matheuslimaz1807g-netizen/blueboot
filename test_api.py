"""
test_api.py — Test the license API locally.

Usage:
    python test_api.py

Requires the API to be running (docker compose up -d).
"""
import requests
import json
import sys

# Fix encoding for Windows terminal
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_BASE = "http://localhost:8000"

def test_health():
    print("\n[TEST] GET /health")
    r = requests.get(f"{API_BASE}/health")
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")
    assert r.status_code == 200
    return True

def test_validate_license(key, machine_id, expected_valid):
    print(f"\n[TEST] POST /license/validate (key={key})")
    r = requests.post(
        f"{API_BASE}/license/validate",
        json={"license_key": key, "machine_id": machine_id},
    )
    data = r.json()
    print(f"   Status: {r.status_code}")
    print(f"   Response: {json.dumps(data, indent=2)}")
    
    if expected_valid:
        assert data["valid"] == True, f"Expected valid=True, got {data['valid']}"
        print("   [OK] License is valid!")
    else:
        assert data["valid"] == False, f"Expected valid=False, got {data['valid']}"
        print("   [OK] License correctly rejected!")
    return data

def test_heartbeat(key, machine_id):
    print(f"\n[TEST] POST /license/heartbeat (key={key})")
    r = requests.post(
        f"{API_BASE}/license/heartbeat",
        json={"license_key": key, "machine_id": machine_id},
    )
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")
    return r.status_code == 200

def test_admin_login():
    print(f"\n[TEST] POST /admin/login")
    r = requests.post(
        f"{API_BASE}/admin/login",
        json={"username": "admin", "password": "admin123"},
    )
    print(f"   Status: {r.status_code}")
    data = r.json()
    print(f"   Token: {data.get('access_token', 'N/A')[:50]}...")
    assert r.status_code == 200
    return data["access_token"]

def test_admin_list_licenses(token):
    print(f"\n[TEST] GET /admin/licenses")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE}/admin/licenses", headers=headers)
    print(f"   Status: {r.status_code}")
    data = r.json()
    print(f"   Licenses found: {len(data)}")
    for lic in data:
        print(f"      - {lic['key']} | plan={lic['plan']} | active={lic['active']} | machine={lic.get('machine_id', 'unbound')}")
    return data

def test_get_config(key, machine_id, token):
    print(f"\n[TEST] GET /config/{key}")
    r = requests.get(
        f"{API_BASE}/config/{key}",
        params={"machine_id": machine_id},
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print(f"   Response: {json.dumps(r.json(), indent=2)}")
    else:
        print(f"   Response: {r.json()}")
    return r

def test_version_latest():
    print(f"\n[TEST] GET /version/latest")
    r = requests.get(f"{API_BASE}/version/latest")
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print(f"   Response: {json.dumps(r.json(), indent=2)}")
    else:
        print(f"   Response: {r.json()}")
    return r


if __name__ == "__main__":
    print("=" * 60)
    print("  BlueBot License API - Test Suite")
    print("=" * 60)
    
    MACHINE_ID = "test_machine_123456"
    
    try:
        # 1. Health check
        test_health()
        
        # 2. Validate a valid license (first time = binds machine)
        test_validate_license("APRO-AAAA-BBBB-CCCC", MACHINE_ID, expected_valid=True)
        
        # 3. Heartbeat
        test_heartbeat("APRO-AAAA-BBBB-CCCC", MACHINE_ID)
        
        # 4. Validate again (should work, same machine)
        test_validate_license("APRO-AAAA-BBBB-CCCC", MACHINE_ID, expected_valid=True)
        
        # 5. Try with wrong machine ID (should fail)
        test_validate_license("APRO-AAAA-BBBB-CCCC", "wrong_machine_999", expected_valid=False)
        
        # 6. Expired license (should fail)
        test_validate_license("APRO-GGGG-HHHH-IIII", MACHINE_ID, expected_valid=False)
        
        # 7. Inactive license (should fail)
        test_validate_license("APRO-JJJJ-KKKK-LLLL", MACHINE_ID, expected_valid=False)
        
        # 8. Admin login
        token = test_admin_login()
        
        # 9. List licenses
        test_admin_list_licenses(token)
        
        # 10. Get config (should be 404 - not configured yet)
        test_get_config("APRO-AAAA-BBBB-CCCC", MACHINE_ID, token)
        
        # 11. Latest version
        test_version_latest()
        
        print("\n" + "=" * 60)
        print("  [ALL TESTS PASSED!]")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n[TEST FAILED]: {e}")
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] API is not running! Start it with: start_local.bat")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
