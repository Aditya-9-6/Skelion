import os
import uuid
os.environ['DATABASE_URI'] = 'sqlite:///./helios.db'
import hmac, hashlib, json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from skelion_agent.control_plane import app
from skelion_agent.razorpay_service import RAZORPAY_WEBHOOK_SECRET

client = TestClient(app)

def run_verification():
    fresh_id = int(uuid.uuid4().int % 100000000)
    print('=== 1. VERIFYING GITHUB SIGN-IN & PILOT AUTO-ASSIGNMENT ===')
    mock_gh_user = {
        'id': fresh_id,
        'login': f'verify_user_{fresh_id}',
        'email': f'verify_{fresh_id}@skelion.dev',
        'avatar_url': f'https://avatars.githubusercontent.com/u/{fresh_id}'
    }

    with patch('httpx.AsyncClient.get') as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gh_user
        mock_get.return_value = mock_resp

        r_auth = client.post('/v1/auth/github', json={'access_token': 'gho_verified_token'})
        assert r_auth.status_code == 200, f'Auth failed: {r_auth.text}'
        auth_data = r_auth.json()
        token = auth_data['access_token']
        user = auth_data['user']
        print(f"User: {user['username']}, Plan: {user['plan']}, Credits: {user['credits_remaining']}")
        assert user['plan'] == 'pilot', 'Initial plan must be pilot'
        assert user['credits_remaining'] == 100, 'Initial credits must be 100'

    headers = {'Authorization': f'Bearer {token}'}

    print('\n=== 2. VERIFYING /v1/auth/me & /v1/billing/plan ===')
    r_me = client.get('/v1/auth/me', headers=headers)
    assert r_me.status_code == 200
    assert r_me.json()['email'] == mock_gh_user['email']

    r_plan = client.get('/v1/billing/plan', headers=headers)
    assert r_plan.status_code == 200
    assert len(r_plan.json()['available_plans']) == 3
    print(f"Current Plan: {r_plan.json()['plan']}, Price: INR {r_plan.json()['price']}")

    print('\n=== 3. VERIFYING MODEL PERMISSIONS & GATING ===')
    r_models = client.get('/v1/models', headers=headers)
    assert r_models.status_code == 200
    unlocked_models = [m['id'] for m in r_models.json()['models'] if m['unlocked']]
    locked_models = [m['id'] for m in r_models.json()['models'] if not m['unlocked']]
    print(f"Unlocked for Pilot: {unlocked_models}")
    print(f"Locked for Pilot: {locked_models}")
    assert 'gpt-4o-mini' in unlocked_models
    assert 'claude-3-5-sonnet' in locked_models

    # Attempt to use locked model -> 403 Forbidden
    r_forbidden = client.post('/v1/chat', json={'messages': [{'role': 'user', 'content': 'Test'}], 'model': 'claude-3-5-sonnet'}, headers=headers)
    assert r_forbidden.status_code == 403
    print(f"Gating check: claude-3-5-sonnet rejected with 403 ({r_forbidden.json()['detail']})")

    print('\n=== 4. VERIFYING CHAT STREAMING & CREDIT DEDUCTION ===')
    r_chat = client.post('/v1/chat', json={'messages': [{'role': 'user', 'content': 'Please fix the edge proxy'}], 'model': 'gpt-4o-mini'}, headers=headers)
    assert r_chat.status_code == 200
    assert 'event: delta' in r_chat.text
    assert 'event: tool_call' in r_chat.text
    assert 'event: usage' in r_chat.text
    print('Streaming response received with delta, tool_call, and usage events.')

    r_me_after_chat = client.get('/v1/auth/me', headers=headers)
    remaining = r_me_after_chat.json()['credits_remaining']
    print(f"Credits after chat: {remaining} (Deducted 1 credit)")
    assert remaining == 99

    print('\n=== 5. VERIFYING RAZORPAY CHECKOUT & WEBHOOK UPGRADE TO PRO ===')
    r_checkout = client.post('/v1/billing/checkout?plan=pro', headers=headers)
    assert r_checkout.status_code == 200
    checkout_data = r_checkout.json()
    order_id = checkout_data['order_id']
    print(f"Razorpay Order Created: {order_id}, Amount: {checkout_data['amount']} paise")

    # Simulate incoming Razorpay webhook on payment.captured
    user_id = user['id']
    webhook_payload = {
        'event': 'payment.captured',
        'payload': {
            'payment': {
                'entity': {
                    'id': f'pay_{fresh_id}',
                    'status': 'captured',
                    'amount': 399900,
                    'currency': 'INR',
                    'receipt': f'{user_id}:pro'
                }
            }
        }
    }
    raw_webhook = json.dumps(webhook_payload).encode('utf-8')
    sig = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode('utf-8'), raw_webhook, hashlib.sha256).hexdigest()

    r_webhook = client.post('/v1/billing/webhook', content=raw_webhook, headers={'X-Razorpay-Signature': sig})
    assert r_webhook.status_code == 200
    print(f"Webhook processed: {r_webhook.json()['status']}, New Plan: {r_webhook.json()['new_plan']}")

    # Verify user is now PRO with 5000 credits
    r_me_pro = client.get('/v1/auth/me', headers=headers)
    assert r_me_pro.json()['plan'] == 'pro'
    assert r_me_pro.json()['credits_remaining'] == 5000
    print(f"User upgraded to PRO! Remaining Credits: {r_me_pro.json()['credits_remaining']}")

    # Verify model unlocking on Pro tier
    r_pro_chat = client.post('/v1/chat', json={'messages': [{'role': 'user', 'content': 'Refactor with sonnet'}], 'model': 'claude-3-5-sonnet'}, headers=headers)
    assert r_pro_chat.status_code == 200
    print('Pro chat stream with claude-3-5-sonnet succeeded!')

    print('\n======================================================')
    print('ALL VERIFICATION CHECKS PASSED WITH 100% SUCCESS!')
    print('======================================================')

if __name__ == '__main__':
    run_verification()
