#!/usr/bin/env python
"""Auth API Test Script

测试登录系统API端点。
"""

import asyncio
import sys

import httpx

BASE_URL = "http://localhost:8001"


async def test_auto_login():
    """测试自动登录"""
    print("\n=== Testing Auto Login ===")
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/api/auth/auto-login", json={})
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data}")

            if data.get("success"):
                user = data["data"]["user"]
                tokens = data["data"]["tokens"]
                client_id = data["data"]["client_id"]

                print(f"\nUser: {user['username']} (role: {user['role']})")
                print(f"Client ID: {client_id}")
                print(f"Access Token: {tokens['access_token'][:30]}...")

                return tokens["access_token"], client_id
            else:
                print("Login failed!")
                return None, None
        else:
            print(f"Error: {response.text}")
            return None, None


async def test_get_current_user(access_token: str, client_id: str):
    """测试获取当前用户"""
    print("\n=== Testing Get Current User ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Client-ID": client_id,
            },
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


async def test_logout(access_token: str, client_id: str):
    """测试登出"""
    print("\n=== Testing Logout ===")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/logout",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Client-ID": client_id,
            },
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


async def main():
    """主测试函数"""
    print("Auth API Test Script")
    print("=" * 50)

    # 测试自动登录
    access_token, client_id = await test_auto_login()

    if not access_token:
        print("\nAuto login failed, stopping tests.")
        sys.exit(1)

    # 测试获取当前用户
    await test_get_current_user(access_token, client_id)

    # 测试登出
    await test_logout(access_token, client_id)

    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
