from app import app

with app.app_context():
    with app.test_client() as client:
        response = client.get('/')
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✓ Landing page renders successfully")
            print(f"Content length: {len(response.data)} bytes")
            if b'Detect Diabetic' in response.data:
                print("✓ Hero title found in page")
            else:
                print("✗ Hero title NOT found in page")
        else:
            print(f"Error: {response.status_code}")
            print(response.data[:500])
