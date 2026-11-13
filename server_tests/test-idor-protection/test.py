from testlib import *
from core_api import CoreApi


'''
Tests IDOR (Insecure Direct Object Reference) protection via Zen firewall.

1. GET /api/idor/safe with X-Tenant-ID header — query filters on tenant_id,
   should succeed (200).
2. GET /api/idor/unsafe — query missing tenant_id filter, Zen should throw
   and the route returns 500.
3. GET /api/idor/bypassed — query missing tenant_id filter but wrapped in
   withoutIdorProtection, should succeed (200).
4. Existing pet routes still work because they use withoutIdorProtection.
'''


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()
    tenant_id = "tenant_1"
    headers = {"X-Tenant-ID": tenant_id}

    # 1. Safe route: query correctly filters on tenant_id
    response = s.get("/api/idor/safe", headers=headers)
    collector.soft_assert_response_code_is(
        response, 200, f"Safe IDOR route should succeed: {response.text}")
    collector.soft_assert_response_body_contains(
        response, '"success":true',
        "Safe IDOR route should return success")

    # 2. Unsafe route: query missing tenant_id filter — Zen should throw
    response = s.get("/api/idor/unsafe", headers=headers)
    collector.soft_assert_response_code_is(
        response, 500, f"Unsafe IDOR route should fail with 500: {response.text}")
    collector.soft_assert_response_body_contains(
        response, '"success":false',
        "Unsafe IDOR route should return failure")
    collector.soft_assert_response_body_contains(
        response, "IDOR",
        "Unsafe IDOR route error should mention IDOR")

    # 3. Bypassed route: missing filter but wrapped in withoutIdorProtection
    response = s.get("/api/idor/bypassed", headers=headers)
    collector.soft_assert_response_code_is(
        response, 200, f"Bypassed IDOR route should succeed: {response.text}")
    collector.soft_assert_response_body_contains(
        response, '"success":true',
        "Bypassed IDOR route should return success")

    # 4. Existing pet routes still work (wrapped with withoutIdorProtection)
    response = s.get("/api/pets/", headers=headers)
    collector.soft_assert_response_code_is(
        response, 200, f"Pets list should still work: {response.text}")

    response = s.post("/api/create", {"name": "TestPet"}, headers=headers)
    collector.soft_assert_response_code_is(
        response, 200, f"Pet creation should still work: {response.text}")
    collector.soft_assert_response_body_contains(
        response, "Success", "Pet creation should return Success")

    # 5. Safe route with different tenant — should return different results
    other_headers = {"X-Tenant-ID": "tenant_2"}
    response_t1 = s.get("/api/idor/safe", headers=headers)
    response_t2 = s.get("/api/idor/safe", headers=other_headers)
    collector.soft_assert_response_code_is(
        response_t1, 200, "tenant_1 safe request failed")
    collector.soft_assert_response_code_is(
        response_t2, 200, "tenant_2 safe request failed")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
