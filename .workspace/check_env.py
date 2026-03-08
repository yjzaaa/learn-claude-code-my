import os

print("Current directory:", os.getcwd())
print("\nEnvironment variables:")
for key in ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_PORT']:
    value = os.getenv(key)
    print(f'{key}: {value}')
    
print("\nChecking for .env file...")
if os.path.exists('.env'):
    print(".env file exists")
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
            print("First 500 chars of .env:")
            print(content[:500])
    except UnicodeDecodeError:
        with open('.env', 'rb') as f:
            content = f.read()
            print("First 500 bytes of .env (binary):")
            print(content[:500])
else:
    print(".env file not found")